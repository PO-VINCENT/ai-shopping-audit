"""MCP adapter used by Codex, Claude Code, Gemini CLI, and other clients."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .env import load_local_env
from .service import (
    audit_catalog,
    audit_discovery_bundle,
    audit_page_html,
    build_visibility_prompt_pack,
    describe_agent,
    optimize_product_csv,
    optimize_product_html,
    optimize_shopify_payload,
    provider_status,
    run_product_agent_html,
    score_visibility_snapshots,
)


mcp = FastMCP(
    "CatalogReady AI",
    instructions=(
        "Optimize retail product evidence and audit generated claims. Keep "
        "readiness separate from observed AI visibility, never invent product "
        "facts, and require merchant approval before publishing."
    ),
)


@mcp.tool()
def catalogready_describe() -> dict:
    """Describe CatalogReady capabilities, protocols, and limitations."""
    return describe_agent()


@mcp.tool()
def catalogready_audit_catalog(catalog_path: str) -> dict:
    """Audit a local CSV catalog and return structured evidence-backed findings."""
    return audit_catalog(catalog_path)


@mcp.tool()
def catalogready_audit_page_html(url: str, html: str) -> dict:
    """Audit supplied product-page HTML; the host remains responsible for fetching it."""
    return audit_page_html(url, html)


@mcp.tool()
def catalogready_audit_discovery_bundle(
    url: str,
    html: str,
    robots_txt: str = "",
    sitemap_xml: str = "",
) -> dict:
    """Audit page HTML together with optional robots.txt and sitemap evidence."""
    return audit_discovery_bundle(url, html, robots_txt, sitemap_xml)


@mcp.tool()
def catalogready_build_visibility_prompt_pack(
    domain: str,
    category: str,
    market: str = "en-AU",
) -> dict:
    """Build prompts for repeated, timestamped AI-visibility observations."""
    return build_visibility_prompt_pack(domain, category, market)


@mcp.tool()
def catalogready_score_visibility_snapshots(snapshot_path: str, target_domain: str) -> dict:
    """Score recorded citation observations without calling a live model provider."""
    return score_visibility_snapshots(snapshot_path, target_domain)


@mcp.tool()
def catalogready_model_providers() -> dict:
    """List BYO model providers and whether their server-side environment is configured."""
    return {"providers": provider_status()}


@mcp.tool()
def catalogready_run_product_agent(
    url: str,
    html: str,
    mode: str = "audit",
    provider: str = "deterministic",
    model: str = "",
    merchant_answers: dict | None = None,
    resumed_from: str = "",
) -> dict:
    """Inspect, plan, safely draft, and validate product-readiness changes."""
    return run_product_agent_html(
        url,
        html,
        mode=mode,
        provider_name=provider,
        model=model,
        merchant_answers=merchant_answers,
        resumed_from=resumed_from,
    )


@mcp.tool()
def catalogready_optimize_product_html(
    url: str,
    html: str,
    provider: str = "deterministic",
    model: str = "",
    market: str = "en-AU",
) -> dict:
    """Create an evidence-backed product listing, journey, claim audit, and readiness score."""
    return optimize_product_html(
        url,
        html,
        provider_name=provider,
        model=model,
        market=market,
    )


@mcp.tool()
def catalogready_optimize_product_csv(
    csv_text: str,
    row_index: int = 0,
    provider: str = "deterministic",
    model: str = "",
    market: str = "en-AU",
) -> dict:
    """Optimize one CSV product row without writing to a merchant system."""
    return optimize_product_csv(
        csv_text,
        row_index,
        provider_name=provider,
        model=model,
        market=market,
    )


@mcp.tool()
def catalogready_optimize_shopify_payload(
    product_data: dict,
    shop_domain: str = "",
    provider: str = "deterministic",
    model: str = "",
    market: str = "en-AU",
) -> dict:
    """Optimize an authorized Shopify GraphQL product object supplied by the host agent."""
    return optimize_shopify_payload(
        product_data,
        shop_domain,
        provider_name=provider,
        model=model,
        market=market,
    )


def main() -> None:
    load_local_env()
    mcp.run()


if __name__ == "__main__":
    main()
