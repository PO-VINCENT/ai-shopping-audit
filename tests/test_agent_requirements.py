from __future__ import annotations

import unittest

from catalogready.catalog.identifiers import is_valid_gtin
from catalogready.discovery.scoring import audit_page_html


def _page(jsonld: str, body: str = "<p>A fine product for daily use.</p>", html_attrs: str = ' lang="en"', head_extra: str = '<meta name="description" content="A product.">') -> str:
    return (
        f"<html{html_attrs}><head><title>Product</title>{head_extra}"
        f'<script type="application/ld+json">{jsonld}</script>'
        f"</head><body>{body}</body></html>"
    )


_BASE_OFFER = '"offers":{"price":"49","priceCurrency":"%s","availability":"%s"%s}'


def _product(currency: str = "AUD", availability: str = "https://schema.org/InStock", offer_extra: str = "", product_extra: str = "") -> str:
    offer = _BASE_OFFER % (currency, availability, offer_extra)
    return '{"@type":"Product","name":"Product","sku":"P1"%s,%s}' % (product_extra, offer)


def _rule_ids(html: str) -> set[str]:
    result = audit_page_html("https://example.com/p", html)
    return {item["rule_id"] for item in result["findings"]}


class GtinValidationTests(unittest.TestCase):
    def test_gs1_checksum(self) -> None:
        self.assertTrue(is_valid_gtin("4006381333931"))   # valid EAN-13
        self.assertTrue(is_valid_gtin("036000291452"))    # valid UPC-A
        self.assertFalse(is_valid_gtin("4006381333932"))  # bad check digit
        self.assertFalse(is_valid_gtin("12345"))          # bad length
        self.assertFalse(is_valid_gtin("abcdefghijklm"))  # not digits

    def test_invalid_gtin_is_flagged(self) -> None:
        html = _page(_product(product_extra=',"gtin13":"4006381333932"'))
        self.assertIn("GEO-GTIN-001", _rule_ids(html))
        html = _page(_product(product_extra=',"gtin13":"4006381333931"'))
        self.assertNotIn("GEO-GTIN-001", _rule_ids(html))


class VocabularyTests(unittest.TestCase):
    def test_unknown_currency_is_flagged(self) -> None:
        self.assertIn("GEO-CURRENCY-001", _rule_ids(_page(_product(currency="DOLLARS"))))
        self.assertNotIn("GEO-CURRENCY-001", _rule_ids(_page(_product(currency="usd"))))

    def test_free_text_availability_is_flagged(self) -> None:
        self.assertIn("GEO-AVAILABILITY-002", _rule_ids(_page(_product(availability="ships in 2 weeks"))))
        self.assertNotIn("GEO-AVAILABILITY-002", _rule_ids(_page(_product(availability="InStock"))))

    def test_expired_price_valid_until(self) -> None:
        self.assertIn("GEO-OFFER-004", _rule_ids(_page(_product(offer_extra=',"priceValidUntil":"2020-01-01"'))))
        self.assertNotIn("GEO-OFFER-004", _rule_ids(_page(_product(offer_extra=',"priceValidUntil":"2099-01-01"'))))


class PageAmbiguityTests(unittest.TestCase):
    def test_multiple_ungrouped_offers_are_flagged(self) -> None:
        two = "[" + _product() + "," + _product().replace('"P1"', '"P2"') + "]"
        self.assertIn("GEO-PRODUCT-004", _rule_ids(_page(two)))
        grouped = two.replace('"sku":"P2"', '"sku":"P2","isVariantOf":{"@id":"#group"}')
        self.assertNotIn("GEO-PRODUCT-004", _rule_ids(_page(grouped)))


class PageHygieneTests(unittest.TestCase):
    def test_refurbished_without_item_condition(self) -> None:
        html = _page(_product(), body="<p>This refurbished unit works like new.</p>")
        self.assertIn("GEO-CONDITION-001", _rule_ids(html))
        declared = _page(
            _product(offer_extra=',"itemCondition":"https://schema.org/RefurbishedCondition"'),
            body="<p>This refurbished unit works like new.</p>",
        )
        self.assertNotIn("GEO-CONDITION-001", _rule_ids(declared))

    def test_missing_description_and_lang(self) -> None:
        html = _page(_product(), html_attrs="", head_extra="")
        rule_ids = _rule_ids(html)
        self.assertIn("SEO-DESC-001", rule_ids)
        self.assertIn("SEO-LANG-001", rule_ids)

    def test_insecure_image_urls_are_flagged(self) -> None:
        html = _page(_product(product_extra=',"image":["http://example.com/p.jpg"]'))
        self.assertIn("SEO-HTTPS-001", _rule_ids(html))
        html = _page(_product(product_extra=',"image":["https://example.com/p.jpg"]'))
        self.assertNotIn("SEO-HTTPS-001", _rule_ids(html))


if __name__ == "__main__":
    unittest.main()
