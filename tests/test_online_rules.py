from __future__ import annotations

import struct
import unittest

from catalogready.discovery.images import audit_image_dimensions, image_dimensions
from catalogready.discovery.indexnow import audit_indexnow


def png_bytes(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def gif_bytes(width: int, height: int) -> bytes:
    return b"GIF89a" + struct.pack("<HH", width, height)


def jpeg_bytes(width: int, height: int) -> bytes:
    # SOI + APP0 (minimal) + SOF0 with dimensions
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof0 = b"\xff\xc0" + struct.pack(">H", 11) + b"\x08" + struct.pack(">HH", height, width) + b"\x01\x00"
    return b"\xff\xd8" + app0 + sof0


def webp_vp8x_bytes(width: int, height: int) -> bytes:
    dims = (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"VP8X" + b"\x0a\x00\x00\x00" + b"\x00\x00\x00\x00" + dims


class ImageSniffTests(unittest.TestCase):
    def test_dimensions_for_all_formats(self) -> None:
        self.assertEqual(image_dimensions(png_bytes(800, 600)), (800, 600))
        self.assertEqual(image_dimensions(gif_bytes(120, 90)), (120, 90))
        self.assertEqual(image_dimensions(jpeg_bytes(1024, 768)), (1024, 768))
        self.assertEqual(image_dimensions(webp_vp8x_bytes(640, 480)), (640, 480))
        self.assertIsNone(image_dimensions(b"not an image at all"))


class ImageRuleTests(unittest.TestCase):
    def test_large_images_pass(self) -> None:
        measured = [{"url": "https://e/a.png", "status": 200, "width": 800, "height": 800}]
        self.assertEqual(audit_image_dimensions(measured), [])

    def test_small_image_is_medium(self) -> None:
        measured = [{"url": "https://e/a.png", "status": 200, "width": 400, "height": 400}]
        findings = audit_image_dimensions(measured)
        self.assertEqual(findings[0]["rule_id"], "GEO-IMAGE-002")
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertIn("400×400px", findings[0]["evidence"])

    def test_tiny_or_unfetchable_is_high(self) -> None:
        tiny = [{"url": "https://e/a.png", "status": 200, "width": 100, "height": 100}]
        self.assertEqual(audit_image_dimensions(tiny)[0]["severity"], "high")
        broken = [{"url": "https://e/a.png", "status": 404, "width": None, "height": None}]
        findings = audit_image_dimensions(broken)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertIn("HTTP 404", findings[0]["evidence"])


class IndexNowTests(unittest.TestCase):
    def test_hosted_key_passes(self) -> None:
        self.assertEqual(audit_indexnow("example.com", "a1b2c3d4e5", 200, "a1b2c3d4e5\n"), [])

    def test_missing_key_file(self) -> None:
        findings = audit_indexnow("example.com", "a1b2c3d4e5", 404, "")
        self.assertEqual(findings[0]["rule_id"], "SEO-INDEXNOW-001")
        self.assertIn("HTTP 404", findings[0]["evidence"])

    def test_content_mismatch_and_bad_format(self) -> None:
        self.assertIn(
            "does not match",
            audit_indexnow("example.com", "a1b2c3d4e5", 200, "other-key")[0]["title"],
        )
        self.assertIn(
            "invalid format",
            audit_indexnow("example.com", "short", 200, "short")[0]["title"],
        )


if __name__ == "__main__":
    unittest.main()
