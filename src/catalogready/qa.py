"""Answer free-text questions about an audit result.

Used by the terminal chat and the dashboard chat window. Deterministic
answers are composed only from the audit result. When a BYO provider is
named, the model answers instead — grounded strictly in the audit JSON —
and any provider failure falls back to the deterministic answer.
"""

from __future__ import annotations

import json
from typing import Any

from .model_providers import ProviderError, create_provider
from .reporting.html import PILLAR_LABELS

ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answer"],
    "additionalProperties": False,
    "properties": {"answer": {"type": "string"}},
}

ASSISTANT_SYSTEM = (
    "You are the CatalogReady audit assistant. Answer the merchant's question "
    "using ONLY the supplied audit JSON. Quote scores, rule IDs, and evidence "
    "from it. If the answer is not in the JSON, say exactly that. Never invent "
    "product facts, rankings, or guarantees."
)


def _readiness(result: dict[str, Any]) -> dict[str, Any]:
    return (result.get("readiness") or {}).get("before") or {}


def explain_pillar(result: dict[str, Any], key: str) -> str:
    section = (_readiness(result).get("components") or {}).get(key)
    if not section:
        return f"No component named {key} in the current result."
    label = PILLAR_LABELS.get(key, key)
    lines = [f"{label}: {section.get('score')}/{section.get('max_score')}"]
    for check, passed in (section.get("checks") or {}).items():
        mark = "✓" if passed else "✗"
        lines.append(f"  {mark} {check.replace('_', ' ')}")
    if any(not passed for passed in (section.get("checks") or {}).values()):
        lines.append("Points are lost on the ✗ checks above; the findings list shows the fixes.")
    return "\n".join(lines)


def _pillar_for(text: str) -> str | None:
    lowered = text.lower()
    for key, label in PILLAR_LABELS.items():
        if label.lower() in lowered or key.replace("_", " ") in lowered:
            return key
    return None


def _score_summary(result: dict[str, Any]) -> str:
    readiness = _readiness(result)
    lines = [
        f"CatalogReady Score: {readiness.get('score', 0)}/100 ({readiness.get('status', 'unknown')})."
    ]
    for key, section in (readiness.get("components") or {}).items():
        label = PILLAR_LABELS.get(key, key.replace("_", " ").title())
        lines.append(f"  {label}: {section.get('score')}/{section.get('max_score')}")
    reasons = readiness.get("cap_reasons") or []
    if reasons:
        lines.append(
            f"The score is capped at {readiness.get('safety_cap')} because: " + " ".join(reasons)
        )
    return "\n".join(lines)


def _questions_summary(result: dict[str, Any]) -> str:
    questions = result.get("merchant_questions") or []
    if not questions:
        return "No open merchant questions."
    lines = ["The agent needs these facts (it will not invent them):"]
    for item in questions:
        marker = "blocking" if item.get("blocking") else "advisory"
        lines.append(f"  [{marker}] {item.get('field', '')}: {item.get('question', '')}")
    return "\n".join(lines)


def _findings_summary(result: dict[str, Any]) -> str:
    findings = result.get("findings") or []
    if not findings:
        return "No findings. Everything checked is machine-readable."
    lines = []
    for severity in ("high", "medium", "low"):
        for item in findings:
            if item.get("severity") != severity:
                continue
            lines.append(
                f"[{severity.upper()}] {item.get('title', '')} ({item.get('rule_id', '')})"
                f" → {item.get('recommendation', '')}"
            )
    return "\n".join(lines)


def deterministic_answer(result: dict[str, Any], question: str) -> str:
    lowered = question.lower()
    pillar = _pillar_for(lowered)
    if pillar:
        return explain_pillar(result, pillar)
    if any(term in lowered for term in ("fix", "improve", "next", "priorit")):
        plan = result.get("plan") or []
        if plan:
            lines = ["Highest-priority actions (severity-first):"]
            lines.extend(
                f"  {item.get('priority')}. {item.get('action')} ({item.get('finding_rule_id')})"
                for item in plan
            )
            return "\n".join(lines)
        return _findings_summary(result)
    if "finding" in lowered:
        return _findings_summary(result)
    if "score" in lowered or "why" in lowered:
        return _score_summary(result)
    if "question" in lowered or "answer" in lowered:
        return _questions_summary(result)
    return (
        "I can explain pillars (e.g. 'why is structured data low?'), list fixes "
        "('what should I fix?'), findings, merchant questions, or the score. "
        "Select a model provider for open-ended questions."
    )


def answer_audit_question(
    audit_result: dict[str, Any],
    question: str,
    provider_name: str = "deterministic",
    model: str = "",
) -> dict[str, Any]:
    if not isinstance(audit_result, dict) or not audit_result:
        raise ValueError("audit_result must be a non-empty object")
    question = str(question or "").strip()
    if not question:
        raise ValueError("question is required")

    mode = "deterministic"
    provider = create_provider(provider_name, model)
    if provider is None:
        answer = deterministic_answer(audit_result, question)
    else:
        context = {
            "readiness": _readiness(audit_result),
            "findings": audit_result.get("findings"),
            "merchant_questions": audit_result.get("merchant_questions"),
            "product": (audit_result.get("evidence_record") or {}).get("product"),
            "plan": audit_result.get("plan"),
            "proposed_changes": audit_result.get("proposed_changes"),
            "validation": audit_result.get("validation"),
        }
        user = f"Question: {question}\n\nAudit JSON:\n{json.dumps(context, ensure_ascii=False)}"
        try:
            generated = provider.generate_json(ASSISTANT_SYSTEM, user, ANSWER_SCHEMA)
            answer = str(generated.get("answer") or "").strip()
            mode = provider.name
            if not answer:
                answer = deterministic_answer(audit_result, question)
                mode = "deterministic"
        except ProviderError as error:
            answer = (
                f"Provider error: {error}. Deterministic answer:\n"
                + deterministic_answer(audit_result, question)
            )
            mode = "deterministic_fallback"
    return {
        "schema_version": "1.0",
        "operation": "answer_audit_question",
        "mode": mode,
        "answer": answer,
    }


__all__ = ["answer_audit_question", "deterministic_answer", "explain_pillar"]
