"""End-to-end customer journey, listing generation, evaluation, and scoring."""

from __future__ import annotations

from typing import Any

from ..model_providers import create_provider
from .evaluation import evaluate_claims
from .evidence import evidence_from_csv, evidence_from_html, evidence_from_shopify
from .journey import build_journey
from .prompts import GENERATOR_SYSTEM, LISTING_SCHEMA, generator_prompt
from .scoring import score_optimization
from .shopify import fetch_shopify_product


def _fallback_draft(evidence_record: dict[str, Any]) -> dict[str, Any]:
    product = evidence_record.get("product") or {}
    evidence = {item["id"]: item for item in evidence_record.get("evidence") or []}
    bullets: list[str] = []
    claims: list[dict[str, Any]] = []
    if product.get("title") and "product.title" in evidence:
        claims.append(
            {
                "text": str(product["title"]),
                "evidence_ids": ["product.title"],
                "risk": "low",
            }
        )
    if product.get("description") and "product.description" in evidence:
        claims.append(
            {
                "text": str(product["description"]),
                "evidence_ids": ["product.description"],
                "risk": "medium",
            }
        )
    for item in evidence_record.get("evidence") or []:
        if str(item.get("id", "")).startswith("spec."):
            label = str(item.get("field", "Specification")).split(".", 1)[-1]
            text = f"{label}: {item.get('value', '')}"
            bullets.append(text)
            claims.append({"text": text, "evidence_ids": [item["id"]], "risk": "low"})
        if len(bullets) >= 5:
            break
    if not bullets and product.get("brand"):
        text = f"Brand: {product['brand']}"
        bullets.append(text)
        claims.append({"text": text, "evidence_ids": ["product.brand"], "risk": "low"})

    faq: list[dict[str, Any]] = []
    price = product.get("price") or {}
    if price.get("amount"):
        value = f"{price.get('amount')} {price.get('currency', '')}".strip()
        faq.append(
            {
                "question": f"What is the listed price of {product.get('title', 'this product')}?",
                "answer": f"The supplied product evidence lists the price as {value}.",
                "evidence_ids": [item for item in ("offer.price", "offer.currency") if item in evidence],
            }
        )
        claims.append(
            {
                "text": f"The listed price is {value}.",
                "evidence_ids": [item for item in ("offer.price", "offer.currency") if item in evidence],
                "risk": "high",
            }
        )
    if product.get("availability"):
        faq.append(
            {
                "question": "What availability does the source currently report?",
                "answer": f"The source reports {str(product['availability']).replace('_', ' ')}.",
                "evidence_ids": ["offer.availability"],
            }
        )
        claims.append(
            {
                "text": f"The source reports {str(product['availability']).replace('_', ' ')}.",
                "evidence_ids": ["offer.availability"],
                "risk": "high",
            }
        )

    missing = [
        field
        for field in ("category", "brand", "description", "images", "availability")
        if not product.get(field)
    ]
    if not (price.get("amount") and price.get("currency")):
        missing.append("price")
    image_briefs = []
    if product.get("images"):
        image_briefs.append(
            {
                "purpose": "Supporting lifestyle image",
                "prompt": "Place the exact referenced product in a simple category-appropriate real-world setting.",
                "fidelity_rules": [
                    "Use the real product image as the visual reference.",
                    "Do not change color, shape, logo, proportions, or included items.",
                    "Do not add unverified capabilities or promotional text.",
                    "Preserve required AI-generated image metadata on export.",
                ],
            }
        )
    return {
        "listing": {
            "title": str(product.get("title", "")),
            "short_title": str(product.get("title", ""))[:70],
            "bullets": bullets,
            "description": str(product.get("description", "")),
            "best_for": [],
            "limitations": [
                "Only facts present in the supplied evidence are included; confirm missing use-case and limitation information."
            ],
            "faq": faq,
            "alt_text": str(product.get("title", "Product image")),
            "image_briefs": image_briefs,
        },
        "claims": claims,
        "missing_information": missing,
    }


def _normalize_draft(draft: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    listing = draft.get("listing")
    if not isinstance(listing, dict):
        listing = {}
    fallback_listing = fallback["listing"]
    for field in (
        "title",
        "short_title",
        "bullets",
        "description",
        "best_for",
        "limitations",
        "faq",
        "alt_text",
        "image_briefs",
    ):
        if field not in listing or listing[field] is None:
            listing[field] = fallback_listing[field]
    claims = draft.get("claims")
    if not isinstance(claims, list):
        claims = fallback["claims"]
    missing = draft.get("missing_information")
    if not isinstance(missing, list):
        missing = fallback["missing_information"]
    return {"listing": listing, "claims": claims, "missing_information": missing}


def optimize_evidence(
    evidence_record: dict[str, Any],
    *,
    provider_name: str = "deterministic",
    model: str = "",
    evaluator_provider_name: str = "",
    evaluator_model: str = "",
    market: str = "en-AU",
    target_customer_types: list[str] | None = None,
) -> dict[str, Any]:
    product = evidence_record.get("product")
    if not isinstance(product, dict):
        raise ValueError("evidence_record.product must be an object")
    journey = build_journey(
        product,
        market=market,
        target_customer_types=target_customer_types,
    )
    fallback = _fallback_draft(evidence_record)
    generator = create_provider(provider_name, model)
    if generator is None:
        draft = fallback
    else:
        generated = generator.generate_json(
            GENERATOR_SYSTEM,
            generator_prompt(evidence_record, journey),
            LISTING_SCHEMA,
        )
        draft = _normalize_draft(generated, fallback)
    evaluator_name = evaluator_provider_name.strip() or provider_name
    evaluator_resolved_model = evaluator_model.strip() or model
    evaluator = create_provider(evaluator_name, evaluator_resolved_model)
    evaluation = evaluate_claims(evidence_record, draft, evaluator)
    score = score_optimization(evidence_record, journey, draft, evaluation)
    return {
        "schema_version": "1.0",
        "operation": "optimize_product_visibility",
        "provider": {
            "generator": generator.name if generator else "deterministic",
            "generator_model": generator.model if generator else "offline",
            "evaluator": evaluator.name if evaluator else "deterministic",
            "evaluator_model": evaluator.model if evaluator else "offline",
        },
        "evidence_record": evidence_record,
        "journey": journey,
        "draft": draft,
        "evaluation": evaluation,
        "readiness": score,
        "approval": {
            "required": True,
            "status": "merchant_review_required",
            "notice": "No storefront or feed was modified.",
        },
    }


def optimize_product_html(
    url: str,
    html: str,
    **options: Any,
) -> dict[str, Any]:
    return optimize_evidence(evidence_from_html(url, html), **options)


def optimize_product_csv(
    csv_text: str,
    row_index: int = 0,
    **options: Any,
) -> dict[str, Any]:
    return optimize_evidence(evidence_from_csv(csv_text, row_index), **options)


def optimize_shopify_payload(
    product_data: dict[str, Any],
    shop_domain: str = "",
    **options: Any,
) -> dict[str, Any]:
    return optimize_evidence(evidence_from_shopify(product_data, shop_domain), **options)


def optimize_shopify_live(
    shop_domain: str,
    product_query: str,
    **options: Any,
) -> dict[str, Any]:
    product = fetch_shopify_product(shop_domain, product_query)
    return optimize_shopify_payload(product, shop_domain, **options)


__all__ = [
    "optimize_evidence",
    "optimize_product_csv",
    "optimize_product_html",
    "optimize_shopify_live",
    "optimize_shopify_payload",
]
