"""Transparent publish-readiness scoring for generated listings.

The headline score is computed only from source evidence and claim
grounding. Completeness of content that CatalogReady generated itself
(journey stages, queries, listing sections) is reported separately as
`generation_quality` and never contributes points, so the tool cannot
raise a score by grading its own output.
"""

from __future__ import annotations

from typing import Any


def _ratio(passed: int, total: int, weight: int) -> int:
    return round(weight * passed / total) if total else 0


def score_optimization(
    evidence_record: dict[str, Any],
    journey: dict[str, Any],
    draft: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    product = evidence_record.get("product") or {}
    listing = draft.get("listing") or {}
    claims = evaluation.get("claims") or []

    supported = sum(1 for item in claims if item.get("status") == "supported")
    grounding = _ratio(supported, len(claims), 50) if claims else 0

    price = product.get("price") or {}
    feed_checks = [
        bool(product.get("id") or product.get("sku") or product.get("url")),
        bool(product.get("title")),
        bool(product.get("description")),
        bool(product.get("brand")),
        bool(product.get("images")),
        bool(price.get("amount") and price.get("currency")),
        bool(product.get("availability")),
    ]
    feed_readiness = _ratio(sum(feed_checks), len(feed_checks), 30)

    images = product.get("images") or []
    image_checks = [bool(images), len(images) >= 2]
    image_readiness = _ratio(sum(image_checks), len(image_checks), 10)

    title = str(listing.get("title", ""))
    description = str(listing.get("description", ""))
    clarity_checks = [
        0 < len(title) <= 150,
        0 < len(description) <= 5000,
        not any(term in title.lower() for term in ("free shipping", "buy now", "#1")),
    ]
    clarity = _ratio(sum(clarity_checks), len(clarity_checks), 10)

    components = {
        "evidence_grounding": grounding,
        "feed_structured_data": feed_readiness,
        "image_readiness": image_readiness,
        "clarity_compliance": clarity,
    }

    stages = journey.get("stages") or []
    queries = journey.get("queries") or []
    listing_checks = [
        bool(listing.get("title")),
        bool(listing.get("description")),
        len(listing.get("bullets") or []) >= 3,
        len(listing.get("faq") or []) >= 2,
        bool(listing.get("limitations")),
    ]
    generation_quality = {
        "notice": "Generated-content completeness is informational and never adds score points.",
        "journey_query_coverage": _ratio(
            min(len(stages), 6) + min(len(queries), 20),
            26,
            100,
        ),
        "listing_completeness": _ratio(sum(listing_checks), len(listing_checks), 100),
    }

    raw_score = sum(components.values())
    cap = 100
    cap_reasons: list[str] = []
    for item in claims:
        if item.get("status") == "contradicted" or (
            item.get("status") in {"unsupported", "requires_human_review"}
            and item.get("risk") == "high"
        ):
            cap = min(cap, 49)
            cap_reasons.append("A contradicted or unsupported high-risk claim blocks publishing.")
    if not (price.get("amount") and price.get("currency")) or not product.get("availability"):
        cap = min(cap, 79)
        cap_reasons.append("Price or availability evidence is incomplete.")
    total = min(raw_score, cap)
    return {
        "score": total,
        "status": "publish_ready" if total >= 80 and cap == 100 else "needs_review",
        "components": components,
        "generation_quality": generation_quality,
        "raw_score": raw_score,
        "safety_cap": cap,
        "cap_reasons": sorted(set(cap_reasons)),
        "observed_ai_visibility": {
            "status": "not_measured",
            "score": None,
            "notice": "Observed visibility requires repeated, timestamped provider responses after publishing.",
        },
    }


__all__ = ["score_optimization"]
