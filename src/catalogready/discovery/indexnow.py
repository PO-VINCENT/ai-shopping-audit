"""IndexNow key verification (SEO-INDEXNOW-001) — pure logic, no network.

IndexNow key files are named by the key itself (https://host/{key}.txt),
so a site's participation is NOT externally discoverable — the merchant
must supply their key. The online adapter fetches the key file; this
module evaluates the response.
"""

from __future__ import annotations

import re

from catalogready.catalog.schemas import Finding, finding

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,128}$")


def audit_indexnow(host: str, key: str, status: int | None, body: str) -> list[Finding]:
    key = key.strip()
    if not _KEY_PATTERN.match(key):
        return [
            finding(
                "SEO-INDEXNOW-001",
                "low",
                "IndexNow key has an invalid format",
                f"The supplied key does not match the protocol format (8–128 chars of a-z, A-Z, 0-9, dashes).",
                "Generate a valid IndexNow key and host it at https://{host}/{key}.txt.",
            )
        ]
    location = f"https://{host}/{key}.txt"
    if status != 200:
        return [
            finding(
                "SEO-INDEXNOW-001",
                "low",
                "IndexNow key file is not reachable",
                f"{location} returned HTTP {status}.",
                "Host the key file at the site root so price/stock changes can be pushed to search engines instantly.",
            )
        ]
    if body.strip() != key:
        return [
            finding(
                "SEO-INDEXNOW-001",
                "low",
                "IndexNow key file content does not match the key",
                f"{location} exists but its content differs from the key.",
                "The key file must contain exactly the key string.",
            )
        ]
    return []


__all__ = ["audit_indexnow"]
