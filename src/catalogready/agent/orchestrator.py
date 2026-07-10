"""Bounded tool-using orchestration for one product page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..model_providers import JsonModelProvider, create_provider
from .policy import (
    MAX_AGENT_STEPS,
    MAX_PLAN_ITEMS,
    blocking_questions,
    order_findings,
    validate_mode,
)
from .prompts import PLAN_SCHEMA, PLANNER_SYSTEM, planner_prompt
from .tools import (
    build_agent_findings,
    build_change_set,
    build_merchant_questions,
    inspect_product_page,
    merge_merchant_answers,
    score_product_readiness,
    validate_change_set,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _trace(
    events: list[dict[str, Any]],
    tool: str,
    status: str,
    summary: str,
) -> None:
    if len(events) >= MAX_AGENT_STEPS:
        raise RuntimeError("Agent exceeded its bounded step limit")
    events.append(
        {
            "step": len(events) + 1,
            "tool": tool,
            "status": status,
            "summary": summary,
        }
    )


def _deterministic_selection(findings: list[dict[str, Any]]) -> list[str]:
    return [
        str(item.get("rule_id"))
        for item in order_findings(findings)[:MAX_PLAN_ITEMS]
        if item.get("rule_id")
    ]


def _select_findings(
    findings: list[dict[str, Any]],
    provider: JsonModelProvider | None,
) -> tuple[list[str], str]:
    deterministic = _deterministic_selection(findings)
    if provider is None or not findings:
        return deterministic, "Deterministic severity-first planning was used."
    decision = provider.generate_json(
        PLANNER_SYSTEM,
        planner_prompt(findings),
        PLAN_SCHEMA,
    )
    allowed = {str(item.get("rule_id")) for item in findings}
    selected: list[str] = []
    for rule_id in decision.get("selected_rule_ids") or []:
        normalized = str(rule_id)
        if normalized in allowed and normalized not in selected:
            selected.append(normalized)
        if len(selected) >= MAX_PLAN_ITEMS:
            break
    return (
        selected or deterministic,
        str(decision.get("summary") or "Model-assisted priority planning was used."),
    )


def _build_plan(
    findings: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    provider: JsonModelProvider | None,
) -> tuple[list[dict[str, Any]], str]:
    selected, summary = _select_findings(findings, provider)
    by_rule = {str(item.get("rule_id")): item for item in findings}
    question_rules = {str(item.get("rule_id")) for item in questions}
    plan: list[dict[str, Any]] = []
    for rule_id in selected:
        item = by_rule[rule_id]
        plan.append(
            {
                "id": f"ACTION-{len(plan) + 1:02d}",
                "finding_rule_id": rule_id,
                "priority": len(plan) + 1,
                "action": item.get("recommendation", "Review the finding."),
                "reason": f"{str(item.get('severity', 'low')).title()} severity: {item.get('title', 'finding')}",
                "requires_merchant_input": rule_id in question_rules,
            }
        )
    return plan, summary


def run_product_agent_html(
    url: str,
    html: str,
    *,
    mode: str = "audit",
    provider_name: str = "deterministic",
    model: str = "",
    merchant_answers: dict[str, Any] | None = None,
    resumed_from: str = "",
) -> dict[str, Any]:
    """Run a bounded inspect-plan-draft-validate loop over supplied HTML."""

    resolved_mode = validate_mode(mode)
    events: list[dict[str, Any]] = []
    run_id = str(uuid4())

    inspection = inspect_product_page(url, html)
    source_evidence = inspection["evidence_record"]
    page_audit = inspection["page_audit"]
    claim_findings = inspection["claim_findings"]
    working_evidence = merge_merchant_answers(source_evidence, merchant_answers)
    _trace(
        events,
        "inspect_product_page",
        "completed",
        f"Extracted {len(working_evidence.get('evidence') or [])} evidence items from supplied HTML and merchant answers.",
    )

    before_readiness = score_product_readiness(source_evidence, page_audit, claim_findings)
    findings = build_agent_findings(working_evidence, page_audit, claim_findings)
    questions = build_merchant_questions(working_evidence)
    _trace(
        events,
        "audit_product",
        "completed",
        f"Measured readiness at {before_readiness['score']}/100 and produced {len(findings)} findings.",
    )

    provider = create_provider(provider_name, model)
    plan, planner_summary = _build_plan(findings, questions, provider)
    _trace(
        events,
        "plan_actions",
        "completed",
        f"Selected {len(plan)} bounded actions using {provider.name if provider else 'deterministic'} planning.",
    )

    if questions:
        _trace(
            events,
            "request_merchant_evidence",
            "waiting" if blocking_questions(questions) else "advisory",
            f"Prepared {len(questions)} questions for facts the agent cannot infer.",
        )

    changes: list[dict[str, Any]] = []
    validation: dict[str, Any] = {
        "status": "not_run",
        "accepted": False,
        "before_score": before_readiness["score"],
        "after_score": None,
        "score_delta": None,
        "preview_notice": "Draft validation runs only in draft mode.",
    }
    if resolved_mode == "draft":
        changes = build_change_set(url, working_evidence, page_audit)
        _trace(
            events,
            "build_change_set",
            "completed",
            f"Created {len(changes)} reversible changes using verified evidence only.",
        )
        if changes:
            validation_input = {
                **before_readiness,
                "findings": page_audit.get("findings") or [],
            }
            validation = validate_change_set(
                url,
                html,
                working_evidence,
                changes,
                validation_input,
                claim_findings,
            )
            _trace(
                events,
                "validate_change_set",
                validation["status"],
                f"Validated an isolated preview with a score delta of {validation['score_delta']:+d}.",
            )
        else:
            validation = {
                "status": "not_needed",
                "accepted": False,
                "before_score": before_readiness["score"],
                "after_score": before_readiness["score"],
                "score_delta": 0,
                "after_readiness": before_readiness,
                "preview_notice": "No evidence-backed page changes were available to validate.",
            }
            _trace(
                events,
                "validate_change_set",
                "not_needed",
                "No page change was justified by the deterministic findings.",
            )

    blocking = blocking_questions(questions)
    if blocking:
        status = "needs_input"
    elif resolved_mode == "audit":
        status = "completed"
    elif validation.get("accepted"):
        status = "ready_for_approval"
    elif not changes:
        status = "completed"
    else:
        status = "needs_review"

    return {
        "schema_version": "1.0",
        "operation": "run_product_readiness_agent",
        "run_id": run_id,
        "resumed_from": resumed_from or None,
        "created_at": _now(),
        "status": status,
        "mode": resolved_mode,
        "provider": {
            "planner": provider.name if provider else "deterministic",
            "model": provider.model if provider else "offline",
        },
        "input": {
            "url": url,
            "source": "supplied_html",
            "merchant_answer_fields": sorted((merchant_answers or {}).keys()),
        },
        "evidence_record": working_evidence,
        "current_audit": page_audit,
        "readiness": {
            "before": before_readiness,
            "validated_after": validation.get("after_readiness"),
        },
        "findings": findings,
        "plan": plan,
        "planner_summary": planner_summary,
        "merchant_questions": questions,
        "proposed_changes": changes,
        "validation": validation,
        "trace": events,
        "limits": {
            "max_steps": MAX_AGENT_STEPS,
            "steps_used": len(events),
            "storefront_writes_allowed": False,
        },
        "approval": {
            "required": bool(changes),
            "status": "pending" if changes else "not_applicable",
            "notice": "No storefront or feed was modified. Export and merchant approval are required before publishing.",
        },
    }


__all__ = ["run_product_agent_html"]
