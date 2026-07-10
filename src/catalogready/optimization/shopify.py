"""Read-only Shopify Admin GraphQL product fetch for the optimization agent."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SHOPIFY_PRODUCT_QUERY = """
query CatalogReadyProduct($query: String!) {
  shop { currencyCode }
  products(first: 1, query: $query) {
    nodes {
      id handle title description descriptionHtml productType vendor status tags onlineStoreUrl
      seo { title description }
      featuredMedia { preview { image { url altText width height } } }
      media(first: 20) { nodes { preview { image { url altText width height } } } }
      metafields(first: 50) { nodes { namespace key type value } }
      variants(first: 100) {
        nodes {
          id title sku barcode availableForSale price compareAtPrice inventoryQuantity
          selectedOptions { name value }
          image { url altText width height }
        }
      }
    }
  }
}
""".strip()


ShopifyTransport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated Shopify domain
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise ValueError(f"Shopify returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(f"Shopify request failed: {type(exc).__name__}") from exc


def fetch_shopify_product(
    shop_domain: str,
    product_query: str,
    *,
    token_env: str = "SHOPIFY_ADMIN_TOKEN",
    api_version: str | None = None,
    transport: ShopifyTransport = _transport,
) -> dict[str, Any]:
    domain = shop_domain.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", domain):
        raise ValueError("shop_domain must be the permanent *.myshopify.com domain")
    query = product_query.strip()
    if not query or len(query) > 300:
        raise ValueError("product_query must contain a Shopify product ID, handle, SKU, or title")
    token = os.environ.get(token_env, "")
    if not token:
        raise ValueError(f"Missing Shopify token in {token_env}")
    version = api_version or os.environ.get("SHOPIFY_API_VERSION", "2026-04")
    response = transport(
        f"https://{domain}/admin/api/{version}/graphql.json",
        {"X-Shopify-Access-Token": token},
        {"query": SHOPIFY_PRODUCT_QUERY, "variables": {"query": query}},
        60.0,
    )
    errors = response.get("errors") or []
    if errors:
        raise ValueError(f"Shopify GraphQL error: {errors[0].get('message', 'unknown error')}")
    data = response.get("data") or {}
    nodes = ((data.get("products") or {}).get("nodes") or [])
    if not nodes:
        raise ValueError("No Shopify product matched product_query")
    product = dict(nodes[0])
    product["_shopCurrency"] = str((data.get("shop") or {}).get("currencyCode", ""))
    return product


__all__ = ["SHOPIFY_PRODUCT_QUERY", "fetch_shopify_product"]
