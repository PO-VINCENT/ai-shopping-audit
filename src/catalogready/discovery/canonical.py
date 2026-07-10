"""Canonical URL checks."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from catalogready.catalog.schemas import Finding, finding


def _normalize(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def audit_canonical(page_url: str, canonical_url: str | None) -> tuple[bool, list[Finding]]:
    if not canonical_url:
        return False, [
            finding(
                "SEO-CANONICAL-001",
                "medium",
                "Canonical URL is missing",
                "No canonical link was found in the supplied HTML.",
                "Declare the preferred indexable product URL.",
            )
        ]
    if not canonical_url.startswith(("http://", "https://")):
        return False, [
            finding(
                "SEO-CANONICAL-002",
                "medium",
                "Canonical URL is not absolute",
                f"The canonical value is `{canonical_url}`.",
                "Publish an absolute HTTP or HTTPS canonical URL.",
            )
        ]
    if _normalize(page_url) != _normalize(canonical_url):
        return True, [
            finding(
                "SEO-CANONICAL-003",
                "low",
                "Page canonicalizes to another URL",
                f"Page URL `{page_url}` points to `{canonical_url}`.",
                "Confirm the target intentionally represents the preferred product identity.",
            )
        ]
    return True, []

