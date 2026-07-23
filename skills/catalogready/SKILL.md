---
name: catalogready
description: >
  Audit product pages, CSV catalogs, and storefronts for AI shopping
  readiness (GEO/AEO for commerce) and draft evidence-backed listing
  fixes. Use when the user asks to audit a product page or catalog for
  AI readiness, check whether a store is citable by AI assistants,
  score AI shopping visibility, or optimize product listings for
  agentic commerce. Works through the catalogready MCP tools when
  connected, or the catalogready CLI otherwise.
license: Apache-2.0
---

# CatalogReady — AI shopping readiness audit

CatalogReady scores how ready a product page or catalog is for AI
shopping assistants and drafts evidence-backed fixes. The core audit is
deterministic: no API key, no account, no network beyond fetching the
page you are asked to audit.

## Choose the entry point

1. **MCP connected** (tools named `catalogready_*` are available):
   prefer them. Call `catalogready_describe` once if you need the
   capability map.
2. **No MCP**: use the CLI via `uvx --from catalogready-ai
   catalogready …` (or `uv run catalogready …` inside this repo).

## Core workflows

### Audit a product page

The audit engine never fetches pages itself — you fetch, it scores.

1. Fetch the page HTML yourself (browser tool, `curl`, or an existing
   file). Note whether it is rendered DOM or raw static HTML; label
   which one you audited in your summary.
2. MCP: `catalogready_run_product_agent(url, html)` — inspects, plans,
   and validates in one call. For a plain score,
   `catalogready_audit_page_html(url, html)`.
   CLI: `catalogready agent <url> <html_file>` or
   `catalogready page <url> <html_file>`.
3. Report: overall score, per-pillar breakdown, and the top 3–5 fixes
   with their evidence. Every finding in the result carries evidence —
   quote it; never add product claims of your own.

### Audit a CSV catalog

MCP: `catalogready_audit_catalog(catalog_path)` (local path).
CLI: `catalogready catalog <path>`.

### Discovery bundle (robots/sitemap)

When the user cares about crawler access, also fetch `/robots.txt` and
the sitemap, then `catalogready_audit_discovery_bundle(url, html,
robots_txt, sitemap_xml)` (CLI: `catalogready discovery`).

### AI visibility (is the store actually cited?)

Readiness and observed visibility are separate numbers — never blend
them. `catalogready_build_visibility_prompt_pack(domain, category,
market)` builds timestamped observation prompts; after the user records
snapshots, `catalogready_score_visibility_snapshots(snapshot_path,
target_domain)` scores them without calling any model.

### Draft listing fixes

`catalogready_optimize_product_html(url, html)` returns a full listing
draft, journey, claim audit, and score. CSV row:
`catalogready_optimize_product_csv`. Shopify payload the host already
fetched with authorization: `catalogready_optimize_shopify_payload`.
Drafts are proposals — require merchant approval before anything is
published to a live system.

## Guardrails

- Never pass API keys, tokens, or merchant customer data in tool
  arguments; BYO model keys live in server-side environment variables
  only (see docs/BYO-KEYS.md).
- Default `provider` is `deterministic`; only switch to a live model
  provider if the user asks for model-drafted copy.
- Never invent product attributes, citations, or rankings — report only
  what the structured result returns.
- Respect the site being audited: fetch the target page once, do not
  crawl beyond what the user asked for.
