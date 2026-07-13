"""Single-page fetch helper for interactive adapters.

This is the only network read in the CLI and chat adapters. The service
layer and the deterministic core never import this module.
"""

from __future__ import annotations

import urllib.request

FETCH_LIMIT_BYTES = 2_000_000
_USER_AGENT = "CatalogReady/0.7 product-page audit (single request)"


def fetch_page(url: str, timeout: int = 20) -> str:
    """Fetch exactly one product page named by the user."""

    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(FETCH_LIMIT_BYTES).decode(charset, errors="replace")


__all__ = ["FETCH_LIMIT_BYTES", "fetch_page"]
