"""Image dimension rules (GEO-IMAGE-002) — pure logic, no network.

Dimensions are read from image bytes supplied by the caller (the online
adapter fetches them; tests craft them). Header sniffing covers PNG,
GIF, JPEG, and WebP without any imaging dependency.
"""

from __future__ import annotations

from typing import Any

from catalogready.catalog.schemas import Finding, finding

GOOGLE_MIN_PX = 500     # GMC minimum (enforcement announced for Jan 2027)
MICROSOFT_MIN_PX = 220  # MMC minimum (250 for apparel)


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return (width, height) for PNG/GIF/JPEG/WebP bytes, else None."""

    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return (
            int.from_bytes(data[16:20], "big"),
            int.from_bytes(data[20:24], "big"),
        )
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        return (
            int.from_bytes(data[6:8], "little"),
            int.from_bytes(data[8:10], "little"),
        )
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return (
                int.from_bytes(data[24:27], "little") + 1,
                int.from_bytes(data[27:30], "little") + 1,
            )
        if chunk == b"VP8L" and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        if chunk == b"VP8 ":
            return (
                int.from_bytes(data[26:28], "little") & 0x3FFF,
                int.from_bytes(data[28:30], "little") & 0x3FFF,
            )
        return None
    if len(data) >= 4 and data[:2] == b"\xff\xd8":  # JPEG
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                return (
                    int.from_bytes(data[index + 7 : index + 9], "big"),
                    int.from_bytes(data[index + 5 : index + 7], "big"),
                )
            index += 2 + int.from_bytes(data[index + 2 : index + 4], "big")
        return None
    return None


def audit_image_dimensions(measured: list[dict[str, Any]]) -> list[Finding]:
    """Evaluate fetched product images.

    Each entry: {"url": str, "status": int, "width": int|None, "height": int|None}.
    """

    findings: list[Finding] = []
    unfetchable = [item for item in measured if item.get("status") != 200]
    small = [
        item
        for item in measured
        if item.get("status") == 200
        and item.get("width") is not None
        and (item["width"] < GOOGLE_MIN_PX or item["height"] < GOOGLE_MIN_PX)
    ]
    if not unfetchable and not small:
        return findings

    problems: list[str] = []
    problems.extend(
        f"{item['url']} → HTTP {item.get('status')}" for item in unfetchable[:3]
    )
    problems.extend(
        f"{item['url']} → {item['width']}×{item['height']}px" for item in small[:3]
    )
    severity = "medium"
    if unfetchable or any(
        item["width"] < MICROSOFT_MIN_PX or item["height"] < MICROSOFT_MIN_PX
        for item in small
    ):
        severity = "high"
    findings.append(
        finding(
            "GEO-IMAGE-002",
            severity,  # type: ignore[arg-type]
            "Product images are unfetchable or below marketplace minimums",
            "; ".join(problems),
            f"Serve crawlable product images of at least {GOOGLE_MIN_PX}×{GOOGLE_MIN_PX}px "
            f"(Google minimum from Jan 2027; Microsoft requires {MICROSOFT_MIN_PX}×{MICROSOFT_MIN_PX}).",
        )
    )
    return findings


__all__ = ["GOOGLE_MIN_PX", "MICROSOFT_MIN_PX", "audit_image_dimensions", "image_dimensions"]
