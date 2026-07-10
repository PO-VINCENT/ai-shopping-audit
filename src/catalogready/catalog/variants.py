"""Variant identity and consistency checks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

from .schemas import Finding, finding


def audit_variants(rows: Iterable[Mapping[str, str]]) -> tuple[list[Finding], dict[str, int]]:
    materialized = list(rows)
    findings: list[Finding] = []
    ids: dict[str, int] = defaultdict(int)
    groups: dict[str, list[Mapping[str, str]]] = defaultdict(list)

    for row in materialized:
        product_id = str(row.get("id", "")).strip()
        if product_id:
            ids[product_id] += 1
        group_id = str(row.get("item_group_id", "")).strip()
        if group_id:
            groups[group_id].append(row)

    duplicate_ids = sorted(product_id for product_id, count in ids.items() if count > 1)
    if duplicate_ids:
        findings.append(
            finding(
                "CAT-IDENTITY-001",
                "high",
                "Duplicate product identifiers",
                f"Duplicate IDs: {', '.join(duplicate_ids[:10])}.",
                "Assign a stable, unique ID to every exported product or variant.",
            )
        )

    ambiguous_groups = 0
    inconsistent_brand_groups = 0
    for group_rows in groups.values():
        if len(group_rows) < 2:
            continue
        titles = [str(row.get("title", "")).strip().lower() for row in group_rows]
        colors = {str(row.get("color", "")).strip().lower() for row in group_rows if str(row.get("color", "")).strip()}
        if len(set(titles)) == 1 and len(colors) > 1:
            ambiguous_groups += 1
        brands = {str(row.get("brand", "")).strip().lower() for row in group_rows if str(row.get("brand", "")).strip()}
        if len(brands) > 1:
            inconsistent_brand_groups += 1

    if ambiguous_groups:
        findings.append(
            finding(
                "CAT-VARIANT-003",
                "medium",
                "Variant titles omit distinguishing attributes",
                f"{ambiguous_groups} item groups reuse one title across multiple colors.",
                "Add verified color or size terms while keeping a consistent parent-product identity.",
            )
        )
    if inconsistent_brand_groups:
        findings.append(
            finding(
                "CAT-VARIANT-004",
                "high",
                "Variant groups contain inconsistent brands",
                f"{inconsistent_brand_groups} item groups contain more than one brand.",
                "Correct group membership or normalize the verified brand value.",
            )
        )

    return findings, {
        "variant_groups": len(groups),
        "ambiguous_title_groups": ambiguous_groups,
        "inconsistent_brand_groups": inconsistent_brand_groups,
        "duplicate_ids": len(duplicate_ids),
    }

