# CatalogReady

**Can AI shopping agents actually read your product page?**

CatalogReady is the open-source Lighthouse for AI shopping. Point it at a
product page and get a transparent 0–100 readiness score, the exact product
data machines can and cannot read, unsupported marketing claims, and
paste-ready fixes.

**Offline · deterministic rules · no API key · never writes to your store.**

```bash
uvx --from catalogready-ai catalogready https://your-store.com/products/example
```

```text
  Waterproof Commuter Shoe – Blue

  CatalogReady Score: 82/100 (ready)

  Product identity      16/20
  Offer completeness    20/20
  Structured data       20/20
  Decision evidence     14/15
  Media & variants       2/15
  Claim grounding       10/10

  0 critical · 2 recommended · 0 minor findings
  Full report: catalogready-report.html
```

The HTML report is a single self-contained file: score dial, per-pillar
breakdown, every finding with a stable rule ID, the questions only the
merchant can answer, a recommended Product JSON-LD block built strictly
from evidence found on the page, and a downloadable PNG score card.

## Why this exists

ChatGPT shopping, Google AI results, and Perplexity buy-flows read product
pages with machines, not eyes. A page can look perfect to humans while
being invisible or untrustworthy to an AI shopping agent: missing stable
IDs, incomplete offers, absent Product JSON-LD, and marketing claims with
no supporting evidence.

CatalogReady checks what the machines check — deterministically, locally,
and with a score that survives scrutiny:

- **Only your page earns points.** Nothing CatalogReady generates
  contributes to the score.
- **Blocking defects cap the score.** Duplicate IDs, incomplete offers,
  missing structured data, or an unsupported high-risk claim hard-cap the
  number, no matter how complete everything else is.
- **Every finding cites evidence** and carries a rule ID you can grep for.
  [docs/RULES.md](docs/RULES.md) documents every rule with its source —
  Google's merchant-listing requirements, OpenAI's Agentic Commerce feed
  spec, Bing's Copilot grounding guidelines, and the published crawler
  documentation of OpenAI, Perplexity, and Anthropic.

See [docs/scoring-methodology.md](docs/scoring-methodology.md) for the full
rubric and caps.

## Install and run

```bash
# one-off (recommended for a first try)
uvx --from catalogready-ai catalogready https://your-store.com/products/example

# or as a checkout
uv sync
uv run catalogready audit https://your-store.com/products/example

# fully offline: audit a saved page instead of fetching it
uv run catalogready audit https://your-store.com/products/example saved-page.html

# machine-readable output
uv run catalogready audit <url> [saved.html] --json
```

Fetching is exactly one HTTP GET for the page you name. The audit engine
itself makes no network calls — the test suite runs with networking
disabled.

Try it on the bundled examples without touching the network:

```bash
uv run catalogready audit https://example.com/products/cr-001 examples/demo-store/index.html
uv run catalogready catalog examples/messy-apparel.csv   # scores 51/100, and shows exactly why
```

## What gets checked

| Pillar | Examples of rules |
|---|---|
| Product identity | stable ID (SKU/GTIN/MPN), brand, category, canonical URL |
| Offer completeness | price + currency + availability, complete Offer markup |
| Structured data | Product JSON-LD present, valid, consistent with the visible page |
| Decision evidence | description, specifications, shipping/returns/care/limitations on the page |
| Media & variants | primary image, image count, variant attributes and identity |
| Claim grounding | superlatives, “clinically proven”, warranty and performance claims checked against page evidence |

When facts are missing, CatalogReady asks instead of inventing: the report
lists the questions only the merchant can answer, and
`--answers merchant-answers.json` resumes the audit with verified values.

## Interactive agent session

`catalogready chat` opens a Claude Code-style terminal session over the
bounded agent — audit, ask, answer, fix:

```text
catalogready> /audit https://your-store.com/products/example
● inspect_product_page — Extracted 3 evidence items ...
● audit_product — Measured readiness at 16/100 and produced 13 findings.

  CatalogReady Score: 16/100 (needs_work)
  ...
  [blocking] price: What is the current verified product price?

catalogready> why is offer completeness low?
Offer completeness: 0/20
  ✗ price
  ✗ currency
  ...

catalogready> /answers sku=CR-100 price=49.00 currency=AUD availability=in_stock
catalogready> /draft
Isolated preview validation: 16 → 60 (+44), status validated.

catalogready> /report
```

The agent pauses for facts it cannot verify instead of inventing them;
`/answers` resumes it. Free-text questions are answered deterministically
from the audit result; set `/provider openai` (or `gemini`, `claude`,
`deepseek` — keys via server environment variables only) for open-ended,
model-answered questions grounded strictly in the audit JSON.

## Interactive dashboard

One command serves the web UI and the local API on the same port and opens
your browser:

```bash
uv run catalogready dashboard
```

Enter a product URL and press Audit — the local server fetches the page
for you (one request). Or paste the HTML / load the built-in good/bad demos
to stay fully offline.
Every audit produces a plain-language summary conclusion, auto-drafted fix
suggestions with an isolated preview validation, expandable per-pillar score
explanations, inline merchant questions, a paste-ready JSON-LD patch, an
"Ask the agent" chat window, and a downloadable HTML report. The UI follows
your browser language (English / 中文, switchable in the header). Everything
runs locally; the page never asks for API keys.

## Use it with ChatGPT, Claude, Gemini, Copilot, or DeepSeek

CatalogReady ships an MCP server, so the AI assistant you already use can
audit pages as a tool:

```bash
claude mcp add catalogready -- uv run catalogready-mcp
```

**[docs/QUICKSTART-AI-ASSISTANTS.md](docs/QUICKSTART-AI-ASSISTANTS.md)**
has copy-paste setups for **ChatGPT/Codex**, **Claude** (Code + Desktop),
**Gemini** (CLI + Enterprise A2A), **Copilot** (VS Code agent mode), and
**DeepSeek** — covering both directions: the assistant calling
CatalogReady as a tool, and each vendor as the optional BYO model inside
CatalogReady. Protocol details: [docs/INTEROPERABILITY.md](docs/INTEROPERABILITY.md).

## How it compares

| | CatalogReady | Google Rich Results Test | Generic SEO crawlers | AI copy generators |
|---|---|---|---|---|
| Validates Product schema syntax | ✓ | ✓ | partial | ✗ |
| Scores completeness for AI shopping agents | ✓ | ✗ | ✗ | ✗ |
| Checks marketing claims against evidence | ✓ | ✗ | ✗ | ✗ |
| Runs offline, no account, no API key | ✓ | ✗ | ✗ | ✗ |
| Hands you a paste-ready JSON-LD fix | ✓ | ✗ | ✗ | generated, ungrounded |

## Bring your own model key (optional)

Everything above runs with **no key**. To enable model-assisted planning,
chat answers, and listing drafts, put a provider key in the server's
`.env` — see [docs/BYO-KEYS.md](docs/BYO-KEYS.md). Keys never enter the
dashboard, the extension, or tool arguments.

## Also in the box

The audit engine is a vendor-neutral service with several thin surfaces.
These are secondary to the page audit and documented in
[docs/ROADMAP.md](docs/ROADMAP.md):

- `catalogready catalog feed.csv` — CSV catalog audit with the same
  deduction-and-cap scoring.
- `catalogready-api` — HTTP server with OpenAPI docs and an A2A agent card.
- A Chromium extension (`browser-extension/`) — one click on any product
  page captures the rendered HTML and shows the score, findings, merchant
  questions, auto-drafted fixes, and the ask-the-agent box. Works on
  bot-protected storefronts because it reads what your browser rendered.
- Optional model-assisted listing drafts (OpenAI, Gemini, Claude, DeepSeek)
  with bring-your-own keys via server environment variables — never in tool
  arguments or browser storage — and deterministic claim evaluation with
  publishing safety caps.

## Guarantees

- The deterministic core requires no API key and makes no network calls.
- CatalogReady never writes to a storefront, feed, or merchant system.
- It never invents product attributes, citations, or rankings.
- A readiness score is not a promise of ranking or citation by any AI
  system — and any tool that promises that is guessing.

## Contributing

Rule proposals are the most valuable contribution — see
[CONTRIBUTING.md](CONTRIBUTING.md) and the issue templates. Run the suite
with `python -m unittest discover -s tests -v`; it must pass offline.

Architecture and module design: [docs/repository-design.md](docs/repository-design.md) ·
Rules with sources: [docs/RULES.md](docs/RULES.md) ·
Scoring: [docs/scoring-methodology.md](docs/scoring-methodology.md) ·
Interoperability: [docs/INTEROPERABILITY.md](docs/INTEROPERABILITY.md) ·
Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

## Contact

Built by **Vincent Po Li**. Questions, fix help, partnership, or feedback:

- Issues / discussions: [github.com/PO-VINCENT/ai-shopping-audit](https://github.com/PO-VINCENT/ai-shopping-audit/issues)
- Email: [vincentli802@hotmail.com](mailto:vincentli802@hotmail.com)
- LinkedIn: [vincent-po-li](https://www.linkedin.com/in/vincent-po-li-324291122/)
- X: [@Vincent_Po_Li](https://x.com/Vincent_Po_Li)
- 小红书 (Xiaohongshu): `vincent726217`

Licensed under [Apache-2.0](LICENSE).
