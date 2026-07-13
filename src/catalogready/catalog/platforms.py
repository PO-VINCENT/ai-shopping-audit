"""Rule → platform relevance mapping (single source of truth).

Each platform score counts only findings whose rules trace to that
platform's documented requirements (sources in docs/RULES.md). Unmapped
rules are universal: field presence, claim integrity, and basic page
hygiene matter to every AI shopping surface. The assignments are a
CatalogReady convention informed by the cited platform documentation.
"""

from __future__ import annotations

PLATFORMS = ("openai", "google", "microsoft", "anthropic", "perplexity")

PLATFORM_LABELS = {
    "openai": "OpenAI",
    "google": "Google",
    "microsoft": "Microsoft Bing",
    "anthropic": "Anthropic",
    "perplexity": "Perplexity",
}

PLATFORM_SURFACES = {
    "openai": ("ChatGPT search", "ChatGPT shopping"),
    "google": ("Merchant listings", "Google Shopping", "AI Overviews", "AI Mode"),
    "microsoft": ("Bing search", "Microsoft Shopping", "Copilot"),
    "anthropic": ("Claude",),
    "perplexity": ("Perplexity",),
}

_ALL = PLATFORMS
_MARKUP = ("google", "microsoft")  # documented JSON-LD consumers

_EXACT: dict[str, tuple[str, ...]] = {
    # Crawler access is inherently per-platform.
    "SEO-ROBOTS-GOOGLEBOT": ("google",),
    "SEO-ROBOTS-BINGBOT": ("microsoft",),
    "SEO-ROBOTS-OAI_SEARCHBOT": ("openai",),
    "SEO-ROBOTS-PERPLEXITYBOT": ("perplexity",),
    "SEO-ROBOTS-CLAUDE_SEARCHBOT": ("anthropic",),
    # Snippet/caching controls gate Copilot grounding and AI Overviews.
    "SEO-SNIPPET-001": ("google", "microsoft"),
    "SEO-SITEMAP-001": _MARKUP,
    "SEO-SITEMAP-002": _MARKUP,
    # Structured-data rules: Google merchant listings + Bing validated markup.
    "GEO-PRODUCT-001": _MARKUP,
    "GEO-PRODUCT-002": _MARKUP,
    "GEO-PRODUCT-004": _MARKUP,
    "SEO-JSONLD-001": _MARKUP,
    "GEO-OFFER-001": _MARKUP,
    "GEO-OFFER-003": _MARKUP,
    "GEO-OFFER-004": _MARKUP,
    "GEO-CURRENCY-001": _MARKUP,
    "GEO-AVAILABILITY-002": _MARKUP,
    "GEO-VARIANT-001": _MARKUP,
    "GEO-RETURNS-002": ("google",),
    "GEO-SHIPPING-002": ("google",),
    # Identifiers and condition: GMC/MMC disapprovals; ACP carries gtin too.
    "GEO-GTIN-001": ("google", "microsoft", "openai"),
    "GEO-CONDITION-001": ("google", "microsoft", "openai"),
    "GEO-RATING-001": ("google", "microsoft", "openai"),
    # Checkout trust: ACP checkout eligibility, MMC store review, Google UCP.
    "GEO-POLICY-001": ("openai", "google", "microsoft"),
    "GEO-SELLER-001": ("openai", "google", "microsoft", "perplexity"),
    # Shipping facts: Perplexity merchant data, Google recommended, ACP.
    "GEO-SHIPPING-001": ("openai", "google", "microsoft", "perplexity"),
}


def platforms_for(rule_id: str) -> tuple[str, ...]:
    return _EXACT.get(str(rule_id or ""), _ALL)


__all__ = ["PLATFORMS", "PLATFORM_LABELS", "PLATFORM_SURFACES", "platforms_for"]
