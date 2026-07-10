"""Product JSON-LD parsing and evidence checks."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from catalogready.catalog.schemas import Finding, finding


def _nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _nodes(item)
    elif isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _nodes(graph)


def parse_json_ld(blocks: Iterable[str]) -> tuple[list[dict[str, Any]], int]:
    nodes: list[dict[str, Any]] = []
    invalid = 0
    for block in blocks:
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            invalid += 1
            continue
        nodes.extend(_nodes(parsed))
    return nodes, invalid


def _has_type(node: dict[str, Any], expected: str) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return expected in node_type
    return node_type == expected


def _price_value(offer: dict[str, Any]) -> float | None:
    raw = offer.get("price")
    if isinstance(raw, dict):
        raw = raw.get("price")
    try:
        return float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return None


def audit_product_structured_data(
    blocks: Iterable[str],
) -> tuple[dict[str, bool], list[Finding], dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    nodes, invalid = parse_json_ld(blocks)
    products = [node for node in nodes if _has_type(node, "Product")]
    offers = [node for node in nodes if _has_type(node, "Offer")]
    for product in products:
        product_offers = product.get("offers")
        if isinstance(product_offers, dict):
            offers.append(product_offers)
        elif isinstance(product_offers, list):
            offers.extend(item for item in product_offers if isinstance(item, dict))

    findings: list[Finding] = []
    if invalid:
        findings.append(
            finding(
                "SEO-JSONLD-001",
                "medium",
                "Invalid JSON-LD blocks",
                f"{invalid} JSON-LD blocks could not be parsed.",
                "Emit valid JSON and test the rendered page before publishing.",
            )
        )
    if not products:
        findings.append(
            finding(
                "GEO-PRODUCT-001",
                "medium",
                "Product structured data is missing",
                "No JSON-LD node with @type Product was found.",
                "Add Product data that matches the visible product page.",
            )
        )
    product_identity = bool(products and all(product.get("name") for product in products))
    if products and not product_identity:
        findings.append(
            finding(
                "GEO-PRODUCT-002",
                "medium",
                "Product structured data lacks a name",
                "At least one Product node has no name.",
                "Use the same verified product name shown to shoppers.",
            )
        )
    offer_complete = bool(
        offers
        and any(
            offer.get("price")
            and offer.get("priceCurrency")
            and offer.get("availability")
            for offer in offers
        )
    )
    if products and not offer_complete:
        findings.append(
            finding(
                "GEO-OFFER-001",
                "medium",
                "Offer data is incomplete",
                "No offer includes price, currency, and availability together.",
                "Align Offer fields with the visible price and availability.",
            )
        )

    priced = [value for value in (_price_value(offer) for offer in offers) if value is not None]
    if priced and max(priced) <= 0:
        findings.append(
            finding(
                "GEO-OFFER-002",
                "high",
                "Offer price is not greater than zero",
                f"The highest machine-readable offer price is {max(priced)}.",
                "Publish the real, current price; merchant listings require a price greater than zero.",
            )
        )

    return (
        {
            "product": bool(products),
            "product_identity": product_identity,
            "offer_complete": offer_complete,
        },
        findings,
        {"json_ld_nodes": len(nodes), "products": len(products), "offers": len(offers), "invalid_json_ld": invalid},
        products,
        offers,
    )

