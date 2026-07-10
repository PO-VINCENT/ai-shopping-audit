"""Deterministic claim-risk rules for merchant listing copy.

Claims are only read from the listing surface (title and description).
Grounding evidence is read from structured data, specifications, review
data, and extracted page-evidence topics. The rules never call a model
and never invent product facts.
"""

from __future__ import annotations

import re
from typing import Any

from catalogready.catalog.schemas import Finding, finding


_SUPERLATIVE_PATTERNS = (
    r"#\s?1\b",
    r"\bworld'?s (?:best|leading|first)\b",
    r"\bbest[- ]selling\b",
    r"\bthe best\b",
    r"\bnumber one\b",
    r"\bmarket[- ]leading\b",
)

_RATED_PATTERNS = (
    r"\btop[- ]rated\b",
    r"\bhighest[- ]rated\b",
    r"\bfive[- ]star\b",
    r"\b5[- ]star\b",
)

_PROOF_PATTERNS = (
    r"\bclinically (?:proven|tested)\b",
    r"\bscientifically proven\b",
    r"\bdoctor (?:recommended|approved)\b",
    r"\bdermatologist (?:recommended|tested)\b",
    r"\bmedical[- ]grade\b",
    r"\bfda[- ](?:approved|cleared)\b",
    r"\blab[- ](?:tested|certified)\b",
)

_WARRANTY_PATTERNS = (
    r"\blifetime (?:warranty|guarantee)\b",
    r"\b\d+[- ](?:year|month)s?[- ](?:warranty|guarantee)\b",
    r"\bmoney[- ]back guarantee\b",
)

_PERFORMANCE_PATTERNS = (
    r"\bwaterproof\b",
    r"\bwater[- ]resistant\b",
    r"\bunbreakable\b",
    r"\bindestructible\b",
    r"\bscratch[- ]proof\b",
    r"\bstain[- ]proof\b",
    r"\bfire[- ](?:proof|resistant)\b",
    r"\bhypoallergenic\b",
    r"\bantibacterial\b",
    r"\bnon[- ]toxic\b",
    r"\b100%\s+\w+",
)


def _matches(patterns: tuple[str, ...], text: str) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            phrase = re.sub(r"\s+", " ", match.group(0)).strip()
            if phrase.lower() not in {item.lower() for item in found}:
                found.append(phrase)
    return found


def _quote(phrases: list[str]) -> str:
    return ", ".join(f"“{phrase}”" for phrase in phrases[:5])


def _grounded(phrases: list[str], evidence_text: str) -> tuple[list[str], list[str]]:
    grounded: list[str] = []
    ungrounded: list[str] = []
    for phrase in phrases:
        key = re.sub(r"[^a-z0-9 ]", "", phrase.lower()).strip()
        tokens = [token for token in key.split() if len(token) > 3]
        if tokens and all(token in evidence_text for token in tokens):
            grounded.append(phrase)
        else:
            ungrounded.append(phrase)
    return grounded, ungrounded


def audit_listing_claims(evidence_record: dict[str, Any]) -> tuple[list[Finding], dict[str, Any]]:
    """Flag risky marketing claims in the listing copy that lack evidence."""

    product = evidence_record.get("product") or {}
    listing_text = " ".join(
        str(product.get(field) or "") for field in ("title", "description")
    )
    review = product.get("review_summary") or {}
    has_review_evidence = bool(review.get("rating") and review.get("count"))

    evidence_parts: list[str] = []
    for item in evidence_record.get("evidence") or []:
        identifier = str(item.get("id", ""))
        if identifier.startswith(("spec.", "page.", "review.")):
            evidence_parts.append(str(item.get("value", "")))
    evidence_text = re.sub(r"[^a-z0-9 ]", " ", " ".join(evidence_parts).lower())

    findings: list[Finding] = []
    risky = 0
    grounded_total = 0

    superlatives = _matches(_SUPERLATIVE_PATTERNS, listing_text)
    if superlatives:
        risky += len(superlatives)
        findings.append(
            finding(
                "CLAIM-SUPERLATIVE-001",
                "medium",
                "Unverifiable superlative claims in listing copy",
                f"The title or description states {_quote(superlatives)} without citable support.",
                "Remove rank claims or replace them with specific, verifiable product facts.",
            )
        )

    rated = _matches(_RATED_PATTERNS, listing_text)
    if rated and not has_review_evidence:
        risky += len(rated)
        findings.append(
            finding(
                "CLAIM-RATING-001",
                "medium",
                "Rating claims lack review evidence",
                f"The listing states {_quote(rated)} but no aggregate rating and review count were found.",
                "Publish machine-readable AggregateRating data or remove the rating claim.",
            )
        )
    elif rated:
        grounded_total += len(rated)

    proof = _matches(_PROOF_PATTERNS, listing_text)
    if proof:
        grounded, ungrounded = _grounded(proof, evidence_text)
        grounded_total += len(grounded)
        if ungrounded:
            risky += len(ungrounded)
            findings.append(
                finding(
                    "CLAIM-PROOF-001",
                    "high",
                    "Scientific or medical claims lack evidence",
                    f"The listing states {_quote(ungrounded)} with no supporting evidence on the page.",
                    "Cite the specific test, certification, or approval on the page, or remove the claim.",
                )
            )

    warranty = _matches(_WARRANTY_PATTERNS, listing_text)
    if warranty:
        has_warranty_evidence = any(
            str(item.get("id")) == "page.warranty"
            for item in evidence_record.get("evidence") or []
        )
        if has_warranty_evidence:
            grounded_total += len(warranty)
        else:
            risky += len(warranty)
            findings.append(
                finding(
                    "CLAIM-WARRANTY-001",
                    "high",
                    "Warranty or guarantee claims lack page evidence",
                    f"The listing states {_quote(warranty)} but no warranty terms appear on the page.",
                    "State the warranty terms on the page or remove the guarantee claim.",
                )
            )

    performance = _matches(_PERFORMANCE_PATTERNS, listing_text)
    if performance:
        grounded, ungrounded = _grounded(performance, evidence_text)
        grounded_total += len(grounded)
        if ungrounded:
            risky += len(ungrounded)
            findings.append(
                finding(
                    "CLAIM-PERFORMANCE-001",
                    "medium",
                    "Performance claims lack supporting evidence",
                    f"The listing states {_quote(ungrounded)} without matching specification or page evidence.",
                    "Back each performance claim with a specification, standard, or visible product fact.",
                )
            )

    summary = {
        "risky_claims": risky,
        "grounded_claims": grounded_total,
        "claim_findings": len(findings),
    }
    return findings, summary


__all__ = ["audit_listing_claims"]
