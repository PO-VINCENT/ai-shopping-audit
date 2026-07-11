from __future__ import annotations

import unittest

from catalogready.discovery.scoring import audit_page_html
from catalogready.optimization.evidence import (
    evidence_from_html,
    specifications_from_text,
)

# Modeled on a real supermarket marketplace page: feed-artifact JSON-LD name,
# heavy unpunctuated navigation, and specifications published only as prose.
MARKETPLACE_HTML = """
<html><head>
  <title>Everfit Auto Incline Treadmill 52cm Belt Home Gym | Example</title>
  <script type="application/ld+json">
  {"@type":"Product","name":"Everfit 1EA","sku":"1115674397",
   "brand":{"@type":"Brand","name":"Everfit"},
   "image":["https://cdn.example.com/1115674397.jpg"],
   "offers":{"price":"595","priceCurrency":"AUD","availability":"InStock"}}
  </script>
</head><body>
  <nav><ul>
    <li><a href="/">Everyday &amp; Other Services</a></li>
    <li><a href="/market">Everyday Market delivery</a></li>
    <li><a href="/login">Log in</a></li>
  </ul></nav>
  <main>
    <h1>Everfit Auto Incline Treadmill</h1>
    <p>Price: AUD 595. A compact treadmill for home cardio with auto incline and
    a five-layer shock absorption system for knees and joints.</p>
    <p>Specifications: Product size: 150cm x 84cm x 130cm belt size: 120cm x 52cm
    Rated voltage: 240V Rated power: 5.0HP Speed: 1-20km/h Weight capacity: 160kg
    Colour: Black Assembly Required: Yes</p>
    <p>Orders dispatch within two business days and shipping estimates are shown
    at checkout for your address.</p>
    <p>Unworn products may be returned within 14 days under the returns policy.</p>
  </main>
</body></html>
"""


class RealPageExtractionTests(unittest.TestCase):
    def test_markup_name_mismatch_is_flagged(self) -> None:
        result = audit_page_html("https://example.com/p/1115674397", MARKETPLACE_HTML)
        rule_ids = {item["rule_id"] for item in result["findings"]}
        self.assertIn("GEO-PRODUCT-003", rule_ids)

    def test_matching_name_is_not_flagged(self) -> None:
        html = MARKETPLACE_HTML.replace('"name":"Everfit 1EA"', '"name":"Everfit Auto Incline Treadmill"')
        result = audit_page_html("https://example.com/p/1115674397", html)
        rule_ids = {item["rule_id"] for item in result["findings"]}
        self.assertNotIn("GEO-PRODUCT-003", rule_ids)

    def test_topic_evidence_skips_navigation_junk(self) -> None:
        record = evidence_from_html("https://example.com/p/1115674397", MARKETPLACE_HTML)
        shipping = next(
            item for item in record["evidence"] if item["id"] == "page.shipping"
        )
        self.assertIn("dispatch", shipping["value"].lower())
        self.assertNotIn("Everyday Market", shipping["value"])
        self.assertNotIn("Log in", shipping["value"])

    def test_prose_specifications_become_evidence(self) -> None:
        record = evidence_from_html("https://example.com/p/1115674397", MARKETPLACE_HTML)
        specs = {item["name"].lower(): item["value"] for item in record["product"]["specifications"]}
        self.assertIn("rated voltage", specs)
        self.assertEqual(specs["rated voltage"], "240V")
        self.assertIn("weight capacity", specs)
        self.assertEqual(specs["weight capacity"], "160kg")
        evidence_ids = {item["id"] for item in record["evidence"]}
        self.assertIn("spec.1", evidence_ids)

    def test_jsonld_specs_still_win_over_prose(self) -> None:
        html = MARKETPLACE_HTML.replace(
            '"sku":"1115674397",',
            '"sku":"1115674397","additionalProperty":[{"name":"Motor","value":"5HP"}],',
        )
        record = evidence_from_html("https://example.com/p/1115674397", html)
        names = [item["name"] for item in record["product"]["specifications"]]
        self.assertEqual(names, ["Motor"])

    def test_spec_parser_requires_a_specifications_heading(self) -> None:
        self.assertEqual(
            specifications_from_text("Contact us Note: something Phone: 123"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
