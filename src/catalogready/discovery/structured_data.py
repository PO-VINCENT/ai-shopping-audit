"""Product JSON-LD parsing and evidence checks."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import date
from typing import Any

from catalogready.catalog.identifiers import is_valid_gtin
from catalogready.catalog.schemas import Finding, finding

# ISO 4217 active codes commonly seen in commerce feeds.
_ISO_4217 = {
    "AED", "ARS", "AUD", "BGN", "BHD", "BRL", "CAD", "CHF", "CLP", "CNY",
    "COP", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
    "INR", "JPY", "KRW", "KWD", "MAD", "MXN", "MYR", "NGN", "NOK", "NZD",
    "PEN", "PHP", "PKR", "PLN", "QAR", "RON", "RSD", "SAR", "SEK", "SGD",
    "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
}

_AVAILABILITY_VOCAB = {
    "instock", "outofstock", "preorder", "presale", "backorder",
    "discontinued", "limitedavailability", "instoreonly", "onlineonly",
    "soldout", "madetoorder", "reserved",
}

_GTIN_KEYS = ("gtin", "gtin8", "gtin12", "gtin13", "gtin14")


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

    bad_gtins = [
        str(product[key]).strip()
        for product in products
        for key in _GTIN_KEYS
        if product.get(key) and not is_valid_gtin(str(product[key]))
    ]
    if bad_gtins:
        findings.append(
            finding(
                "GEO-GTIN-001",
                "high",
                "GTIN fails GS1 validation",
                f"Invalid GTIN value(s): {', '.join(bad_gtins[:3])} (length or check digit).",
                "Publish the manufacturer-assigned GTIN exactly; an incorrect GTIN is a documented disapproval cause.",
            )
        )

    bad_currencies = sorted({
        str(offer.get("priceCurrency")).strip()
        for offer in offers
        if offer.get("priceCurrency")
        and str(offer.get("priceCurrency")).strip().upper() not in _ISO_4217
    })
    if bad_currencies:
        findings.append(
            finding(
                "GEO-CURRENCY-001",
                "medium",
                "priceCurrency is not a recognized ISO 4217 code",
                f"Unrecognized currency value(s): {', '.join(bad_currencies[:3])}.",
                "Use a three-letter ISO 4217 code (USD, EUR, AUD, …); agents cannot quote an offer without one.",
            )
        )

    bad_availability = sorted({
        str(offer.get("availability")).strip()
        for offer in offers
        if offer.get("availability")
        and re.sub(r"[^a-z]", "", str(offer.get("availability")).rsplit("/", 1)[-1].lower())
        not in _AVAILABILITY_VOCAB
    })
    if bad_availability:
        findings.append(
            finding(
                "GEO-AVAILABILITY-002",
                "medium",
                "availability is not a schema.org ItemAvailability value",
                f"Unrecognized availability value(s): {', '.join(bad_availability[:3])}.",
                "Use a schema.org value such as https://schema.org/InStock; free-text availability is not machine-readable.",
            )
        )

    expired = []
    for offer in offers:
        raw = str(offer.get("priceValidUntil") or "").strip()
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if not match:
            continue
        try:
            valid_until = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        if valid_until < date.today():
            expired.append(raw)
    if expired:
        findings.append(
            finding(
                "GEO-OFFER-004",
                "medium",
                "Offer priceValidUntil is in the past",
                f"priceValidUntil {', '.join(expired[:3])} has expired.",
                "Update or remove priceValidUntil; an expired offer date signals stale price data to agents.",
            )
        )

    offered_products = [
        product for product in products
        if product.get("offers") and not product.get("isVariantOf") and not product.get("inProductGroupWithID")
    ]
    if len(offered_products) > 1:
        names = [str(product.get("name", ""))[:40] for product in offered_products[:3]]
        findings.append(
            finding(
                "GEO-PRODUCT-004",
                "medium",
                "Multiple ungrouped Product offers on one page",
                f"{len(offered_products)} Product nodes carry offers without variant grouping (e.g. {', '.join(names)}).",
                "Keep one primary Product per page, or link variants with isVariantOf/inProductGroupWithID.",
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

