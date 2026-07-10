from __future__ import annotations

import unittest

from catalogready.optimization.evaluation import evaluate_claims
from catalogready.optimization.evidence import (
    evidence_from_csv,
    evidence_from_html,
    evidence_from_shopify,
)
from catalogready.optimization.pipeline import optimize_product_html


PRODUCT_HTML = """
<!doctype html>
<html>
<head>
  <title>Commuter Shell</title>
  <link rel="canonical" href="https://example.com/products/shell">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "productID": "CR-100",
    "name": "Commuter Shell",
    "description": "A navy commuter jacket with taped seams.",
    "category": "Apparel & Accessories > Clothing > Outerwear",
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
</head>
<body><h1>Commuter Shell</h1></body>
</html>
"""


class ProductEvidenceTests(unittest.TestCase):
    def test_extracts_product_jsonld_as_evidence(self) -> None:
        record = evidence_from_html("https://example.com/products/shell", PRODUCT_HTML)
        self.assertEqual(record["product"]["title"], "Commuter Shell")
        self.assertEqual(record["product"]["price"], {"amount": "149.00", "currency": "AUD"})
        self.assertEqual(record["product"]["availability"], "in_stock")
        evidence_ids = {item["id"] for item in record["evidence"]}
        self.assertIn("offer.price", evidence_ids)
        self.assertIn("spec.1", evidence_ids)

    def test_extracts_csv_and_shopify_payloads(self) -> None:
        csv_record = evidence_from_csv(
            "id,title,description,link,image_link,price,availability,brand,product_type,color\n"
            "1,City Shoe,Mesh commuter shoe,https://e/1,https://e/1.jpg,120 AUD,in_stock,Example,Shoes,Blue\n"
        )
        self.assertEqual(csv_record["product"]["price"]["currency"], "AUD")
        self.assertEqual(csv_record["product"]["specifications"][0]["name"], "color")

        shopify_record = evidence_from_shopify(
            {
                "id": "gid://shopify/Product/1",
                "handle": "city-shoe",
                "title": "City Shoe",
                "description": "Mesh commuter shoe",
                "productType": "Shoes",
                "vendor": "Example",
                "_shopCurrency": "AUD",
                "variants": {
                    "nodes": [
                        {
                            "id": "gid://shopify/ProductVariant/2",
                            "sku": "CITY-BLUE",
                            "price": "120.00",
                            "availableForSale": True,
                            "selectedOptions": [{"name": "Color", "value": "Blue"}],
                        }
                    ]
                },
            },
            "example.myshopify.com",
        )
        self.assertEqual(shopify_record["product"]["sku"], "CITY-BLUE")
        self.assertEqual(shopify_record["product"]["availability"], "in_stock")
        self.assertEqual(shopify_record["product"]["price"]["currency"], "AUD")


class ProductOptimizationTests(unittest.TestCase):
    def test_offline_pipeline_builds_journey_evaluation_and_score(self) -> None:
        result = optimize_product_html(
            "https://example.com/products/shell",
            PRODUCT_HTML,
        )
        self.assertEqual(result["operation"], "optimize_product_visibility")
        self.assertEqual(len(result["journey"]["stages"]), 6)
        self.assertGreaterEqual(len(result["journey"]["queries"]), 15)
        self.assertEqual(result["provider"]["generator"], "deterministic")
        self.assertTrue(result["approval"]["required"])
        self.assertGreater(result["readiness"]["score"], 0)

    def test_unsupported_high_risk_claim_is_not_upgraded(self) -> None:
        record = evidence_from_html("https://example.com/products/shell", PRODUCT_HTML)
        evaluation = evaluate_claims(
            record,
            {
                "claims": [
                    {
                        "text": "The safest jacket is guaranteed for life.",
                        "evidence_ids": ["product.description"],
                        "risk": "high",
                    }
                ]
            },
        )
        self.assertEqual(evaluation["claims"][0]["status"], "requires_human_review")

    def test_unlisted_numeric_statement_is_caught(self) -> None:
        record = evidence_from_html("https://example.com/products/shell", PRODUCT_HTML)
        evaluation = evaluate_claims(
            record,
            {
                "listing": {
                    "description": "This product includes an unsupported 25 year warranty.",
                    "bullets": [],
                    "best_for": [],
                    "limitations": [],
                    "faq": [],
                },
                "claims": [],
            },
        )
        self.assertEqual(evaluation["claims"][0]["status"], "unsupported")
        self.assertEqual(evaluation["claims"][0]["evaluator"], "deterministic_claim_coverage")


if __name__ == "__main__":
    unittest.main()
