"""Deterministic tools available to the product-readiness agent."""

from __future__ import annotations

import copy
import html as html_module
import json
import re
from typing import Any

from ..catalog.schemas import finding
from ..discovery.content_evidence import extract_page_signals
from ..discovery.scoring import audit_page_html
from ..optimization.claims import audit_listing_claims
from ..optimization.evidence import evidence_from_html
from ..optimization.readiness import score_page_readiness


_ANSWER_FIELDS = {
    "id",
    "title",
    "description",
    "category",
    "brand",
    "sku",
    "gtin",
    "mpn",
    "url",
    "image",
    "price",
    "currency",
    "availability",
}


def inspect_product_page(url: str, html: str) -> dict[str, Any]:
    """Extract the canonical evidence record, page audit, and claim findings."""

    evidence_record = evidence_from_html(url, html)
    claim_findings, claim_summary = audit_listing_claims(evidence_record)
    return {
        "evidence_record": evidence_record,
        "page_audit": audit_page_html(url, html),
        "claim_findings": claim_findings,
        "claim_summary": claim_summary,
    }


def _clean_answer(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _set_evidence(
    record: dict[str, Any],
    evidence_id: str,
    field: str,
    value: Any,
) -> None:
    cleaned = _clean_answer(value)
    evidence = record.setdefault("evidence", [])
    evidence[:] = [item for item in evidence if item.get("id") != evidence_id]
    if cleaned:
        evidence.append(
            {
                "id": evidence_id,
                "field": field,
                "value": cleaned,
                "source": "merchant_answer",
            }
        )


def merge_merchant_answers(
    evidence_record: dict[str, Any],
    merchant_answers: dict[str, Any] | None,
) -> dict[str, Any]:
    """Add explicit merchant answers without treating them as page observations."""

    record = copy.deepcopy(evidence_record)
    answers = merchant_answers or {}
    if not isinstance(answers, dict):
        raise ValueError("merchant_answers must be an object")
    unsupported = sorted(set(answers) - _ANSWER_FIELDS)
    if unsupported:
        raise ValueError(f"Unsupported merchant answer fields: {', '.join(unsupported)}")

    product = record.setdefault("product", {})
    price = product.setdefault("price", {"amount": "", "currency": ""})
    for field, raw_value in answers.items():
        if field == "image":
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            images = [_clean_answer(value) for value in values if _clean_answer(value)]
            product["images"] = images
            record["evidence"] = [
                item
                for item in record.get("evidence") or []
                if not str(item.get("id", "")).startswith("image.")
            ]
            for index, value in enumerate(images, 1):
                _set_evidence(record, f"image.{index}", "image", value)
        elif field == "price":
            value = _clean_answer(raw_value)
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            price["amount"] = match.group(0).replace(",", ".") if match else value
            _set_evidence(record, "offer.price", "price", price["amount"])
        elif field == "currency":
            price["currency"] = _clean_answer(raw_value).upper()
            _set_evidence(record, "offer.currency", "currency", price["currency"])
        elif field == "availability":
            value = _clean_answer(raw_value).lower().replace(" ", "_")
            product[field] = value
            _set_evidence(record, "offer.availability", field, value)
        else:
            value = _clean_answer(raw_value)
            product[field] = value
            _set_evidence(record, f"product.{field}", field, value)
    if answers:
        record["source"] = {
            **(record.get("source") or {}),
            "merchant_answers_supplied": sorted(answers),
        }
    return record


def score_product_readiness(
    evidence_record: dict[str, Any],
    page_audit: dict[str, Any],
    claim_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score only observable or explicitly supplied product evidence."""

    return score_page_readiness(evidence_record, page_audit, claim_findings)


def _missing_finding(
    rule_id: str,
    severity: str,
    title: str,
    field_name: str,
    recommendation: str,
) -> dict[str, Any]:
    return finding(
        rule_id,
        severity,  # type: ignore[arg-type]
        title,
        f"No verified `{field_name}` value is present in the supplied evidence.",
        recommendation,
        source="agent_deterministic_rule",
    )


def build_agent_findings(
    evidence_record: dict[str, Any],
    page_audit: dict[str, Any],
    claim_findings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    product = evidence_record.get("product") or {}
    price = product.get("price") or {}
    findings = [copy.deepcopy(item) for item in page_audit.get("findings") or []]
    findings.extend(copy.deepcopy(item) for item in claim_findings or [])
    additions: list[dict[str, Any]] = []
    if not (product.get("id") or product.get("sku") or product.get("gtin") or product.get("mpn")):
        additions.append(_missing_finding("AGENT-IDENTITY-001", "high", "Stable product identity is missing", "id/sku/gtin/mpn", "Supply a verified stable product or variant identifier."))
    if not product.get("brand"):
        additions.append(_missing_finding("AGENT-BRAND-001", "medium", "Brand evidence is missing", "brand", "Confirm the merchant or manufacturer brand."))
    if not product.get("category"):
        additions.append(_missing_finding("AGENT-CATEGORY-001", "medium", "Product category is missing", "category", "Supply a verified merchant category or taxonomy path."))
    if not price.get("amount"):
        additions.append(_missing_finding("AGENT-OFFER-PRICE", "high", "Price evidence is missing", "price", "Supply the current verified price."))
    if not price.get("currency"):
        additions.append(_missing_finding("AGENT-OFFER-CURRENCY", "high", "Currency evidence is missing", "currency", "Supply the ISO 4217 price currency."))
    if not product.get("availability"):
        additions.append(_missing_finding("AGENT-OFFER-AVAILABILITY", "high", "Availability evidence is missing", "availability", "Supply the current verified availability state."))
    if not product.get("images"):
        additions.append(_missing_finding("AGENT-IMAGE-001", "medium", "Primary product image is missing", "image", "Supply the canonical product image URL."))
    if not product.get("description"):
        additions.append(_missing_finding("AGENT-DESCRIPTION-001", "medium", "Product description evidence is missing", "description", "Supply a factual merchant-approved description."))

    seen = {str(item.get("rule_id")) for item in findings}
    findings.extend(item for item in additions if item["rule_id"] not in seen)
    return findings


def build_merchant_questions(evidence_record: dict[str, Any]) -> list[dict[str, Any]]:
    product = evidence_record.get("product") or {}
    price = product.get("price") or {}
    questions: list[dict[str, Any]] = []

    def ask(
        field: str,
        rule_id: str,
        question: str,
        reason: str,
        blocking: bool,
    ) -> None:
        questions.append(
            {
                "id": f"MQ-{len(questions) + 1:02d}",
                "field": field,
                "rule_id": rule_id,
                "question": question,
                "reason": reason,
                "blocking": blocking,
            }
        )

    if not (product.get("id") or product.get("sku") or product.get("gtin") or product.get("mpn")):
        ask("sku", "AGENT-IDENTITY-001", "What verified SKU or stable product identifier should be used?", "A stable identity is required to distinguish the product or variant.", True)
    if not price.get("amount"):
        ask("price", "AGENT-OFFER-PRICE", "What is the current verified product price?", "The agent cannot create an Offer without a merchant-supplied price.", True)
    if not price.get("currency"):
        ask("currency", "AGENT-OFFER-CURRENCY", "What ISO currency code applies to the price?", "Price requires an explicit currency such as AUD or USD.", True)
    if not product.get("availability"):
        ask("availability", "AGENT-OFFER-AVAILABILITY", "What is the current availability state?", "Availability must come from merchant evidence.", True)
    if not product.get("brand"):
        ask("brand", "AGENT-BRAND-001", "What verified brand or manufacturer should be shown?", "The page has no reliable brand evidence.", False)
    if not product.get("category"):
        ask("category", "AGENT-CATEGORY-001", "What merchant category or taxonomy path describes this product?", "Category improves product classification but must not be inferred.", False)
    if not product.get("images"):
        ask("image", "AGENT-IMAGE-001", "What is the canonical primary product image URL?", "The agent will not invent or substitute a product image.", False)
    if not product.get("description"):
        ask("description", "AGENT-DESCRIPTION-001", "What factual merchant-approved description can be used?", "A description cannot be generated without source facts.", False)
    return questions


def build_product_jsonld(evidence_record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    product = evidence_record.get("product") or {}
    price = product.get("price") or {}
    evidence_ids = {str(item.get("id")) for item in evidence_record.get("evidence") or []}
    node: dict[str, Any] = {"@context": "https://schema.org", "@type": "Product"}
    used: list[str] = []

    def add(key: str, value: Any, evidence_id: str) -> None:
        if value not in (None, "", [], {}):
            node[key] = value
            if evidence_id in evidence_ids:
                used.append(evidence_id)

    add("productID", product.get("id"), "product.id")
    add("name", product.get("title"), "product.title")
    add("description", product.get("description"), "product.description")
    add("category", product.get("category"), "product.category")
    add("sku", product.get("sku"), "product.sku")
    add("gtin", product.get("gtin"), "product.gtin")
    add("mpn", product.get("mpn"), "product.mpn")
    add("url", product.get("url"), "product.url")
    if product.get("brand"):
        node["brand"] = {"@type": "Brand", "name": product["brand"]}
        if "product.brand" in evidence_ids:
            used.append("product.brand")
    if product.get("images"):
        node["image"] = list(product["images"])
        used.extend(sorted(item for item in evidence_ids if item.startswith("image.")))
    specifications = product.get("specifications") or []
    if specifications:
        node["additionalProperty"] = [
            {
                "@type": "PropertyValue",
                "name": str(item.get("name", "")),
                "value": str(item.get("value", "")),
            }
            for item in specifications
            if isinstance(item, dict) and item.get("name") and item.get("value")
        ]
        used.extend(sorted(item for item in evidence_ids if item.startswith("spec.")))
    if price.get("amount") or price.get("currency") or product.get("availability"):
        offer: dict[str, Any] = {"@type": "Offer"}
        if price.get("amount"):
            offer["price"] = price["amount"]
            used.append("offer.price")
        if price.get("currency"):
            offer["priceCurrency"] = price["currency"]
            used.append("offer.currency")
        if product.get("availability"):
            availability = str(product["availability"]).replace("_", "").lower()
            availability_map = {
                "instock": "InStock",
                "outofstock": "OutOfStock",
                "preorder": "PreOrder",
                "backorder": "BackOrder",
            }
            offer["availability"] = "https://schema.org/" + availability_map.get(
                availability,
                str(product["availability"]),
            )
            used.append("offer.availability")
        node["offers"] = offer
    return node, sorted(set(used))


def build_change_set(
    url: str,
    evidence_record: dict[str, Any],
    page_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    product = evidence_record.get("product") or {}
    summary = page_audit.get("summary") or {}
    changes: list[dict[str, Any]] = []
    node, evidence_ids = build_product_jsonld(evidence_record)
    structured_rule_ids = {
        "GEO-PRODUCT-001",
        "GEO-PRODUCT-002",
        "GEO-OFFER-001",
        "SEO-JSONLD-001",
    }
    current_rule_ids = {
        str(item.get("rule_id")) for item in page_audit.get("findings") or []
    }
    if product.get("title") and structured_rule_ids & current_rule_ids:
        changes.append(
            {
                "id": "CHANGE-001",
                "operation": "replace_product_jsonld",
                "target": "head",
                "value": node,
                "evidence_ids": evidence_ids,
                "reversible": True,
                "status": "proposed",
            }
        )
    if summary.get("canonical") != url:
        changes.append(
            {
                "id": f"CHANGE-{len(changes) + 1:03d}",
                "operation": "set_canonical",
                "target": "head",
                "value": url,
                "evidence_ids": ["product.url"] if "product.url" in evidence_ids else [],
                "reversible": True,
                "status": "proposed",
            }
        )
    if not summary.get("description") and product.get("description"):
        changes.append(
            {
                "id": f"CHANGE-{len(changes) + 1:03d}",
                "operation": "set_meta_description",
                "target": "head",
                "value": product["description"],
                "evidence_ids": ["product.description"],
                "reversible": True,
                "status": "proposed",
            }
        )
    coverage = summary.get("evidence_coverage") or {}
    if not coverage.get("specifications") and product.get("specifications"):
        changes.append(
            {
                "id": f"CHANGE-{len(changes) + 1:03d}",
                "operation": "append_visible_specifications",
                "target": "product_content",
                "value": [
                    {"name": item.get("name"), "value": item.get("value")}
                    for item in product["specifications"]
                    if isinstance(item, dict)
                ],
                "evidence_ids": sorted(item for item in evidence_ids if item.startswith("spec.")),
                "reversible": True,
                "status": "proposed",
            }
        )
    return changes


def _change_value(changes: list[dict[str, Any]], operation: str, fallback: Any) -> Any:
    for change in changes:
        if change.get("operation") == operation:
            return change.get("value")
    return fallback


def build_validation_preview(
    url: str,
    html: str,
    evidence_record: dict[str, Any],
    changes: list[dict[str, Any]],
) -> str:
    """Create an isolated preview; this never mutates the merchant page."""

    signals = extract_page_signals(html)
    product = evidence_record.get("product") or {}
    title = product.get("title") or signals.title or "Product"
    canonical = _change_value(changes, "set_canonical", signals.canonical or url)
    description = _change_value(
        changes,
        "set_meta_description",
        signals.description or product.get("description", ""),
    )
    jsonld, _ = build_product_jsonld(evidence_record)
    jsonld = _change_value(changes, "replace_product_jsonld", jsonld)
    body_parts = [signals.visible_text]
    specifications = _change_value(changes, "append_visible_specifications", [])
    if specifications:
        body_parts.append("Specifications")
        body_parts.extend(
            f"{item.get('name', '')}: {item.get('value', '')}"
            for item in specifications
            if isinstance(item, dict)
        )
    robots = (
        f'<meta name="robots" content="{html_module.escape(signals.robots)}">'
        if signals.robots
        else ""
    )
    return "".join(
        [
            "<html><head>",
            f"<title>{html_module.escape(str(title))}</title>",
            f'<link rel="canonical" href="{html_module.escape(str(canonical), quote=True)}">',
            f'<meta name="description" content="{html_module.escape(str(description), quote=True)}">',
            robots,
            '<script type="application/ld+json">',
            json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"),
            "</script></head><body><main>",
            html_module.escape(" ".join(body_parts)),
            "</main></body></html>",
        ]
    )


def validate_change_set(
    url: str,
    html: str,
    evidence_record: dict[str, Any],
    changes: list[dict[str, Any]],
    before_readiness: dict[str, Any],
    claim_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    preview = build_validation_preview(url, html, evidence_record, changes)
    after_audit = audit_page_html(url, preview)
    after_readiness = score_product_readiness(evidence_record, after_audit, claim_findings)
    before_high = sum(
        item.get("severity") == "high"
        for item in (before_readiness.get("findings") or [])
    )
    after_high = sum(
        item.get("severity") == "high"
        for item in after_audit.get("findings") or []
    )
    accepted = bool(changes) and (
        after_readiness["score"] >= before_readiness["score"]
        and after_high <= before_high
    )
    return {
        "status": "validated" if accepted else "needs_review",
        "accepted": accepted,
        "before_score": before_readiness["score"],
        "after_score": after_readiness["score"],
        "score_delta": after_readiness["score"] - before_readiness["score"],
        "after_readiness": after_readiness,
        "after_audit": after_audit,
        "preview_notice": "Validation used an isolated in-memory preview; no storefront was modified.",
    }


__all__ = [
    "build_agent_findings",
    "build_change_set",
    "build_merchant_questions",
    "build_product_jsonld",
    "build_validation_preview",
    "inspect_product_page",
    "merge_merchant_answers",
    "score_product_readiness",
    "validate_change_set",
]
