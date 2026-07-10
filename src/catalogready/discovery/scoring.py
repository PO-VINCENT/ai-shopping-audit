"""Compose page, robots, sitemap, canonical, and structured-data checks."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from catalogready.catalog.schemas import Finding, finding, percent, result, scores

from .canonical import audit_canonical
from .content_evidence import evidence_coverage, extract_page_signals
from .quality import audit_page_quality
from .robots import audit_robots
from .sitemap import audit_sitemap
from .structured_data import audit_product_structured_data


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute HTTP or HTTPS URL")


def audit_page_html(url: str, html: str) -> dict[str, Any]:
    _validate_url(url)
    signals = extract_page_signals(html)
    findings: list[Finding] = []

    title_ok = bool(signals.title)
    if not title_ok:
        findings.append(finding("SEO-TITLE-001", "high", "Page title is missing", "No non-empty title element was found.", "Add a concise title that accurately identifies the product."))

    canonical_ok, canonical_findings = audit_canonical(url, signals.canonical)
    findings.extend(canonical_findings)

    indexable = "noindex" not in signals.robots
    if not indexable:
        findings.append(finding("SEO-ROBOTS-001", "high", "Page requests noindex", f"robots content is `{signals.robots}`.", "Remove noindex only if public discovery is intended."))

    structured_checks, structured_findings, structured_summary, products, offers = (
        audit_product_structured_data(signals.json_ld_blocks)
    )
    findings.extend(structured_findings)

    evidence = evidence_coverage(signals)
    substantive = signals.visible_words >= 120
    if not substantive:
        findings.append(finding("GEO-EVIDENCE-001", "medium", "Product evidence is thin", f"Only {signals.visible_words} visible words were detected.", "Add verified specifications, use cases, limitations, shipping, and return information."))
    missing_evidence = [name for name, present in evidence.items() if not present]
    if missing_evidence:
        findings.append(finding("GEO-EVIDENCE-002", "low", "Product evidence coverage is incomplete", f"Missing evidence areas: {', '.join(missing_evidence)}.", "Add concise shopper-facing facts only where the merchant can support them."))

    findings.extend(audit_page_quality(signals, products, offers, evidence))

    checks = [
        title_ok,
        canonical_ok,
        indexable,
        structured_checks["product"],
        structured_checks["product_identity"],
        structured_checks["offer_complete"],
        substantive,
    ]
    return result(
        "audit_page_html",
        {"url": url},
        scores(discovery=percent(sum(checks), len(checks))),
        {
            "title": signals.title or None,
            "description": signals.description or None,
            "canonical": signals.canonical,
            "visible_words": signals.visible_words,
            "evidence_coverage": evidence,
            **structured_summary,
            "findings": len(findings),
        },
        findings,
    )


def audit_discovery_bundle(
    url: str,
    html: str,
    robots_txt: str = "",
    sitemap_xml: str = "",
) -> dict[str, Any]:
    page_result = audit_page_html(url, html)
    robots_access, robots_findings = audit_robots(robots_txt, url)
    sitemap_included, sitemap_findings, sitemap_url_count = audit_sitemap(sitemap_xml, url)
    bundle_findings = [*page_result["findings"], *robots_findings, *sitemap_findings]

    page_score = page_result["scores"]["discovery_readiness"]["score"] or 0
    transport_checks = [*robots_access.values(), sitemap_included]
    transport_score = percent(sum(transport_checks), len(transport_checks))
    combined_score = round(page_score * 0.75 + transport_score * 0.25)
    page_result["operation"] = "audit_discovery_bundle"
    page_result["scores"] = scores(discovery=combined_score)
    page_result["summary"].update(
        {
            "robots_access": robots_access,
            "sitemap_included": sitemap_included,
            "sitemap_url_count": sitemap_url_count,
            "findings": len(bundle_findings),
        }
    )
    page_result["findings"] = bundle_findings
    return page_result
