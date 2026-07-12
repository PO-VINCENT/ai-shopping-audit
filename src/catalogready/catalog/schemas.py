"""Shared catalog audit schemas and result helpers."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from .metrics import metric_for

Severity = Literal["low", "medium", "high"]
ScoreStatus = Literal["measured", "not_run", "unavailable"]


class Finding(TypedDict):
    rule_id: str
    severity: Severity
    title: str
    evidence: str
    recommendation: str
    source: str
    metric: str


class ScoreSection(TypedDict):
    score: int | None
    status: ScoreStatus


def finding(
    rule_id: str,
    severity: Severity,
    title: str,
    evidence: str,
    recommendation: str,
    *,
    source: str = "deterministic_rule",
) -> Finding:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
        "source": source,
        "metric": metric_for(rule_id),
    }


def percent(passed: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(100 * passed / total)


def scores(
    *,
    catalog: int | None = None,
    discovery: int | None = None,
    visibility: int | None = None,
) -> dict[str, ScoreSection]:
    return {
        "catalog_readiness": {
            "score": catalog,
            "status": "measured" if catalog is not None else "not_run",
        },
        "discovery_readiness": {
            "score": discovery,
            "status": "measured" if discovery is not None else "not_run",
        },
        "observed_ai_visibility": {
            "score": visibility,
            "status": "measured" if visibility is not None else "not_run",
        },
    }


def result(
    operation: str,
    input_data: dict[str, Any],
    result_scores: dict[str, ScoreSection],
    summary: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "operation": operation,
        "input": input_data,
        "scores": result_scores,
        "summary": summary,
        "findings": findings,
    }

