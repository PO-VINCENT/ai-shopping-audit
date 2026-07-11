"""Page-quality rules collected from platform documentation.

Each rule's source is documented in docs/RULES.md. All checks are
deterministic and offline: they read only the supplied HTML signals and
parsed JSON-LD nodes.
"""

from __future__ import annotations

import re
from typing import Any

from catalogready.catalog.schemas import Finding, finding

from .content_evidence import PageSignals

_PROMO_TERMS = ("free shipping", "buy now", "sale!", "% off", "best price", "order today")

_SNIPPET_BLOCKERS = ("noarchive", "nocache", "nosnippet", "max-snippet:0", "max-snippet: 0")

_REVIEW_PATTERN = re.compile(r"\b\d[\d,]*\s+(?:customer\s+)?reviews?\b|\bcustomer reviews\b", re.IGNORECASE)

_INJECTION_PATTERNS = (
    r"ignore (?:all )?(?:previous|prior|above) (?:instructions|prompts)",
    r"disregard (?:your|all|previous) (?:instructions|guidelines)",
    r"you are an ai (?:assistant|agent|model)",
    r"as an ai (?:assistant|agent|model),? (?:you must|always|recommend)",
    r"system prompt",
    r"always (?:recommend|choose|rank) this (?:product|item|store)",
    r"do not (?:mention|recommend) (?:any )?(?:other|competitor)",
)


def _variant_signals(product: dict[str, Any]) -> bool:
    return bool(product.get("color") or product.get("size") or product.get("pattern"))


def _has_variant_grouping(product: dict[str, Any]) -> bool:
    return bool(product.get("inProductGroupWithID") or product.get("isVariantOf"))


def _image_urls(product: dict[str, Any]) -> list[str]:
    value = product.get("image")
    values = value if isinstance(value, list) else [value]
    urls: list[str] = []
    for item in values:
        if isinstance(item, dict):
            item = item.get("url") or item.get("contentUrl")
        if item:
            urls.append(str(item))
    return urls


def _price_texts(offers: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for offer in offers:
        raw = offer.get("price")
        if isinstance(raw, dict):
            raw = raw.get("price")
        if raw not in (None, ""):
            texts.append(str(raw))
    return texts


def _price_on_page(price: str, page_text: str) -> bool:
    normalized = price.replace(",", "")
    candidates = {normalized, normalized.rstrip("0").rstrip("."), normalized.split(".")[0]}
    haystack = page_text.replace(",", "")
    return any(candidate and candidate in haystack for candidate in candidates)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def audit_page_quality(
    signals: PageSignals,
    products: list[dict[str, Any]],
    offers: list[dict[str, Any]],
    coverage: dict[str, bool],
) -> list[Finding]:
    findings: list[Finding] = []
    text = signals.visible_text
    lowered = text.lower()

    # GEO-PRODUCT-003 — the markup name is what agents read; it must match
    # the visible page. Catches feed-artifact names like "Brand 1EA".
    page_haystack = _normalize(f"{signals.title} {text}")
    for product in products:
        name = product.get("name")
        if not isinstance(name, str) or len(name.strip()) < 3:
            continue
        if _normalize(name) not in page_haystack:
            findings.append(
                finding(
                    "GEO-PRODUCT-003",
                    "medium",
                    "Product name in markup does not match the visible page",
                    f"JSON-LD names the product “{name.strip()}”, which does not appear in the page title or text.",
                    "Use the real, shopper-facing product name in structured data; agents read the markup name, not the page.",
                )
            )
            break

    # GEO-OFFER-003 — markup price should be visible on the page.
    prices = _price_texts(offers)
    if prices and signals.visible_words >= 30 and not any(
        _price_on_page(price, text) for price in prices
    ):
        findings.append(
            finding(
                "GEO-OFFER-003",
                "low",
                "Machine-readable price is not visible in the page text",
                f"No offer price ({', '.join(prices[:3])}) appears in the supplied HTML text.",
                "Confirm the visible price matches the markup; mismatches are a documented disapproval cause.",
            )
        )

    # GEO-RETURNS-001 — returns information in markup or on the page.
    has_return_markup = any(
        offer.get("hasMerchantReturnPolicy") for offer in offers
    ) or any(product.get("hasMerchantReturnPolicy") for product in products)
    if products and not has_return_markup and not coverage.get("returns"):
        findings.append(
            finding(
                "GEO-RETURNS-001",
                "medium",
                "Return policy is missing",
                "No hasMerchantReturnPolicy markup and no visible returns information were found.",
                "State the return policy on the page; AI shopping feeds require a return policy.",
            )
        )

    # GEO-SHIPPING-001 — shipping information in markup or on the page.
    has_shipping_markup = any(offer.get("shippingDetails") for offer in offers)
    if products and not has_shipping_markup and not coverage.get("shipping"):
        findings.append(
            finding(
                "GEO-SHIPPING-001",
                "low",
                "Shipping information is missing",
                "No shippingDetails markup and no visible shipping information were found.",
                "State shipping cost and time on the page or add machine-readable shippingDetails.",
            )
        )

    # GEO-IMAGE-001 — image URLs must be absolute, crawlable http(s) URLs.
    bad_images = [
        url
        for product in products
        for url in _image_urls(product)
        if not url.startswith(("http://", "https://"))
    ]
    if bad_images:
        findings.append(
            finding(
                "GEO-IMAGE-001",
                "low",
                "Product image URLs are not crawlable absolute URLs",
                f"Non-absolute image references: {', '.join(bad_images[:3])}.",
                "Publish absolute http(s) image URLs that crawlers can fetch and index.",
            )
        )

    # GEO-VARIANT-001 — variant attributes without variant-group markup.
    for product in products:
        if _variant_signals(product) and not _has_variant_grouping(product):
            findings.append(
                finding(
                    "GEO-VARIANT-001",
                    "low",
                    "Variant attributes lack variant-group markup",
                    "The Product declares color/size/pattern but no inProductGroupWithID or isVariantOf.",
                    "Link variants with inProductGroupWithID or isVariantOf so agents group them correctly.",
                )
            )
            break

    # GEO-RATING-001 — visible review counts without AggregateRating markup.
    has_rating_markup = any(product.get("aggregateRating") for product in products)
    if products and not has_rating_markup and _REVIEW_PATTERN.search(text):
        findings.append(
            finding(
                "GEO-RATING-001",
                "low",
                "Visible reviews lack AggregateRating markup",
                "The page text mentions reviews but no aggregateRating is machine-readable.",
                "Publish AggregateRating with ratingValue and reviewCount matching the visible reviews.",
            )
        )

    # SEO-TITLE-002 — title length, promo text, shouting.
    title = signals.title
    if title:
        problems = []
        if len(title) > 150:
            problems.append(f"{len(title)} characters (limit 150)")
        promo = [term for term in _PROMO_TERMS if term in title.lower()]
        if promo:
            problems.append(f"promotional text ({', '.join(promo)})")
        letters = [char for char in title if char.isalpha()]
        if len(letters) >= 12 and sum(char.isupper() for char in letters) / len(letters) > 0.8:
            problems.append("mostly capital letters")
        if problems:
            findings.append(
                finding(
                    "SEO-TITLE-002",
                    "medium",
                    "Title violates product-title conventions",
                    f"The title has {'; '.join(problems)}.",
                    "Use a plain, accurate product title: no promotions, no all-caps, at most 150 characters.",
                )
            )

    # SEO-SNIPPET-001 — snippet/caching restrictions silently degrade AI answers.
    robots = signals.robots.replace(" ", "")
    blockers = [token for token in _SNIPPET_BLOCKERS if token.replace(" ", "") in robots]
    if blockers:
        findings.append(
            finding(
                "SEO-SNIPPET-001",
                "medium",
                "Snippet or caching restrictions limit AI answers",
                f"robots meta contains: {', '.join(sorted(set(blockers)))}.",
                "Remove noarchive/nocache/nosnippet unless intentional; they reduce or block Copilot citations.",
            )
        )

    # CLAIM-INJECTION-001 — text aimed at manipulating AI agents.
    injected = [
        pattern
        for pattern in _INJECTION_PATTERNS
        if re.search(pattern, lowered)
    ]
    if injected:
        match = re.search(injected[0], lowered)
        findings.append(
            finding(
                "CLAIM-INJECTION-001",
                "high",
                "Page text attempts to manipulate AI agents",
                f"Prompt-injection-style text found: “{match.group(0) if match else injected[0]}”.",
                "Remove instructions aimed at AI systems; platforms treat this as abuse and may delist the page.",
            )
        )

    return findings


__all__ = ["audit_page_quality"]
