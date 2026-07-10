"""Agent limits, state rules, and deterministic action ordering."""

from __future__ import annotations

from typing import Any


MAX_AGENT_STEPS = 8
MAX_PLAN_ITEMS = 5
ALLOWED_MODES = {"audit", "draft"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def validate_mode(mode: str) -> str:
    normalized = mode.strip().lower() or "audit"
    if normalized not in ALLOWED_MODES:
        raise ValueError("mode must be `audit` or `draft`")
    return normalized


def order_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a stable, severity-first finding order for planning."""

    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "low")), 3),
            str(item.get("rule_id", "")),
        ),
    )


def blocking_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [question for question in questions if question.get("blocking") is True]


__all__ = [
    "ALLOWED_MODES",
    "MAX_AGENT_STEPS",
    "MAX_PLAN_ITEMS",
    "blocking_questions",
    "order_findings",
    "validate_mode",
]
