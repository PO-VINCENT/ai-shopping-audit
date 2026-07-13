from __future__ import annotations

import unittest

from catalogready.catalog.metrics import METRICS, metric_for
from catalogready.catalog.platforms import PLATFORMS
from catalogready.catalog.schemas import finding
from catalogready.service import dispatch


class MetricMappingTests(unittest.TestCase):
    def test_exact_prefix_and_fallback(self) -> None:
        self.assertEqual(metric_for("GEO-GTIN-001"), "validity")
        self.assertEqual(metric_for("CAT-VALUE-PRICE"), "completeness")
        self.assertEqual(metric_for("SEO-ROBOTS-PERPLEXITYBOT"), "accessibility")
        self.assertEqual(metric_for("AGENT-OFFER-PRICE"), "completeness")
        self.assertEqual(metric_for("CLAIM-FUTURE-999"), "trust")
        self.assertEqual(metric_for("GEO-FUTURE-999"), "machine_readability")

    def test_finding_is_stamped_with_a_valid_metric(self) -> None:
        item = finding("GEO-POLICY-001", "medium", "t", "e", "r")
        self.assertEqual(item["metric"], "transactability")
        self.assertEqual(item["platforms"], ["openai", "google", "microsoft"])

    def test_every_agent_finding_carries_a_metric(self) -> None:
        result = dispatch(
            "run_product_agent_html",
            {
                "url": "https://example.com/lamp",
                "html": "<html><head><title>Lamp</title></head><body>Lamp</body></html>",
            },
        )
        self.assertTrue(result["findings"])
        for item in result["findings"]:
            self.assertIn(item.get("metric"), METRICS, item["rule_id"])
            self.assertTrue(item.get("platforms"), item["rule_id"])

    def test_platform_scores_filter_findings_and_keep_comprehensive_view(self) -> None:
        from catalogready.optimization.readiness import score_page_readiness

        evidence = {
            "product": {
                "id": "P-1", "title": "Lamp", "brand": "Acme", "category": "Lighting",
                "url": "https://example.com/lamp", "description": "A lamp",
                "price": {"amount": "20", "currency": "AUD"},
                "availability": "in_stock", "images": ["https://example.com/lamp.jpg"],
            }
        }
        google_only = finding("SEO-ROBOTS-GOOGLEBOT", "high", "blocked", "e", "r")
        audit = {
            "summary": {"products": 1, "offers": 1, "canonical": "https://example.com/lamp", "visible_words": 120},
            "findings": [google_only],
        }
        readiness = score_page_readiness(evidence, audit)
        views = readiness["platform_scores"]
        self.assertEqual(tuple(views), ("comprehensive", *PLATFORMS))
        self.assertEqual(views["comprehensive"]["score"], readiness["score"])
        self.assertLess(views["google"]["score"], views["openai"]["score"])
        self.assertEqual(views["google"]["metrics"]["accessibility"]["findings"], 1)
        self.assertEqual(views["openai"]["metrics"]["accessibility"]["findings"], 0)
        self.assertEqual(
            sum(item["points"] for item in views["comprehensive"]["deduction_items"]),
            views["comprehensive"]["deductions"],
        )
        self.assertEqual(views["google"]["deduction_items"][0]["rule_id"], "SEO-ROBOTS-GOOGLEBOT")
        self.assertIn("ChatGPT shopping", views["openai"]["surfaces"])


class GeoWeightTests(unittest.TestCase):
    def test_geo_findings_deduct_more_than_base_families(self) -> None:
        from catalogready.catalog.schemas import finding
        from catalogready.optimization.readiness import _deduction

        geo = finding("GEO-RETURNS-001", "medium", "t", "e", "r")
        seo = finding("SEO-DESC-001", "low", "t", "e", "r")
        claim = finding("CLAIM-SUPERLATIVE-001", "medium", "t", "e", "r")
        self.assertEqual(_deduction(geo), 5)
        self.assertEqual(_deduction(seo), 1)
        self.assertEqual(_deduction(claim), 3)
        self.assertEqual(_deduction(finding("GEO-GTIN-001", "high", "t", "e", "r")), 9)


if __name__ == "__main__":
    unittest.main()
