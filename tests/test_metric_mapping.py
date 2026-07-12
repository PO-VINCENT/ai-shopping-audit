from __future__ import annotations

import unittest

from catalogready.catalog.metrics import METRICS, metric_for
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
