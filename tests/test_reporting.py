from __future__ import annotations

import unittest

from catalogready.agent import run_product_agent_html
from catalogready.reporting import render_html_report, render_markdown_report


class ReportingTests(unittest.TestCase):
    def test_markdown_report_contains_scores_and_findings(self) -> None:
        report = render_markdown_report(
            {
                "operation": "audit_catalog",
                "scores": {"catalog_readiness": {"score": 80, "status": "measured"}},
                "findings": [
                    {
                        "rule_id": "CAT-001",
                        "severity": "medium",
                        "title": "Missing value",
                        "evidence": "One row is empty.",
                        "recommendation": "Populate verified data.",
                    }
                ],
            }
        )
        self.assertIn("Catalog Readiness: 80/100", report)
        self.assertIn("[MEDIUM] Missing value", report)

    def test_html_report_is_self_contained(self) -> None:
        html = """
        <html><head><title>Desk Lamp</title><script type="application/ld+json">
        {"@type":"Product","name":"Desk Lamp","sku":"LAMP-1",
        "offers":{"price":"49","priceCurrency":"AUD","availability":"InStock"}}
        </script></head><body>Compact desk lamp.</body></html>
        """
        result = run_product_agent_html("https://example.com/lamp", html)
        report = render_html_report(result)
        self.assertIn("<!doctype html>", report)
        self.assertIn("Desk Lamp", report)
        self.assertIn("Claim grounding", report)
        self.assertIn("Recommended Product JSON-LD", report)
        # Self-contained: no external resources.
        self.assertNotIn("http-equiv=\"refresh\"", report)
        self.assertNotIn("src=\"http", report)
        self.assertNotIn("href=\"http", report)

    def test_html_report_renders_generic_audit_results(self) -> None:
        report = render_html_report(
            {
                "operation": "audit_catalog",
                "scores": {"catalog_readiness": {"score": 51, "status": "measured"}},
                "findings": [
                    {
                        "rule_id": "CAT-IDENTITY-001",
                        "severity": "high",
                        "title": "Duplicate product identifiers",
                        "evidence": "Duplicate IDs: 1.",
                        "recommendation": "Assign unique IDs.",
                    }
                ],
            }
        )
        self.assertIn("51/100", report)
        self.assertIn("CAT-IDENTITY-001", report)

