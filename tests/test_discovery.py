from __future__ import annotations

import unittest
from pathlib import Path

from catalogready.discovery.robots import is_allowed
from catalogready.discovery.scoring import audit_discovery_bundle


class DiscoveryAuditTests(unittest.TestCase):
    def test_demo_store_has_strong_discovery_score(self) -> None:
        root = Path(__file__).resolve().parents[1] / "examples" / "demo-store"
        result = audit_discovery_bundle(
            "https://example.com/products/cr-001",
            (root / "index.html").read_text(encoding="utf-8"),
            (root / "robots.txt").read_text(encoding="utf-8"),
            (root / "sitemap.xml").read_text(encoding="utf-8"),
        )
        self.assertGreaterEqual(result["scores"]["discovery_readiness"]["score"], 90)
        self.assertTrue(result["summary"]["sitemap_included"])
        self.assertTrue(result["summary"]["robots_access"]["oai_searchbot"])

    def test_longest_robots_rule_wins(self) -> None:
        robots = "User-agent: *\nDisallow: /products\nAllow: /products/public\n"
        self.assertFalse(is_allowed(robots, "googlebot", "https://example.com/products/private"))
        self.assertTrue(is_allowed(robots, "googlebot", "https://example.com/products/public/1"))

