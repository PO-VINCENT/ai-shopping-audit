# CatalogReady AI repository design

## 1. Product definition

CatalogReady AI is a vendor-neutral product-readiness agent. Its bounded v0.4
workflow inspects supplied product HTML, plans evidence-backed remediations,
asks for missing merchant facts, and validates reversible changes in memory.
The wider reference core also evaluates three
different concerns without presenting them as one guaranteed ranking signal:

1. **Catalog readiness** — product-feed completeness, taxonomy and variants.
2. **Discovery readiness** — technical SEO, structured data and page evidence.
3. **Observed AI visibility** — measured citations and product mentions from
   recorded model responses.

The deterministic domain core does not crawl websites, call a model provider or
write to merchant systems. Codex, Claude Code, Gemini and third-party agents can
fetch authorized data and invoke the same core through MCP, A2A or HTTP.

The later roadmap includes a read-only Product Data Agent for
multi-source catalog extraction, product feedback, and location-level inventory.
Its connector contracts, schemas, safety boundaries, MVP and repository tree are
defined in [product-data-agent-design.md](product-data-agent-design.md).

## 2. Design principles

- Keep retail rules independent from model and protocol vendors.
- Separate readiness from observed visibility.
- Attach evidence and remediation to every finding.
- Never infer missing product facts without an explicit approval workflow.
- Make offline fixtures and tests work without API keys.
- Version public result contracts.
- Keep protocol adapters thin and replaceable.
- Default to read-only analysis.

## 3. Complete repository structure

```text
catalogready-ai/
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── .mcp.json
├── .gemini/
│   └── settings.json
├── .gitignore
├── pyproject.toml
├── Dockerfile
│
├── src/
│   └── catalogready/
│       ├── __init__.py
│       ├── service.py
│       ├── cli.py
│       ├── mcp_server.py
│       ├── api_server.py
│       ├── local_server.py
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   ├── policy.py
│       │   ├── prompts.py
│       │   └── tools.py
│       │
│       ├── catalog/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   ├── taxonomy.py
│       │   ├── variants.py
│       │   └── scoring.py
│       │
│       ├── discovery/
│       │   ├── __init__.py
│       │   ├── robots.py
│       │   ├── sitemap.py
│       │   ├── canonical.py
│       │   ├── structured_data.py
│       │   ├── content_evidence.py
│       │   └── scoring.py
│       │
│       ├── visibility/
│       │   ├── __init__.py
│       │   ├── prompt_packs.py
│       │   ├── providers.py
│       │   ├── citations.py
│       │   ├── competitors.py
│       │   ├── snapshots.py
│       │   └── metrics.py
│       │
│       ├── optimization/
│       │   ├── evidence.py
│       │   ├── evaluation.py
│       │   ├── journey.py
│       │   ├── pipeline.py
│       │   ├── prompts.py
│       │   ├── scoring.py
│       │   └── shopify.py
│       │
│       ├── model_providers/
│       │   ├── __init__.py
│       │   └── base.py
│       │
│       └── reporting/
│           ├── __init__.py
│           └── render.py
│
├── contracts/
│   ├── audit-result.schema.json
│   ├── product-agent-run.schema.json
│   ├── product-optimization-result.schema.json
│   └── agent-card.example.json
│
├── integrations/
│   └── codex/
│       └── config.toml.example
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── README.md
│
├── browser-extension/
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   ├── popup.css
│   └── README.md
│
├── examples/
│   ├── demo-apparel.csv
│   ├── messy-apparel.csv
│   ├── prompt-pack.yaml
│   ├── demo-store/
│   │   ├── index.html
│   │   ├── robots.txt
│   │   └── sitemap.xml
│   └── recorded-responses/
│       └── sample.json
│
├── docs/
│   ├── repository-design.md
│   ├── architecture.md
│   ├── scoring-methodology.md
│   ├── seo-methodology.md
│   ├── geo-methodology.md
│   ├── limitations.md
│   └── INTEROPERABILITY.md
│
└── tests/
    ├── test_agent.py
    ├── test_catalog.py
    ├── test_discovery.py
    ├── test_visibility.py
    ├── test_reporting.py
    └── test_service.py
```

## 4. Runtime architecture

```text
Codex ──────────────┐
Claude Code ────────┼── MCP tools ────────┐
Gemini CLI ─────────┘                      │
Gemini Enterprise ───── A2A message ──────┤
Third-party client ─ REST/OpenAPI request ─┤
Local developer ───────── CLI command ─────┘
                                           ↓
                                  service.dispatch()
                                           ↓
             ┌─────────────┬───────────────┼──────────────┐
             ↓             ↓               ↓              ↓
          catalog/     discovery/      visibility/     reporting/
             └─────────────┴───────────────┴──────────────┘
                                           ↓
                              audit-result.schema.json
```

`service.py` is the application facade. External adapters call it instead of
importing domain internals. This allows module organization to evolve without
breaking agent integrations.

## 5. Root configuration and guidance

### `README.md`

Public project introduction, installation commands, demo workflows and primary
entry points.

### `AGENTS.md`

Shared repository instructions for Codex and other agents that recognize the
AGENTS format. It defines architectural boundaries, verification commands and
data-handling constraints.

### `CLAUDE.md`

Claude Code project instructions. It imports `AGENTS.md` and adds Claude-specific
MCP and approval guidance.

### `GEMINI.md`

Gemini CLI project guidance. It points Gemini to the shared architecture and
the project MCP configuration.

### `.mcp.json`

Project-scoped Claude Code MCP configuration. It launches `catalogready-mcp`
through `uv` without embedding secrets.

### `.gemini/settings.json`

Gemini CLI MCP configuration. Tool trust remains disabled so sensitive calls
are not silently approved.

### `pyproject.toml`

Python packaging metadata, runtime dependencies and console scripts:

- `catalogready`
- `catalogready-mcp`
- `catalogready-api`

### `Dockerfile`

Production-shaped container entry point for the HTTP and A2A server. A real
deployment must add authentication, rate limiting, observability and tenant
isolation outside or around the container.

## 6. Application facade and adapters

### `service.py`

Public application operations:

| Operation | Input | Domain owner |
|---|---|---|
| `describe` | none | service facade |
| `audit_catalog` | CSV path | catalog |
| `audit_page_html` | URL and HTML | discovery |
| `audit_discovery_bundle` | URL, HTML, robots and sitemap | discovery |
| `build_visibility_prompt_pack` | domain, category and market | visibility |
| `score_visibility_snapshots` | snapshot path and target domain | visibility |
| `render_markdown_report` | audit-result object | reporting |

`dispatch()` maps protocol-neutral operation names to domain functions.

### `cli.py`

Commands:

- `catalog`
- `page`
- `discovery`
- `prompts`
- `visibility`
- `report`
- `describe`

The CLI handles paths and presentation only. It must not duplicate scoring
logic.

### `mcp_server.py`

Exposes read-only MCP tools for agent clients:

- `catalogready_describe`
- `catalogready_audit_catalog`
- `catalogready_audit_page_html`
- `catalogready_audit_discovery_bundle`
- `catalogready_build_visibility_prompt_pack`
- `catalogready_score_visibility_snapshots`

Tool results are structured dictionaries following the shared result contract.

### `api_server.py`

FastAPI application exposing:

- `GET /health`
- `GET /v1/capabilities`
- `POST /v1/execute`
- `GET /.well-known/agent-card.json`
- `POST /a2a`
- generated `/openapi.json` and `/docs`

The A2A endpoint currently supports synchronous JSON-RPC `message/send` and
advertises non-streaming A2A 0.3 compatibility.

## 7. Catalog package

### `catalog/schemas.py`

Defines the stable internal shapes used across domain modules:

- `Finding`
- `ScoreSection`
- `finding()`
- `percent()`
- `scores()`
- `result()`

Every finding carries rule ID, severity, title, evidence, recommendation and
source.

### `catalog/taxonomy.py`

Contains the deliberately limited apparel taxonomy profile. It:

- normalizes common category aliases;
- infers a category from explicit fields or product text;
- checks category-specific attribute coverage;
- reports uncategorized products without inventing a category value.

Future taxonomy adapters should implement a shared interface for Shopify,
Google Product Categories or merchant-owned taxonomies.

### `catalog/variants.py`

Checks product and variant identity:

- duplicate product IDs;
- grouped variants with ambiguous titles;
- inconsistent brands inside a variant group;
- variant group counts for reporting.

### `catalog/scoring.py`

Loads CSV input, calculates required-field completeness, runs taxonomy and
variant checks, and produces the catalog-readiness result.

Taxonomy and variant findings remain visible rather than being hidden inside an
arbitrary score penalty.

## 8. Discovery package

### `discovery/content_evidence.py`

Parses supplied HTML using the standard library. It extracts:

- title;
- description;
- canonical URL;
- robots meta directives;
- JSON-LD blocks;
- visible text and word count;
- evidence coverage for specifications, limitations, shipping and returns.

Script and style content are excluded from visible-text scoring.

### `discovery/canonical.py`

Validates whether the canonical exists, is absolute, and points to the current
page or an intentionally different preferred identity.

### `discovery/structured_data.py`

Parses JSON-LD and checks:

- valid JSON;
- Product nodes;
- product names;
- Offer price;
- price currency;
- availability.

It does not assume that structured data is truthful merely because it parses.

### `discovery/robots.py`

Evaluates supplied robots rules for:

- Googlebot;
- OAI-SearchBot;
- Bingbot.

The longest matching allow/disallow path wins. The module does not fetch
`robots.txt` itself.

### `discovery/sitemap.py`

Parses XML, extracts `loc` elements and checks whether the canonical product URL
is present.

### `discovery/scoring.py`

Composes page checks and the optional discovery bundle. Page evidence contributes
75% and crawler/sitemap evidence contributes 25% to the reference discovery
score.

## 9. Visibility package

### `visibility/prompt_packs.py`

Builds stable shopper-intent prompts covering discovery, comparison, value,
education, trust, limitations, use cases, evidence and transaction intent.

### `visibility/providers.py`

Defines the `VisibilityProvider` protocol and an offline
`RecordedResponseProvider`. Live OpenAI, Anthropic, Google or other integrations
must be added behind this boundary.

### `visibility/citations.py`

Extracts URLs, normalizes citation domains and matches subdomains against the
target merchant domain.

### `visibility/competitors.py`

Calculates domain citation share of voice and returns the most visible competitor
domains. It does not infer commercial performance from citation counts.

### `visibility/snapshots.py`

Loads JSON or JSONL observations and normalizes provider, timestamp, answer,
citations, product mention and answer-support labels.

### `visibility/metrics.py`

Calculates:

- target-domain citation rate;
- product mention rate;
- labeled answer support rate;
- target citation share of voice;
- top competitor domains;
- providers represented.

The observed visibility score is currently the target-domain citation rate.

## 10. Reporting package

### `reporting/render.py`

Converts the shared JSON result into a compact Markdown report. Future renderers
can add HTML, PDF or dashboard output without changing audit logic.

## 11. Contracts

### `audit-result.schema.json`

Versioned JSON Schema for audit results. The stable top-level fields are:

```json
{
  "schema_version": "1.0",
  "operation": "audit_catalog",
  "input": {},
  "scores": {
    "catalog_readiness": {"score": 0, "status": "measured"},
    "discovery_readiness": {"score": null, "status": "not_run"},
    "observed_ai_visibility": {"score": null, "status": "not_run"}
  },
  "summary": {},
  "findings": []
}
```

### `agent-card.example.json`

Reference A2A discovery card for deployment. The runtime server generates its
card using `CATALOGREADY_PUBLIC_URL`.

## 12. Examples

- `demo-apparel.csv`: simple backwards-compatible catalog fixture.
- `messy-apparel.csv`: intentionally broken catalog for demonstrations.
- `prompt-pack.yaml`: human-readable prompt-pack example.
- `demo-store/`: HTML, robots and sitemap discovery fixture.
- `recorded-responses/sample.json`: deterministic visibility observations.

Examples must use synthetic data and domains reserved for examples.

## 13. Tests

- `test_catalog.py`: identity and variant failures.
- `test_discovery.py`: complete demo page and robots precedence.
- `test_visibility.py`: citations and recorded visibility metrics.
- `test_reporting.py`: Markdown rendering.
- `test_service.py`: facade behavior and score separation.

The required offline verification command is:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 14. Security and privacy boundaries

- No credentials in repository configuration.
- No default write tools.
- No automatic crawling or WAF bypass.
- No merchant data persisted by the core.
- No provider response presented without provider and timestamp metadata.
- No model-generated product claim accepted as verified evidence.
- Production A2A and HTTP deployments require authentication and authorization.

## 15. Planned extension points

### Near term

- Shopify and Google Merchant taxonomy profiles.
- URL fetching behind explicit authorization and network policy.
- richer Product and Offer consistency checks.
- HTML report connected to the current frontend.
- provider adapters for recorded, manual and approved live observations.

### Later

- OAuth-protected Streamable HTTP MCP deployment.
- official A2A SDK server with streaming and task persistence.
- image-to-product consistency checks.
- multilingual prompt packs and evidence checks.
- Shopify, WooCommerce, Magento and PIM connectors.
- scheduled visibility snapshots and longitudinal volatility metrics.
- human approval queue for proposed catalog changes.

## 16. Definition of done for new modules

A new module is complete when it:

1. has one clearly documented responsibility;
2. does not duplicate a rule owned by another module;
3. returns structured evidence instead of only a boolean;
4. has an offline deterministic test;
5. is exposed through `service.dispatch()` when it is a public capability;
6. updates the result contract if its public shape changes;
7. documents limitations and security implications;
8. preserves separate catalog, discovery and visibility scores.
