# Roadmap

CatalogReady v1 is one product: an offline product-page AI-readiness
checker. Everything below exists in the codebase or design docs but is
deliberately **not** part of the v1 story. It ships (or stays) as
experimental until the core audit has an established user base.

## In the box today, secondary

- **CSV catalog auditing** — `catalogready catalog feed.csv`.
- **MCP server** — `catalogready-mcp`; lets Claude Code, Codex, Cursor, and
  other MCP clients run audits as a tool.
- **HTTP/OpenAPI server** — `catalogready-api` with generated docs.
- **Local dashboard** — `catalogready dashboard` serves the packaged UI in
  `src/catalogready/dashboard/` and the JSON API on one port.
- **Browser extension** (`browser-extension/`) — demo surface over the same
  service.
- **Model-assisted listing drafts** — BYO-key OpenAI/Gemini/Claude/DeepSeek
  adapters behind one JSON contract; deterministic fallback by default.

## Experimental / deferred

- **A2A protocol surface** — kept for interoperability testing.
- **Visibility and citation tracking** — prompt packs and recorded-response
  scoring exist; continuous tracking is out of scope for v1.
- **Customer-journey and query-hypothesis generation** — informational
  output only; no longer contributes to any score.
- **Shopify Admin GraphQL read path** — works, but is not part of the
  launch story.
- **Image-generation briefs** — remain in the draft output.
- **Automatic publishing** — will not be built; CatalogReady never writes
  to a storefront.

## Wanted (contributions welcome)

- Chrome Web Store packaging for the extension.
- A hosted or WASM (Pyodide) paste-a-page demo running the deterministic
  core fully client-side.
- Store-wide crawling with explicit robots.txt respect and rate limits.
- Rule-documentation pages, one per rule ID, linkable from reports.
- A public benchmark of readiness scores across well-known storefronts.
