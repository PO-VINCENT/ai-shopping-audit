from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from catalogready.service import audit_catalog, audit_page_html, build_visibility_prompt_pack, dispatch


class CatalogReadyServiceTests(unittest.TestCase):
    def test_catalog_audit_reports_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.csv"
            path.write_text(
                "id,title,description,link,image_link,price,availability,brand\n"
                "1,Shoe,,https://example.com/1,,10 AUD,in_stock,Example\n",
                encoding="utf-8",
            )
            result = audit_catalog(str(path))
        self.assertEqual(result["operation"], "audit_catalog")
        breakdown = result["summary"]["score_breakdown"]
        self.assertEqual(breakdown["base_completeness"], 75)
        self.assertEqual(
            result["scores"]["catalog_readiness"]["score"],
            max(1, 75 - breakdown["severity_deductions"]),
        )
        self.assertLess(result["scores"]["catalog_readiness"]["score"], 75)
        self.assertGreaterEqual(result["summary"]["findings"], 2)

    def test_page_audit_keeps_scores_separate(self) -> None:
        html = "<html><head><title>Shoe</title></head><body>Short page</body></html>"
        result = audit_page_html("https://example.com/shoe", html)
        self.assertIsNone(result["scores"]["catalog_readiness"]["score"])
        self.assertEqual(result["scores"]["discovery_readiness"]["status"], "measured")
        self.assertIsNone(result["scores"]["observed_ai_visibility"]["score"])

    def test_prompt_pack_is_stable(self) -> None:
        result = build_visibility_prompt_pack("https://example.com", "commuter shoes")
        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(len(result["prompts"]), 10)
        self.assertEqual(result["prompts"][0]["id"], "VIS-001")
        self.assertEqual(result["prompts"][0]["intent"], "discovery")

    def test_dispatch_exposes_product_optimization(self) -> None:
        html = """
        <html><head><script type="application/ld+json">
        {"@type":"Product","name":"Desk Lamp","description":"A compact lamp.",
        "category":"Home > Lighting","offers":{"price":"49","priceCurrency":"AUD","availability":"InStock"}}
        </script></head></html>
        """
        result = dispatch(
            "optimize_product_html",
            {"url": "https://example.com/lamp", "html": html},
        )
        self.assertEqual(result["operation"], "optimize_product_visibility")
        self.assertEqual(result["provider"]["generator"], "deterministic")

    def test_dispatch_exposes_product_agent(self) -> None:
        html = """
        <html><head><title>Desk Lamp</title><script type="application/ld+json">
        {"@type":"Product","name":"Desk Lamp","sku":"LAMP-1",
        "offers":{"price":"49","priceCurrency":"AUD","availability":"InStock"}}
        </script></head><body>Compact desk lamp.</body></html>
        """
        result = dispatch(
            "run_product_agent_html",
            {
                "url": "https://example.com/lamp",
                "html": html,
                "mode": "audit",
            },
        )
        self.assertEqual(result["operation"], "run_product_readiness_agent")
        self.assertEqual(result["provider"]["planner"], "deterministic")


if __name__ == "__main__":
    unittest.main()
