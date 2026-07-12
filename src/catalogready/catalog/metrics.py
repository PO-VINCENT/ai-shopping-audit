"""Rule → measurement-metric mapping (single source of truth).

Every finding is stamped with one of eight metrics (docs/METRICS.md).
Metrics are diagnostic status, never a second score. Exact rule IDs are
matched first, then prefix families, so parameterized rules
(CAT-VALUE-*, SEO-ROBOTS-*) and future rules classify predictably.
"""

from __future__ import annotations

METRICS = (
    "machine_readability",
    "validity",
    "completeness",
    "consistency",
    "trust",
    "accessibility",
    "transactability",
    "freshness",
)

_EXACT = {
    # machine readability — can a parser extract the product at all?
    "GEO-PRODUCT-001": "machine_readability",
    "GEO-PRODUCT-002": "machine_readability",
    "SEO-JSONLD-001": "machine_readability",
    "SEO-LANG-001": "machine_readability",
    "GEO-EVIDENCE-001": "machine_readability",
    # validity — is the data well-formed against its standard?
    "GEO-GTIN-001": "validity",
    "GEO-CURRENCY-001": "validity",
    "GEO-AVAILABILITY-002": "validity",
    "GEO-OFFER-002": "validity",
    # completeness — are the fields agents require present?
    "GEO-EVIDENCE-002": "completeness",
    "GEO-RETURNS-001": "completeness",
    "GEO-SHIPPING-001": "completeness",
    "GEO-RATING-001": "completeness",
    # consistency — does the markup match reality?
    "GEO-PRODUCT-003": "consistency",
    "GEO-OFFER-003": "consistency",
    "CAT-IDENTITY-001": "consistency",
    "CAT-VARIANT-003": "consistency",
    "CAT-VARIANT-004": "consistency",
    "CAT-TAXONOMY-001": "consistency",
    # trust & claim integrity
    "SEO-TITLE-002": "trust",
    # agent accessibility — can crawlers reach and cite it?
    "SEO-ROBOTS-001": "accessibility",
    "SEO-SNIPPET-001": "accessibility",
    "SEO-CANONICAL-001": "accessibility",
    "SEO-CANONICAL-002": "accessibility",
    "SEO-CANONICAL-003": "accessibility",
    "SEO-SITEMAP-001": "accessibility",
    "SEO-SITEMAP-002": "accessibility",
    "SEO-TITLE-001": "accessibility",
    "SEO-DESC-001": "accessibility",
    "SEO-HTTPS-001": "accessibility",
    "GEO-IMAGE-001": "accessibility",
    "GEO-IMAGE-002": "accessibility",
    # transactability — could an agent complete a purchase?
    "GEO-POLICY-001": "transactability",
    "GEO-SELLER-001": "transactability",
    "GEO-RETURNS-002": "transactability",
    "GEO-SHIPPING-002": "transactability",
    "GEO-CONDITION-001": "transactability",
    "GEO-PRODUCT-004": "transactability",
    "GEO-VARIANT-001": "transactability",
    # freshness — is the data current?
    "GEO-OFFER-004": "freshness",
    "SEO-INDEXNOW-001": "freshness",
}

_PREFIX = (
    ("CAT-COLUMN-", "completeness"),
    ("CAT-VALUE-", "completeness"),
    ("CAT-ATTR-", "completeness"),
    ("SEO-ROBOTS-", "accessibility"),
    ("AGENT-", "completeness"),
    ("CLAIM-", "trust"),
)

_FAMILY_FALLBACK = {
    "CAT": "consistency",
    "SEO": "accessibility",
    "GEO": "machine_readability",
}


def metric_for(rule_id: str) -> str:
    rule_id = str(rule_id or "")
    if rule_id in _EXACT:
        return _EXACT[rule_id]
    for prefix, metric in _PREFIX:
        if rule_id.startswith(prefix):
            return metric
    return _FAMILY_FALLBACK.get(rule_id.split("-", 1)[0], "machine_readability")


__all__ = ["METRICS", "metric_for"]
