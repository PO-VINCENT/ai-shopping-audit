"""Sitemap inclusion checks using the Python standard library."""

from __future__ import annotations

from xml.etree import ElementTree

from catalogready.catalog.schemas import Finding, finding


def sitemap_urls(sitemap_xml: str) -> list[str]:
    if not sitemap_xml.strip():
        return []
    try:
        root = ElementTree.fromstring(sitemap_xml)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid sitemap XML: {exc}") from exc
    urls: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "loc" and element.text:
            urls.append(element.text.strip())
    return urls


def audit_sitemap(sitemap_xml: str, page_url: str) -> tuple[bool, list[Finding], int]:
    if not sitemap_xml.strip():
        return False, [
            finding(
                "SEO-SITEMAP-001",
                "low",
                "Sitemap was not supplied",
                "The discovery bundle contains no sitemap XML.",
                "Provide the sitemap when validating indexable product coverage.",
            )
        ], 0
    urls = sitemap_urls(sitemap_xml)
    included = page_url in urls
    if included:
        return True, [], len(urls)
    return False, [
        finding(
            "SEO-SITEMAP-002",
            "medium",
            "Product URL is absent from the sitemap",
            f"The audited URL was not found among {len(urls)} sitemap URLs.",
            "Add the canonical indexable product URL to the appropriate sitemap.",
        )
    ], len(urls)

