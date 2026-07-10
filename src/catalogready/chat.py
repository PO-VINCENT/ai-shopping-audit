"""Interactive agent interface for CatalogReady, in the spirit of Claude Code.

A terminal session wraps the bounded product-readiness agent: load a page,
watch the tool trace stream, answer the questions the agent cannot infer,
draft evidence-backed fixes, and ask free-text questions about the result.

Free-text questions are answered deterministically from the audit result.
When a BYO provider is configured (server environment variables only), the
same questions are answered by the model, grounded strictly in the audit
JSON. The chat layer is an adapter: all capability lives in the service.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .fetch import fetch_page
from .model_providers import ProviderError, create_provider, provider_status
from .reporting.html import PILLAR_LABELS, render_html_report
from .reporting.terminal import (
    render_findings,
    render_questions,
    render_score_card,
    render_trace,
)
from .service import run_product_agent_html

_BANNER = """\
CatalogReady agent · audit product pages for AI shopping readiness
Offline deterministic core · no storefront writes · /help for commands
"""

_HELP = """\
Commands
  /audit <url> [saved.html]   Load a page (one fetch, or a local file) and audit it
  /draft                      Build and validate reversible, evidence-backed fixes
  /answers field=value ...    Supply verified merchant facts and re-run the agent
  /questions                  Show the facts the agent still needs
  /findings                   Show all findings with rule IDs
  /score                      Show the score card again
  /jsonld                     Print the recommended Product JSON-LD
  /report [path]              Write the self-contained HTML report
  /provider <name> [model]    Use a BYO model for free-text answers (env keys only)
  /json                       Dump the full result JSON
  /quit                       Exit

Anything else is treated as a question about the current audit, e.g.
  why is media & variants low?   what should I fix first?
"""

_ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answer"],
    "properties": {"answer": {"type": "string"}},
}

_ASSISTANT_SYSTEM = (
    "You are the CatalogReady audit assistant. Answer the merchant's question "
    "using ONLY the supplied audit JSON. Quote scores, rule IDs, and evidence "
    "from it. If the answer is not in the JSON, say exactly that. Never invent "
    "product facts, rankings, or guarantees."
)


class ChatSession:
    def __init__(self, use_color: bool = False) -> None:
        self.use_color = use_color
        self.url: str = ""
        self.html: str = ""
        self.result: dict[str, Any] | None = None
        self.answers: dict[str, Any] = {}
        self.provider_name: str = "deterministic"
        self.model: str = ""

    # ---- agent runs -------------------------------------------------

    def _run(self, mode: str) -> str:
        result = run_product_agent_html(
            self.url,
            self.html,
            mode=mode,
            merchant_answers=self.answers or None,
        )
        self.result = result
        parts = [render_trace(result, self.use_color), render_score_card(result, use_color=self.use_color)]
        questions = result.get("merchant_questions") or []
        blocking = [item for item in questions if item.get("blocking")]
        if blocking:
            parts.append(render_questions(questions, self.use_color))
        if mode == "draft":
            parts.append(self._describe_validation(result))
        return "\n".join(part for part in parts if part)

    def _describe_validation(self, result: dict[str, Any]) -> str:
        changes = result.get("proposed_changes") or []
        validation = result.get("validation") or {}
        if not changes:
            return "No evidence-backed page changes were justified."
        lines = [f"Proposed {len(changes)} reversible change(s):"]
        lines.extend(
            f"  {item.get('id')}: {item.get('operation')}" for item in changes
        )
        delta = validation.get("score_delta")
        if delta is not None:
            lines.append(
                f"Isolated preview validation: {validation.get('before_score')} → "
                f"{validation.get('after_score')} ({delta:+d}), status {validation.get('status')}."
            )
        lines.append("Nothing was written to any storefront. Use /jsonld or /report to export.")
        return "\n".join(lines)

    # ---- commands ---------------------------------------------------

    def cmd_audit(self, args: list[str]) -> str:
        if not args:
            return "Usage: /audit <url> [saved.html]"
        self.url = args[0]
        if len(args) > 1:
            self.html = Path(args[1]).read_text(encoding="utf-8")
        else:
            print(f"Fetching {self.url} (single request) ...", file=sys.stderr)
            self.html = fetch_page(self.url)
        self.answers = {}
        return self._run("audit")

    def cmd_answers(self, args: list[str]) -> str:
        if not self.result:
            return "Load a page first with /audit."
        if not args:
            return "Usage: /answers field=value [field=value ...]"
        for pair in args:
            if "=" not in pair:
                return f"Not a field=value pair: {pair}"
            field, value = pair.split("=", 1)
            self.answers[field.strip()] = value.strip()
        try:
            return self._run("audit")
        except ValueError as error:
            return str(error)

    def cmd_draft(self) -> str:
        if not self.result:
            return "Load a page first with /audit."
        return self._run("draft")

    def cmd_report(self, args: list[str]) -> str:
        if not self.result:
            return "Load a page first with /audit."
        path = Path(args[0]) if args else Path("catalogready-report.html")
        path.write_text(render_html_report(self.result), encoding="utf-8")
        return f"Report written to {path}"

    def cmd_jsonld(self) -> str:
        if not self.result:
            return "Load a page first with /audit."
        from .agent.tools import build_product_jsonld

        node, _ = build_product_jsonld(self.result.get("evidence_record") or {})
        return json.dumps(node, indent=2, ensure_ascii=False)

    def cmd_provider(self, args: list[str]) -> str:
        if not args:
            configured = [item for item in provider_status() if item.get("configured")]
            names = ", ".join(item["provider"] for item in configured) or "none"
            return f"Current: {self.provider_name}. Configured via environment: {names}."
        self.provider_name = args[0]
        self.model = args[1] if len(args) > 1 else ""
        if self.provider_name == "deterministic":
            return "Free-text answers will use deterministic explanations."
        return (
            f"Free-text answers will use {self.provider_name}. Keys are read from "
            "server environment variables only."
        )

    # ---- free text --------------------------------------------------

    def _pillar_for(self, text: str) -> str | None:
        lowered = text.lower()
        for key, label in PILLAR_LABELS.items():
            if label.lower() in lowered or key.replace("_", " ") in lowered:
                return key
        return None

    def explain_pillar(self, key: str) -> str:
        readiness = (self.result or {}).get("readiness", {}).get("before") or {}
        section = (readiness.get("components") or {}).get(key)
        if not section:
            return f"No component named {key} in the current result."
        label = PILLAR_LABELS.get(key, key)
        lines = [f"{label}: {section.get('score')}/{section.get('max_score')}"]
        for check, passed in (section.get("checks") or {}).items():
            mark = "✓" if passed else "✗"
            lines.append(f"  {mark} {check.replace('_', ' ')}")
        failed = [check for check, passed in (section.get("checks") or {}).items() if not passed]
        if failed:
            lines.append("Points are lost on the ✗ checks above; /findings shows the fixes.")
        return "\n".join(lines)

    def deterministic_answer(self, text: str) -> str:
        if not self.result:
            return "Load a page first with /audit <url> [saved.html]."
        lowered = text.lower()
        pillar = self._pillar_for(lowered)
        if pillar:
            return self.explain_pillar(pillar)
        if any(term in lowered for term in ("fix", "improve", "next", "priorit")):
            plan = self.result.get("plan") or []
            if plan:
                lines = ["Highest-priority actions (severity-first):"]
                lines.extend(
                    f"  {item.get('priority')}. {item.get('action')} ({item.get('finding_rule_id')})"
                    for item in plan
                )
                return "\n".join(lines)
            return render_findings(self.result.get("findings") or [], self.use_color)
        if "score" in lowered or "why" in lowered:
            readiness = self.result.get("readiness", {}).get("before") or {}
            reasons = readiness.get("cap_reasons") or []
            lines = [render_score_card(self.result, use_color=self.use_color)]
            if reasons:
                lines.append("The score is capped because: " + " ".join(reasons))
            return "\n".join(lines)
        if "question" in lowered or "answer" in lowered:
            return render_questions(self.result.get("merchant_questions") or [], self.use_color)
        return (
            "I can explain pillars (e.g. 'why is structured data low?'), list fixes "
            "('what should I fix?'), or show /findings, /questions, /jsonld, /report. "
            "Configure /provider <name> for open-ended questions."
        )

    def model_answer(self, text: str) -> str:
        provider = create_provider(self.provider_name, self.model)
        if provider is None:
            return self.deterministic_answer(text)
        result = self.result or {}
        context = {
            "readiness": (result.get("readiness") or {}).get("before"),
            "findings": result.get("findings"),
            "merchant_questions": result.get("merchant_questions"),
            "product": (result.get("evidence_record") or {}).get("product"),
            "plan": result.get("plan"),
        }
        user = (
            f"Question: {text}\n\nAudit JSON:\n{json.dumps(context, ensure_ascii=False)}"
        )
        try:
            answer = provider.generate_json(_ASSISTANT_SYSTEM, user, _ANSWER_SCHEMA)
        except ProviderError as error:
            return f"Provider error: {error}. Falling back:\n{self.deterministic_answer(text)}"
        return str(answer.get("answer") or "").strip() or self.deterministic_answer(text)

    # ---- dispatch ---------------------------------------------------

    def handle(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        if line.startswith("/"):
            parts = line.split()
            command, args = parts[0].lower(), parts[1:]
            if command in {"/quit", "/exit", "/q"}:
                raise EOFError
            if command == "/help":
                return _HELP
            if command == "/audit":
                return self.cmd_audit(args)
            if command == "/answers":
                return self.cmd_answers(args)
            if command == "/draft":
                return self.cmd_draft()
            if command == "/questions":
                return render_questions((self.result or {}).get("merchant_questions") or [], self.use_color)
            if command == "/findings":
                return render_findings((self.result or {}).get("findings") or [], self.use_color)
            if command == "/score":
                return (
                    render_score_card(self.result, use_color=self.use_color)
                    if self.result
                    else "Load a page first with /audit."
                )
            if command == "/jsonld":
                return self.cmd_jsonld()
            if command == "/report":
                return self.cmd_report(args)
            if command == "/provider":
                return self.cmd_provider(args)
            if command == "/json":
                return json.dumps(self.result, indent=2, ensure_ascii=False) if self.result else "No result yet."
            return f"Unknown command {command}. Try /help."
        if re.match(r"^https?://", line):
            return self.cmd_audit(line.split())
        if self.provider_name != "deterministic":
            return self.model_answer(line)
        return self.deterministic_answer(line)


def main() -> None:
    try:
        import readline  # noqa: F401  (line editing and history when available)
    except ImportError:
        pass
    use_color = sys.stdout.isatty()
    session = ChatSession(use_color=use_color)
    print(_BANNER)
    while True:
        try:
            line = input("catalogready> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = session.handle(line)
        except EOFError:
            break
        except FileNotFoundError as error:
            output = f"File not found: {error.filename}"
        except (ValueError, OSError) as error:
            output = str(error)
        if output:
            print(output)


__all__ = ["ChatSession", "main"]
