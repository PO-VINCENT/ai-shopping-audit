from __future__ import annotations

import unittest
from unittest.mock import patch

from catalogready.agent import run_product_agent_html


RICH_PRODUCT_HTML = """
<!doctype html>
<html><head>
  <title>Commuter Shell</title>
  <link rel="canonical" href="https://example.com/products/shell">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "productID": "CR-100",
    "name": "Commuter Shell",
    "description": "A navy commuter jacket with taped seams.",
    "category": "Apparel > Outerwear",
    "brand": {"@type": "Brand", "name": "CatalogReady"},
    "sku": "CR-100-NAVY",
    "image": ["https://example.com/shell.jpg"],
    "color": "Navy",
    "material": "Recycled nylon",
    "offers": {
      "@type": "Offer",
      "price": "149.00",
      "priceCurrency": "AUD",
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
</head><body>
  <h1>Commuter Shell</h1>
  <p>This commuter jacket uses recycled nylon and taped seams. Review the size
  guide before purchase. Delivery and dispatch estimates appear at checkout.
  Unworn items may be returned under the merchant return policy. Avoid prolonged
  immersion and follow the published care instructions. The jacket is intended
  for ordinary wet-weather commuting and is not described as safety equipment.</p>
</body></html>
"""


class ProductAgentTests(unittest.TestCase):
    def test_audit_mode_is_bounded_and_read_only(self) -> None:
        result = run_product_agent_html(
            "https://example.com/products/shell",
            RICH_PRODUCT_HTML,
        )
        self.assertEqual(result["operation"], "run_product_readiness_agent")
        self.assertEqual(result["mode"], "audit")
        self.assertEqual(result["proposed_changes"], [])
        self.assertLessEqual(result["limits"]["steps_used"], 8)
        self.assertFalse(result["limits"]["storefront_writes_allowed"])
        self.assertIsNone(
            result["readiness"]["before"]["observed_ai_visibility"]["score"]
        )

    def test_draft_mode_validates_reversible_changes(self) -> None:
        html = RICH_PRODUCT_HTML.replace(
            '<link rel="canonical" href="https://example.com/products/shell">',
            "",
        )
        result = run_product_agent_html(
            "https://example.com/products/shell",
            html,
            mode="draft",
        )
        self.assertTrue(result["proposed_changes"])
        self.assertTrue(all(item["reversible"] for item in result["proposed_changes"]))
        self.assertTrue(result["validation"]["accepted"])
        self.assertGreaterEqual(
            result["validation"]["after_score"],
            result["validation"]["before_score"],
        )
        self.assertTrue(result["approval"]["required"])

    def test_missing_facts_pause_for_merchant_input(self) -> None:
        html = "<html><head><title>Desk Lamp</title></head><body>Desk lamp</body></html>"
        result = run_product_agent_html(
            "https://example.com/lamp",
            html,
            mode="draft",
        )
        fields = {item["field"] for item in result["merchant_questions"]}
        self.assertEqual(result["status"], "needs_input")
        self.assertTrue({"sku", "price", "currency", "availability"}.issubset(fields))

    def test_verified_answers_resume_without_inventing_facts(self) -> None:
        html = "<html><head><title>Desk Lamp</title></head><body>Desk lamp</body></html>"
        answers = {
            "sku": "LAMP-001",
            "price": "49.00",
            "currency": "AUD",
            "availability": "in_stock",
            "brand": "Example",
            "category": "Home > Lighting",
            "description": "A compact merchant-approved desk lamp.",
            "image": "https://example.com/lamp.jpg",
        }
        result = run_product_agent_html(
            "https://example.com/lamp",
            html,
            mode="draft",
            merchant_answers=answers,
            resumed_from="prior-run",
        )
        self.assertEqual(result["resumed_from"], "prior-run")
        self.assertFalse(any(item["blocking"] for item in result["merchant_questions"]))
        self.assertEqual(result["status"], "ready_for_approval")
        merchant_evidence = [
            item for item in result["evidence_record"]["evidence"]
            if item["source"] == "merchant_answer"
        ]
        self.assertGreaterEqual(len(merchant_evidence), len(answers))

    def test_model_planner_cannot_add_findings(self) -> None:
        class FakePlanner:
            name = "fake-planner"
            model = "fake-model"

            def generate_json(self, system, user, schema=None):
                return {
                    "selected_rule_ids": ["INVENTED-RULE", "GEO-EVIDENCE-001"],
                    "summary": "Selected an allowed evidence finding.",
                }

        with patch(
            "catalogready.agent.orchestrator.create_provider",
            return_value=FakePlanner(),
        ):
            result = run_product_agent_html(
                "https://example.com/products/shell",
                RICH_PRODUCT_HTML,
                provider_name="openai",
            )
        selected = {item["finding_rule_id"] for item in result["plan"]}
        available = {item["rule_id"] for item in result["findings"]}
        self.assertEqual(selected, {"GEO-EVIDENCE-001"})
        self.assertTrue(selected.issubset(available))


if __name__ == "__main__":
    unittest.main()
