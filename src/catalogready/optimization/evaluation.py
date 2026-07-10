"""Deterministic and optional model-assisted claim evaluation."""

from __future__ import annotations

import json
import re
from typing import Any

from ..model_providers import JsonModelProvider, ProviderError
from .prompts import EVALUATION_SCHEMA, EVALUATOR_SYSTEM, evaluator_prompt


_HIGH_RISK_WORDS = {
    "best",
    "fastest",
    "safest",
    "guaranteed",
    "perfect",
    "medical",
    "clinically",
    "certified",
    "compatible",
    "warranty",
    "waterproof",
    "eco-friendly",
    "sustainable",
}


def _numbers(text: str) -> set[str]:
    return {match.replace(",", ".") for match in re.findall(r"\d+(?:[.,]\d+)?", text)}


def _listing_statements(draft: dict[str, Any]) -> list[str]:
    listing = draft.get("listing") or {}
    statements: list[str] = []
    for field in ("bullets", "best_for", "limitations"):
        statements.extend(str(item).strip() for item in listing.get(field) or [] if str(item).strip())
    for item in listing.get("faq") or []:
        if isinstance(item, dict) and str(item.get("answer", "")).strip():
            statements.append(str(item["answer"]).strip())
    description = str(listing.get("description", ""))
    statements.extend(part.strip() for part in re.split(r"(?<=[.!?])\s+", description) if part.strip())
    return statements


def _claim_covers_statement(claim_text: str, statement: str) -> bool:
    claim_words = set(re.findall(r"[a-z0-9]+", claim_text.lower()))
    statement_words = set(re.findall(r"[a-z0-9]+", statement.lower()))
    if not claim_words or not statement_words:
        return False
    overlap = len(claim_words & statement_words) / min(len(claim_words), len(statement_words))
    same_numbers = not _numbers(statement) or _numbers(statement).issubset(_numbers(claim_text))
    return overlap >= 0.55 and same_numbers


def _deterministic_claims(
    evidence_record: dict[str, Any],
    draft: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence = {
        str(item.get("id")): str(item.get("value", ""))
        for item in evidence_record.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    evaluations: list[dict[str, Any]] = []
    for claim in draft.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text", "")).strip()
        ids = [str(item) for item in claim.get("evidence_ids") or []]
        missing_ids = [item for item in ids if item not in evidence]
        cited_text = " ".join(evidence.get(item, "") for item in ids)
        claim_numbers = _numbers(text)
        cited_numbers = _numbers(cited_text)
        risky = {word for word in _HIGH_RISK_WORDS if word in text.lower()}
        status = "supported"
        reason = "All cited evidence IDs exist."
        if not ids:
            status = "unsupported"
            reason = "The claim has no evidence IDs."
        elif missing_ids:
            status = "unsupported"
            reason = f"Unknown evidence IDs: {', '.join(missing_ids)}"
        elif claim_numbers and not claim_numbers.issubset(cited_numbers):
            status = "unsupported"
            reason = "A numeric value in the claim is absent from its cited evidence."
        elif risky and not any(word in cited_text.lower() for word in risky):
            status = "requires_human_review"
            reason = "A high-risk or comparative term is not explicit in the cited evidence."
        evaluations.append(
            {
                "text": text,
                "status": status,
                "reason": reason,
                "evidence_ids": ids,
                "risk": "high" if risky else str(claim.get("risk", "low")),
                "evaluator": "deterministic",
            }
        )
    declared_text = [item["text"] for item in evaluations]
    watched_terms = _HIGH_RISK_WORDS | {"price", "in stock", "out of stock", "available", "unavailable"}
    for statement in _listing_statements(draft):
        lower = statement.lower()
        if not (_numbers(statement) or any(term in lower for term in watched_terms)):
            continue
        if any(_claim_covers_statement(claim, statement) for claim in declared_text):
            continue
        high_risk = any(term in lower for term in _HIGH_RISK_WORDS)
        evaluations.append(
            {
                "text": statement,
                "status": "unsupported",
                "reason": "A high-signal listing statement was not declared in the claim ledger.",
                "evidence_ids": [],
                "risk": "high" if high_risk else "medium",
                "evaluator": "deterministic_claim_coverage",
            }
        )
    return evaluations


def evaluate_claims(
    evidence_record: dict[str, Any],
    draft: dict[str, Any],
    evaluator: JsonModelProvider | None = None,
) -> dict[str, Any]:
    deterministic = _deterministic_claims(evidence_record, draft)
    notes: list[str] = []
    model_evaluation: dict[str, Any] | None = None
    if evaluator is not None and deterministic:
        try:
            model_evaluation = evaluator.generate_json(
                EVALUATOR_SYSTEM,
                evaluator_prompt(evidence_record, draft),
                EVALUATION_SCHEMA,
            )
        except ProviderError as exc:
            notes.append(f"Model evaluator unavailable: {exc}")

    if model_evaluation:
        by_text = {
            str(item.get("text", "")): item
            for item in model_evaluation.get("claims") or []
            if isinstance(item, dict)
        }
        severity = {
            "supported": 0,
            "partially_supported": 1,
            "requires_human_review": 2,
            "unsupported": 3,
            "contradicted": 4,
        }
        for item in deterministic:
            model_item = by_text.get(item["text"])
            if not model_item:
                continue
            model_status = str(model_item.get("status", "requires_human_review"))
            if severity.get(model_status, 2) > severity.get(item["status"], 2):
                item["status"] = model_status
                item["reason"] = str(model_item.get("reason", item["reason"]))
                item["evaluator"] = f"deterministic+{evaluator.name}"
        notes.extend(str(item) for item in model_evaluation.get("overall_notes") or [])

    counts: dict[str, int] = {}
    for item in deterministic:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "claims": deterministic,
        "counts": counts,
        "notes": notes,
        "evaluator_provider": evaluator.name if evaluator else "deterministic",
        "audit_payload_sha256": __import__("hashlib").sha256(
            json.dumps(draft, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


__all__ = ["evaluate_claims"]
