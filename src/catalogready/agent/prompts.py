"""Provider-neutral planning prompt for the bounded product agent."""

from __future__ import annotations

import json
from typing import Any


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "selected_rule_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "summary": {"type": "string"},
    },
    "required": ["selected_rule_ids", "summary"],
}


PLANNER_SYSTEM = """You plan a retail product-readiness audit using only the
supplied deterministic findings. Select up to five allowed rule IDs in priority
order. Prefer high-severity identity and offer failures, then structured data,
decision evidence, and images. Do not invent product facts, new findings, scores,
or fixes. Return JSON only."""


def planner_prompt(findings: list[dict[str, Any]]) -> str:
    compact = [
        {
            "rule_id": item.get("rule_id"),
            "severity": item.get("severity"),
            "title": item.get("title"),
            "recommendation": item.get("recommendation"),
        }
        for item in findings
    ]
    return "Select the highest-impact allowed findings:\n" + json.dumps(
        compact,
        ensure_ascii=False,
    )


__all__ = ["PLAN_SCHEMA", "PLANNER_SYSTEM", "planner_prompt"]
