"""Normalize URL HTML, CSV rows, and Shopify product objects into evidence."""

from __future__ import annotations

import csv
import html as html_module
import io
import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("name") or value.get("value") or value.get("url") or ""
    if isinstance(value, list):
        value = ", ".join(_clean(item) for item in value if _clean(item))
    text = html_module.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _first(*values: Any) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def _availability(value: Any) -> str:
    text = _clean(value).lower().rsplit("/", 1)[-1]
    aliases = {
        "instock": "in_stock",
        "in stock": "in_stock",
        "in_stock": "in_stock",
        "outofstock": "out_of_stock",
        "out of stock": "out_of_stock",
        "out_of_stock": "out_of_stock",
        "preorder": "preorder",
        "pre_order": "preorder",
        "backorder": "backorder",
        "back_order": "backorder",
    }
    return aliases.get(text, text)


def _price(value: Any, currency: Any = "") -> dict[str, str]:
    text = _clean(value)
    amount_match = re.search(r"-?\d+(?:[.,]\d+)?", text)
    amount = amount_match.group(0).replace(",", ".") if amount_match else ""
    resolved_currency = _clean(currency).upper()
    if not resolved_currency:
        currency_match = re.search(r"\b[A-Z]{3}\b", text.upper())
        if currency_match:
            resolved_currency = currency_match.group(0)
    return {"amount": amount, "currency": resolved_currency}


class _ProductHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._in_jsonld = False
        self._ignored_depth = 0
        self._script_parts: list[str] = []
        self.jsonld: list[Any] = []
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._script_parts = []
        elif tag.lower() in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        elif tag.lower() == "meta":
            key = values.get("property") or values.get("name") or values.get("itemprop")
            if key and values.get("content"):
                self.meta[key.lower()] = values["content"]
        elif tag.lower() == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href", "")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script" and self._in_jsonld:
            self._in_jsonld = False
            raw = "".join(self._script_parts).strip()
            if raw:
                try:
                    self.jsonld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        elif tag.lower() in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_jsonld:
            self._script_parts.append(data)
            return
        if self._ignored_depth:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._text_parts.append(cleaned)

    @property
    def visible_text(self) -> str:
        return " ".join(self._text_parts)


_PAGE_TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("shipping", ("shipping", "delivery", "dispatch", "ships ")),
    ("returns", ("return", "refund", "exchange")),
    ("warranty", ("warranty", "guarantee")),
    ("care", ("care instructions", "machine wash", "hand wash", "wipe clean", "do not bleach")),
    ("materials", ("material", "made from", "made of", "recycled", "fabric")),
    ("limitations", ("not suitable", "not intended", "avoid", "warning", "limitation")),
)


def page_topic_evidence(visible_text: str) -> dict[str, str]:
    """Extract the first supporting sentence per shopper-facing topic."""

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", visible_text)
        if sentence.strip()
    ]
    topics: dict[str, str] = {}
    for topic, keywords in _PAGE_TOPICS:
        for sentence in sentences:
            lowered = sentence.lower()
            if any(keyword in lowered for keyword in keywords):
                topics[topic] = sentence[:240]
                break
    return topics


def _walk_jsonld(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_walk_jsonld(item))
    elif isinstance(value, dict):
        found.append(value)
        if "@graph" in value:
            found.extend(_walk_jsonld(value["@graph"]))
    return found


def _product_jsonld(parser: _ProductHTMLParser) -> dict[str, Any]:
    for block in parser.jsonld:
        for node in _walk_jsonld(block):
            types = node.get("@type") or []
            if isinstance(types, str):
                types = [types]
            if any(str(item).lower() == "product" for item in types):
                return node
    return {}


def _offer(product: dict[str, Any]) -> dict[str, Any]:
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    return offers if isinstance(offers, dict) else {}


def _images(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        url = _clean(item)
        if url and url not in result:
            result.append(url)
    return result


def _specifications(product: dict[str, Any]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    properties = product.get("additionalProperty") or []
    if isinstance(properties, dict):
        properties = [properties]
    for item in properties:
        if not isinstance(item, dict):
            continue
        name = _first(item.get("name"), item.get("propertyID"))
        value = _first(item.get("value"), item.get("valueReference"))
        if name and value:
            specs.append({"name": name, "value": value})
    for field in ("color", "material", "size", "pattern", "weight"):
        value = _clean(product.get(field))
        if value and not any(spec["name"].lower() == field for spec in specs):
            specs.append({"name": field, "value": value})
    return specs


def _evidence_record(source: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []

    def add(evidence_id: str, field: str, value: Any) -> None:
        cleaned = _clean(value)
        if cleaned:
            evidence.append(
                {
                    "id": evidence_id,
                    "field": field,
                    "value": cleaned,
                    "source": source.get("uri") or source.get("kind"),
                }
            )

    for field in ("id", "title", "description", "category", "brand", "sku", "gtin", "mpn", "url"):
        add(f"product.{field}", field, product.get(field))
    price = product.get("price") or {}
    add("offer.price", "price", price.get("amount"))
    add("offer.currency", "currency", price.get("currency"))
    add("offer.availability", "availability", product.get("availability"))
    for index, image in enumerate(product.get("images") or [], 1):
        add(f"image.{index}", "image", image)
    for index, spec in enumerate(product.get("specifications") or [], 1):
        add(f"spec.{index}", f"specification.{spec.get('name', '')}", spec.get("value"))
    review = product.get("review_summary") or {}
    add("review.rating", "aggregate_rating", review.get("rating"))
    add("review.count", "review_count", review.get("count"))
    return {
        "schema_version": "1.0",
        "source": source,
        "product": product,
        "evidence": evidence,
    }


def evidence_from_html(url: str, html: str) -> dict[str, Any]:
    if not url.strip():
        raise ValueError("url is required")
    if not html.strip():
        raise ValueError("html is required")
    parser = _ProductHTMLParser()
    parser.feed(html)
    node = _product_jsonld(parser)
    offer = _offer(node)
    brand = node.get("brand") or {}
    aggregate = node.get("aggregateRating") or {}
    product = {
        "id": _first(node.get("productID"), node.get("sku"), parser.meta.get("product:retailer_item_id")),
        "title": _first(node.get("name"), parser.meta.get("og:title"), parser.title),
        "description": _first(node.get("description"), parser.meta.get("og:description"), parser.meta.get("description")),
        "category": _first(node.get("category"), parser.meta.get("product:category")),
        "brand": _first(brand, node.get("manufacturer")),
        "sku": _clean(node.get("sku")),
        "gtin": _first(node.get("gtin"), node.get("gtin13"), node.get("gtin12"), node.get("gtin14")),
        "mpn": _clean(node.get("mpn")),
        "url": _first(node.get("url"), parser.canonical, parser.meta.get("og:url"), url),
        "images": _images(node.get("image") or parser.meta.get("og:image")),
        "price": _price(
            offer.get("price") or offer.get("lowPrice") or parser.meta.get("product:price:amount"),
            offer.get("priceCurrency") or parser.meta.get("product:price:currency"),
        ),
        "availability": _availability(offer.get("availability") or parser.meta.get("product:availability")),
        "specifications": _specifications(node),
        "review_summary": {
            "rating": _clean(aggregate.get("ratingValue")),
            "count": _first(aggregate.get("reviewCount"), aggregate.get("ratingCount")),
        },
    }
    record = _evidence_record(
        {"kind": "url_html", "uri": url, "observed_at": _now()},
        product,
    )
    for topic, sentence in page_topic_evidence(parser.visible_text).items():
        record["evidence"].append(
            {
                "id": f"page.{topic}",
                "field": f"page_evidence.{topic}",
                "value": sentence,
                "source": url,
            }
        )
    return record


_CSV_CORE = {
    "id",
    "title",
    "name",
    "description",
    "link",
    "url",
    "image_link",
    "image",
    "price",
    "currency",
    "availability",
    "brand",
    "product_type",
    "category",
    "sku",
    "gtin",
    "mpn",
}


def evidence_from_csv(csv_text: str, row_index: int = 0) -> dict[str, Any]:
    if row_index < 0:
        raise ValueError("row_index must be non-negative")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        raise ValueError("CSV must contain a header and at least one product row")
    if row_index >= len(rows):
        raise ValueError(f"row_index {row_index} is outside the {len(rows)} CSV rows")
    row = {str(key).strip().lower(): value for key, value in rows[row_index].items()}
    specs = [
        {"name": key, "value": _clean(value)}
        for key, value in row.items()
        if key not in _CSV_CORE and _clean(value)
    ]
    link = _first(row.get("link"), row.get("url"))
    product = {
        "id": _clean(row.get("id")),
        "title": _first(row.get("title"), row.get("name")),
        "description": _clean(row.get("description")),
        "category": _first(row.get("product_type"), row.get("category")),
        "brand": _clean(row.get("brand")),
        "sku": _clean(row.get("sku")),
        "gtin": _clean(row.get("gtin")),
        "mpn": _clean(row.get("mpn")),
        "url": link,
        "images": _images(row.get("image_link") or row.get("image")),
        "price": _price(row.get("price"), row.get("currency")),
        "availability": _availability(row.get("availability")),
        "specifications": specs,
        "review_summary": {},
    }
    return _evidence_record(
        {
            "kind": "csv",
            "uri": f"csv:row:{row_index}",
            "observed_at": _now(),
            "rows": len(rows),
        },
        product,
    )


def _nodes(connection: Any) -> list[dict[str, Any]]:
    if not isinstance(connection, dict):
        return []
    if isinstance(connection.get("nodes"), list):
        return [node for node in connection["nodes"] if isinstance(node, dict)]
    return [
        edge["node"]
        for edge in connection.get("edges") or []
        if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
    ]


def evidence_from_shopify(product_data: dict[str, Any], shop_domain: str = "") -> dict[str, Any]:
    if not isinstance(product_data, dict) or not product_data:
        raise ValueError("Shopify product data is required")
    variants = _nodes(product_data.get("variants"))
    variant = variants[0] if variants else {}
    metafields = _nodes(product_data.get("metafields"))
    specs = [
        {
            "name": f"{item.get('namespace', 'custom')}.{item.get('key', '')}".strip("."),
            "value": _clean(item.get("value")),
        }
        for item in metafields
        if item.get("key") and _clean(item.get("value"))
    ]
    for option in variant.get("selectedOptions") or []:
        if isinstance(option, dict) and option.get("name") and _clean(option.get("value")):
            specs.append({"name": str(option["name"]), "value": _clean(option["value"])})
    images: list[str] = []
    featured = product_data.get("featuredMedia") or {}
    featured_image = (featured.get("preview") or {}).get("image") or featured.get("image") or {}
    if isinstance(featured_image, dict) and featured_image.get("url"):
        images.append(str(featured_image["url"]))
    for node in _nodes(product_data.get("media")) + _nodes(product_data.get("images")):
        image = (node.get("preview") or {}).get("image") or node.get("image") or node
        if isinstance(image, dict) and image.get("url") and image["url"] not in images:
            images.append(str(image["url"]))
    online_url = _clean(product_data.get("onlineStoreUrl"))
    if not online_url and shop_domain and product_data.get("handle"):
        online_url = f"https://{shop_domain}/products/{product_data['handle']}"
    product = {
        "id": _clean(product_data.get("id")),
        "title": _clean(product_data.get("title")),
        "description": _first(product_data.get("description"), product_data.get("descriptionHtml")),
        "category": _first(product_data.get("productType"), (product_data.get("category") or {}).get("name")),
        "brand": _clean(product_data.get("vendor")),
        "sku": _clean(variant.get("sku")),
        "gtin": _clean(variant.get("barcode")),
        "mpn": "",
        "url": online_url,
        "images": images,
        "price": _price(
            variant.get("price"),
            variant.get("currencyCode") or product_data.get("_shopCurrency"),
        ),
        "availability": "in_stock" if variant.get("availableForSale") else "out_of_stock",
        "specifications": specs,
        "review_summary": {},
        "variants": variants,
    }
    uri = f"shopify://{shop_domain or 'store'}/{product.get('id') or product_data.get('handle', '')}"
    return _evidence_record(
        {"kind": "shopify", "uri": uri, "observed_at": _now()},
        product,
    )


def domain_from_url(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


__all__ = [
    "domain_from_url",
    "evidence_from_csv",
    "evidence_from_html",
    "evidence_from_shopify",
    "page_topic_evidence",
]
