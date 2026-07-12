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


if __name__ == "__main__":
    unittest.main()
