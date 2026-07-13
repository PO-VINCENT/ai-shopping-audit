"""Opt-in online checks (--online): the only multi-request network code.

Adapter layer, like fetch.py — the service and rule core stay offline.
Fetches at most three product images (bounded reads) and, when the
merchant supplies their IndexNow key, the key file. Rule evaluation
lives in discovery/images.py and discovery/indexnow.py.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from .discovery.images import audit_image_dimensions, image_dimensions
from .discovery.indexnow import audit_indexnow

_IMAGE_READ_LIMIT = 512 * 1024
_MAX_IMAGES = 3
_USER_AGENT = "CatalogReady/0.7 online checks (bounded, user-initiated)"


def _get(url: str, limit: int) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read(limit)
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b""


def run_online_checks(
    page_url: str,
    image_urls: list[str],
    indexnow_key: str | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    measured = []
    for url in [u for u in image_urls if u.startswith(("http://", "https://"))][:_MAX_IMAGES]:
        status, data = _get(url, _IMAGE_READ_LIMIT)
        size = image_dimensions(data) if status == 200 else None
        measured.append(
            {
                "url": url,
                "status": status,
                "width": size[0] if size else None,
                "height": size[1] if size else None,
            }
        )
    # Images whose format we could not sniff are skipped, not penalized.
    findings.extend(
        audit_image_dimensions(
            [m for m in measured if m["status"] != 200 or m["width"] is not None]
        )
    )

    if indexnow_key:
        host = urlparse(page_url).hostname or ""
        status, body = _get(f"https://{host}/{indexnow_key.strip()}.txt", 4096)
        findings.extend(
            audit_indexnow(host, indexnow_key, status, body.decode("utf-8", "replace"))
        )

    return findings


__all__ = ["run_online_checks"]
