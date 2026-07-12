"""Catalog CSV orchestration and scoring."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .schemas import Finding, finding, percent, result, scores
from .taxonomy import audit_taxonomy
from .variants import audit_variants


REQUIRED_CATALOG_FIELDS = (
    "id",
    "title",
    "description",
    "link",
    "image_link",
    "price",
    "availability",
    "brand",
)


def audit_catalog(catalog_path: str) -> dict[str, Any]:
    path = Path(catalog_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Catalog file does not exist: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("The reference implementation currently supports CSV only.")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        rows = list(reader)

    findings: list[Finding] = []
    missing_columns = [field for field in REQUIRED_CATALOG_FIELDS if field not in headers]
    for field_name in missing_columns:
        findings.append(
            finding(
                f"CAT-COLUMN-{field_name.upper()}",
                "high",
                f"Required field is missing: {field_name}",
                f"The CSV header does not contain `{field_name}`.",
                f"Add a `{field_name}` column populated from verified merchant data.",
            )
        )

    total_checks = len(rows) * len(REQUIRED_CATALOG_FIELDS)
    passed_checks = 0
    missing_values = {field_name: 0 for field_name in REQUIRED_CATALOG_FIELDS}
    for row in rows:
        for field_name in REQUIRED_CATALOG_FIELDS:
            if field_name in headers and str(row.get(field_name, "")).strip():
                passed_checks += 1
            else:
                missing_values[field_name] += 1

    for field_name, count in missing_values.items():
        if count and field_name not in missing_columns:
            findings.append(
                finding(
                    f"CAT-VALUE-{field_name.upper()}",
                    "high" if count == len(rows) else "medium",
                    f"Missing values in {field_name}",
                    f"{count} of {len(rows)} products have no `{field_name}` value.",
                    "Populate only values supported by the source catalog or product page.",
                )
            )

    taxonomy_findings, category_counts = audit_taxonomy(rows)
    variant_findings, variant_summary = audit_variants(rows)
    findings.extend(taxonomy_findings)
    findings.extend(variant_findings)

    score, breakdown = _score_catalog(passed_checks, total_checks, findings)
    return result(
        "audit_catalog",
        {"catalog_path": str(path)},
        scores(catalog=score),
        {
            "products": len(rows),
            "required_fields": len(REQUIRED_CATALOG_FIELDS),
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "categories": category_counts,
            **variant_summary,
            "findings": len(findings),
            "score_breakdown": breakdown,
        },
        findings,
    )


_SEVERITY_DEDUCTIONS = {"high": 10, "medium": 5, "low": 2}

# Structural defects that make a feed unsafe to rely on cap the score,
# so a mostly-filled catalog cannot present a high score anyway.
_SCORE_CAPS = {
    "CAT-IDENTITY-001": (69, "Duplicate product identifiers make rows ambiguous."),
    "CAT-VARIANT-004": (79, "Variant groups mix more than one brand."),
}


def _score_catalog(
    passed_checks: int,
    total_checks: int,
    findings: list[Finding],
) -> tuple[int, dict[str, Any]]:
    base = percent(passed_checks, total_checks)
    deductions = sum(
        _SEVERITY_DEDUCTIONS.get(item["severity"], 2) for item in findings
    )
    cap = 100
    cap_reasons: list[str] = []
    for item in findings:
        capped = _SCORE_CAPS.get(item["rule_id"])
        if capped and capped[0] < cap:
            cap = capped[0]
        if capped:
            cap_reasons.append(capped[1])
    score = max(1, min(base - deductions, cap))
    return score, {
        "base_completeness": base,
        "severity_deductions": deductions,
        "cap": cap,
        "cap_reasons": sorted(set(cap_reasons)),
    }
