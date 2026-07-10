"""Small, explicit apparel taxonomy profile for the initial release."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .schemas import Finding, finding


APPAREL_ATTRIBUTE_PROFILE: dict[str, tuple[str, ...]] = {
    "shoes": ("color", "size", "gender", "age_group", "material"),
    "shirts": ("color", "size", "gender", "age_group", "material"),
    "pants": ("color", "size", "gender", "age_group", "material"),
    "dresses": ("color", "size", "gender", "age_group", "material"),
    "jackets": ("color", "size", "gender", "age_group", "material"),
}


def normalize_category(value: str) -> str | None:
    lowered = " ".join(value.lower().replace("_", " ").replace("-", " ").split())
    aliases = {
        "shoe": "shoes",
        "footwear": "shoes",
        "shirt": "shirts",
        "top": "shirts",
        "trousers": "pants",
        "trouser": "pants",
        "dress": "dresses",
        "jacket": "jackets",
        "coat": "jackets",
    }
    if lowered in APPAREL_ATTRIBUTE_PROFILE:
        return lowered
    return aliases.get(lowered)


def infer_category(row: Mapping[str, str]) -> str | None:
    for field in ("product_type", "category", "google_product_category"):
        normalized = normalize_category(str(row.get(field, "")))
        if normalized:
            return normalized
    haystack = f"{row.get('title', '')} {row.get('description', '')}".lower()
    for category in APPAREL_ATTRIBUTE_PROFILE:
        singular = category[:-1] if category.endswith("s") else category
        if category in haystack or singular in haystack:
            return category
    return None


def audit_taxonomy(rows: Iterable[Mapping[str, str]]) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    category_counts: dict[str, int] = {}
    uncategorized = 0
    missing_attribute_counts: dict[str, int] = {}

    for row in rows:
        category = infer_category(row)
        if not category:
            uncategorized += 1
            continue
        category_counts[category] = category_counts.get(category, 0) + 1
        for attribute in APPAREL_ATTRIBUTE_PROFILE[category]:
            if not str(row.get(attribute, "")).strip():
                missing_attribute_counts[attribute] = missing_attribute_counts.get(attribute, 0) + 1

    total = sum(category_counts.values()) + uncategorized
    if uncategorized:
        findings.append(
            finding(
                "CAT-TAXONOMY-001",
                "medium",
                "Products cannot be mapped to the apparel profile",
                f"{uncategorized} of {total} products have no recognizable apparel category.",
                "Supply a verified product_type or category value before attribute enrichment.",
            )
        )

    for attribute, count in sorted(missing_attribute_counts.items()):
        findings.append(
            finding(
                f"CAT-ATTR-{attribute.upper()}",
                "low",
                f"Category attribute is incomplete: {attribute}",
                f"{count} categorized products have no `{attribute}` value.",
                "Populate the attribute only when it is supported by catalog or page evidence.",
            )
        )

    return findings, category_counts

