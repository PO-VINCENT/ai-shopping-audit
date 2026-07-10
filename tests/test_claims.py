from __future__ import annotations

import unittest

from catalogready.agent import run_product_agent_html
from catalogready.optimization.claims import audit_listing_claims
from catalogready.optimization.evidence import evidence_from_html, page_topic_evidence


def _record(title: str, description: str, evidence: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "source": {"kind": "url_html", "uri": "https://example.com/p"},
        "product": {
            "title": title,
            "description": description,
            "review_summary": {},
            "price": {},
        },
        "evidence": evidence or [],
    }


class ListingClaimTests(unittest.TestCase):
    def test_superlative_claims_are_flagged(self) -> None:
        findings, summary = audit_listing_claims(
            _record("The best commuter shoe, #1 worldwide", "A shoe.")
        )
        rule_ids = {item["rule_id"] for item in findings}
        self.assertIn("CLAIM-SUPERLATIVE-001", rule_ids)
        self.assertGreaterEqual(summary["risky_claims"], 2)

    def test_grounded_performance_claim_is_not_flagged(self) -> None:
        findings, _ = audit_listing_claims(
            _record(
                "Waterproof commuter shoe",
                "A waterproof shoe.",
                evidence=[
                    {
                        "id": "spec.1",
                        "field": "specification.material",
                        "value": "Verified waterproof membrane",
                        "source": "https://example.com/p",
                    }
                ],
            )
        )
        self.assertEqual(findings, [])

    def test_ungrounded_warranty_claim_is_high_risk(self) -> None:
        findings, _ = audit_listing_claims(
            _record("Desk lamp", "Comes with a lifetime warranty.")
        )
        matched = [item for item in findings if item["rule_id"] == "CLAIM-WARRANTY-001"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["severity"], "high")

    def test_page_warranty_evidence_grounds_the_claim(self) -> None:
        findings, _ = audit_listing_claims(
            _record(
                "Desk lamp",
                "Comes with a lifetime warranty.",
                evidence=[
                    {
                        "id": "page.warranty",
                        "field": "page_evidence.warranty",
                        "value": "Every lamp includes a registered lifetime warranty.",
                        "source": "https://example.com/p",
                    }
                ],
            )
        )
        self.assertEqual(findings, [])


class PageEvidenceTests(unittest.TestCase):
    def test_body_text_becomes_topic_evidence(self) -> None:
        html = (
            "<html><head><title>Shoe</title></head><body>"
            "<p>Free shipping on orders over $50. Dispatch within two days.</p>"
            "<p>Unworn items may be returned within 30 days for a refund.</p>"
            "<p>Machine wash cold and air dry.</p>"
            "</body></html>"
        )
        record = evidence_from_html("https://example.com/shoe", html)
        evidence_ids = {item["id"] for item in record["evidence"]}
        self.assertIn("page.shipping", evidence_ids)
        self.assertIn("page.returns", evidence_ids)
        self.assertIn("page.care", evidence_ids)

    def test_script_and_style_text_is_ignored(self) -> None:
        topics = page_topic_evidence("")
        self.assertEqual(topics, {})
        html = (
            "<html><body><script>var shipping = 'free shipping hack';</script>"
            "<style>.returns { color: red; }</style><p>A plain product.</p></body></html>"
        )
        record = evidence_from_html("https://example.com/p", html)
        evidence_ids = {item["id"] for item in record["evidence"]}
        self.assertNotIn("page.shipping", evidence_ids)
        self.assertNotIn("page.returns", evidence_ids)


class ReadinessCapTests(unittest.TestCase):
    def test_high_risk_claim_caps_the_agent_score(self) -> None:
        html = """
        <html><head><title>Miracle Lamp</title><script type="application/ld+json">
        {"@type":"Product","name":"Miracle Lamp","sku":"LAMP-9",
        "description":"Clinically proven to improve focus.",
        "offers":{"price":"49","priceCurrency":"AUD","availability":"InStock"}}
        </script></head><body>Compact desk lamp with no supporting studies.</body></html>
        """
        result = run_product_agent_html("https://example.com/lamp", html)
        readiness = result["readiness"]["before"]
        self.assertLessEqual(readiness["score"], 49)
        self.assertEqual(readiness["safety_cap"], 49)
        rule_ids = {item["rule_id"] for item in result["findings"]}
        self.assertIn("CLAIM-PROOF-001", rule_ids)


if __name__ == "__main__":
    unittest.main()
