"""Render a compact Markdown audit report from the shared result contract."""

from __future__ import annotations

from typing import Any


def render_markdown_report(audit_result: dict[str, Any]) -> str:
    lines = ["# CatalogReady audit report", ""]
    lines.append(f"Operation: `{audit_result.get('operation', 'unknown')}`")
    lines.append("")
    lines.append("## Scores")
    lines.append("")
    for name, section in (audit_result.get("scores") or {}).items():
        label = name.replace("_", " ").title()
        score = section.get("score")
        value = f"{score}/100" if score is not None else section.get("status", "not_run")
        lines.append(f"- {label}: {value}")
    lines.extend(["", "## Findings", ""])
    findings = audit_result.get("findings") or []
    if not findings:
        lines.append("No findings were produced for this operation.")
    for item in findings:
        lines.extend(
            [
                f"### [{str(item.get('severity', 'unknown')).upper()}] {item.get('title', 'Finding')}",
                "",
                f"- Rule: `{item.get('rule_id', 'unknown')}`",
                f"- Evidence: {item.get('evidence', '')}",
                f"- Recommendation: {item.get('recommendation', '')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
