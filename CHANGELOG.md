# Changelog

## 0.7.0 — 2026-07-12

### Added

- Extension (v0.6.5): the crawler comparison is now a **view-mode
  switcher** directly under the score — "Rendered · N | Crawler · M"
  tabs swap the entire popup (dial, pillars, summary, findings) between
  the two views, with the JavaScript-dependence gap explained in one
  line. The crawler audit runs lazily on first switch and is cached per
  page; bot-walled fetches disable the mode with an explanation.
- Extension (v0.6.3): **Compare crawler view** — audits the same URL's
  static HTML via the local server and diffs it against the rendered
  page: both scores side by side, the JavaScript-dependence gap, and the
  rules that fail only in each view. Detects bot-protection responses
  ("crawlers may be blocked entirely"). Localized EN/中文.
- The audited HTML source is now labeled in both UIs: the dashboard
  marks fetched-vs-supplied HTML and the extension marks the rendered
  page, with a note that the score gap between the two views measures
  JavaScript dependence (rendered-only content is invisible to
  non-rendering AI crawlers). Localized EN/中文.

### Changed

- **GEO rules weigh more in the final score.** Findings from the GEO-*
  family (machine-readable product data) deduct at −9/−5/−2 for
  high/medium/low versus −6/−3/−1 for other families; the live
  Woolworths reference drops further to 69 "needs_work" (raw 87 − 18).
- **Score recalibration: findings now deduct.** Real-world pages were
  scoring 85–95 "ready" because ~30 newer rules produced findings that
  cost nothing. Every page/claim finding now deducts by severity
  (high −6, medium −3, low −1) on top of the presence checks, before the
  caps; `raw_score` and `deductions` are reported for transparency and
  shown in the CLI card, dashboard/popup summaries, and HTML report.
  GEO-PRODUCT-003 (markup name does not match the page) is now high
  severity — the markup name is the agent's matching key. Reference
  points: the live Woolworths page drops 87 "ready" → 76 "needs_work";
  the bad demo drops 16 → 0; clean pages (good demo 97) are unaffected.

### Added

- `docs/METRICS.md`: the rules categorized into eight measurement
  metrics (machine readability, validity, completeness, consistency,
  trust & claim integrity, agent accessibility, transactability,
  freshness) plus a landscape comparison against Lighthouse, Core Web
  Vitals, security graders, SEO health scores, GMC/GS1/PIM data-quality
  systems, and GEO/AEO visibility tools.
- The extension (v0.6.1) and dashboard run the bounded image-size check
  automatically after every audit via the new `/v1/online-checks` route
  (adapter-level, max 3 fetches by the local server). Findings are
  appended as informational; the deterministic score never changes.
- `catalogready audit --online`: the two network-dependent rules, opt-in
  and adapter-layer only. GEO-IMAGE-002 fetches up to three product
  images (bounded reads, stdlib header sniffing for PNG/GIF/JPEG/WebP)
  and flags files below Google's 500×500 minimum (high when below
  Microsoft's 220×220 floor or unfetchable). SEO-INDEXNOW-001 verifies
  the merchant's IndexNow key file with `--indexnow-key` (keys are named
  by the key itself, so participation is not externally discoverable).
  Rule logic is pure and offline-tested; online findings are
  informational and never change the deterministic score. Every candidate
  rule from the platform research is now implemented.
- Round three: the agentic-checkout trust layer, researched against the
  UCP spec (ucp.dev, Google/Shopify-led), OpenAI's ACP checkout schema,
  and Microsoft's MMC UCP-readiness docs. Four new page rules:
  GEO-POLICY-001 (privacy-policy and terms links — required for ACP
  checkout eligibility and MMC store approval), GEO-RETURNS-002
  (hasMerchantReturnPolicy must be complete: applicableCountry +
  returnPolicyCategory or merchantReturnLink), GEO-SHIPPING-002
  (shippingDetails must carry shippingRate/shippingDestination/
  deliveryTime), and GEO-SELLER-001 (machine-readable seller identity).
  The page parser now extracts links; docs/RULES.md gains an
  "agentic checkout layer" section covering UCP, ACP checkout, and the
  verified absence of product-data requirements in AP2. The good demo
  fixture gains footer policy links.
- Nine more agent-requirement rules, all offline and deterministic:
  GEO-GTIN-001 (GS1 length + check-digit validation; an incorrect GTIN is
  a documented disapproval cause), GEO-CURRENCY-001 (ISO 4217),
  GEO-AVAILABILITY-002 (schema.org ItemAvailability vocabulary, no free
  text), GEO-OFFER-004 (expired priceValidUntil), GEO-PRODUCT-004
  (multiple ungrouped Product offers on one page), GEO-CONDITION-001
  (refurbished/pre-owned pages must declare itemCondition), SEO-DESC-001
  (meta description), SEO-LANG-001 (html lang), and SEO-HTTPS-001
  (canonical/image URLs must be HTTPS). Documented with sources in
  docs/RULES.md; demo fixture scores unchanged.

## 0.6.0 — 2026-07-11

### Added

- `docs/QUICKSTART-AI-ASSISTANTS.md`: copy-paste setups for ChatGPT/Codex,
  Claude (Code + Desktop), Gemini (CLI + Enterprise A2A), Copilot (VS Code
  agent mode), and DeepSeek — both as MCP clients calling CatalogReady and
  as BYO models inside it. Linked from the README.
- Launch tooling: a tag-triggered release workflow (PyPI Trusted
  Publishing + extension zip artifact), extension icons (16/32/48/128),
  `scripts/package-extension.sh`, `scripts/benchmark.py` (audits a URL
  list into a Markdown benchmark table), `docs/BYO-KEYS.md`, and
  `docs/LAUNCH.md` — the full launch runbook with pre-written listing and
  announcement copy.
- Selecting a model provider without a configured key now shows a
  localized hint (add the key to the server's `.env` and restart) in both
  the dashboard and the extension, instead of a raw provider error.
- The dashboard footer shows the server version and start time, refreshed
  every 30 seconds. The `/health` route now reports `version`,
  `started_at`, and `stale` — the server compares its own source mtimes
  against its start time, so running old code after a `git pull` shows a
  red "restart" warning (localized) instead of silently serving outdated
  audit results.
- The browser-extension popup is multilingual like the dashboard: default
  follows the browser language (English / 简体中文), a header selector
  overrides and persists it, and switching re-renders the current result.
  Static-key coverage is test-enforced.
- GEO-PRODUCT-003: the JSON-LD product name must appear in the visible
  page title or text. Catches feed-artifact markup names (e.g. a real
  marketplace page whose markup names a treadmill "Everfit 1EA") that AI
  agents would read as the product name; also fails the structured-data
  identity check.
- Specifications published only as prose ("Specifications: Rated voltage:
  240V ...") are now parsed deterministically into structured spec
  evidence when the markup has none, feeding the decision-evidence pillar,
  claim grounding, and the recommended JSON-LD's additionalProperty block.

### Fixed

- Page-topic evidence (shipping/returns/warranty/care) no longer captures
  navigation junk: visible text is segmented at block-element boundaries
  and topic sentences must be at least 30 characters, so unpunctuated menu
  strings can no longer masquerade as shipping or warranty evidence.
- The dashboard is multilingual: the UI language follows the browser
  language automatically (English and 简体中文 to start), with a header
  selector that persists the choice. All UI chrome, pillar names and
  explanations, check labels, summary verdicts, and status messages are
  localized in dashboard/i18n.js; engine-generated findings and
  recommendations remain English. Adding a language is one dictionary
  entry, enforced by a key-coverage test.
- Nine new deterministic page rules, implemented from the sourced candidate
  list in docs/RULES.md: GEO-OFFER-002 (price must exceed zero; fails the
  offer pillar checks), GEO-OFFER-003 (markup price visible in page text),
  GEO-RETURNS-001 (return policy required by AI shopping feeds),
  GEO-SHIPPING-001, GEO-IMAGE-001 (crawlable absolute image URLs),
  GEO-VARIANT-001 (variant-group markup), GEO-RATING-001 (AggregateRating
  for visible reviews), SEO-TITLE-002 (length/promo/all-caps title rules),
  SEO-SNIPPET-001 (noarchive/nocache/nosnippet degrade Copilot citations),
  and CLAIM-INJECTION-001 — prompt-injection text aimed at AI agents, which
  caps the page score at 49. Only the two network-dependent candidates
  (image dimensions, IndexNow key) remain proposed.
- The browser extension is now the full agent experience (v0.5.0): one
  click captures the active tab's rendered HTML and shows the verdict,
  score dial, expandable pillars with per-check details, findings with rule
  IDs, inline merchant questions with re-run, auto-drafted fix suggestions
  with validated preview and copyable JSON-LD, an ask-the-agent box, and
  HTML/JSON downloads. Talks only to the local server; MV3 with
  activeTab/scripting/storage permissions and local-only host permissions,
  enforced by tests.
- The dashboard now audits from a URL alone: a Fetch button and an
  auto-fetch on Audit ask the local server to retrieve the page via the new
  `/v1/fetch` route (one GET, http/https only, adapter-layer — the service
  still accepts supplied HTML only). Bot-protection interstitials are
  detected with a hint to paste the HTML instead; changing the URL clears
  stale HTML.
- `docs/RULES.md` — the full rule reference with provenance. Every rule is
  labeled Standard / Platform-derived / CatalogReady convention and cited
  against primary sources verified in July 2026: Google merchant-listing
  structured data and Merchant Center specs, OpenAI's crawler docs and
  Agentic Commerce Protocol feed schema, Bing's rewritten Webmaster
  Guidelines (Copilot grounding, noarchive/nocache effects) and MMC specs,
  Perplexity's crawler docs and Merchant Program terms, and Anthropic's
  crawler documentation. Includes 11 sourced candidate rules and documents
  that DeepSeek publishes no crawler or site-owner guidance.
- Robots access checks now cover all five documented AI search crawlers:
  googlebot, bingbot, oai-searchbot, and the new perplexitybot and
  claude-searchbot (`SEO-ROBOTS-PERPLEXITYBOT`, `SEO-ROBOTS-CLAUDE_SEARCHBOT`).
  Training-only bots (GPTBot, ClaudeBot, Google-Extended) are deliberately
  not flagged — blocking them does not affect answer inclusion.
- Every dashboard audit now opens with a plain-language summary conclusion:
  a verdict sentence, cap explanations, finding counts, the top priority
  action, and the auto-fix outcome.
- Fix suggestions are drafted automatically after every audit: the agent
  re-runs in draft mode in the background and the Fixes tab fills with
  reversible changes, the validated before/after score, and the JSON-LD patch.
- An "Ask the agent" chat window in the dashboard. Questions are answered
  from the audit result — deterministically by default, or by the selected
  BYO provider grounded strictly in the audit JSON (`/v1/agent/ask`,
  `answer_audit_question` service operation, shared `qa.py` module also
  used by the terminal chat).
- Dashboard pillars are now self-explanatory: click any pillar to expand a
  plain-language description of what it measures and the exact ✓/✗ checks
  behind its points, plus a note on how the 100-point total and caps work.
- `catalogready dashboard` — one command serves the interactive web UI and
  the local JSON API on the same port and opens the browser. The dashboard
  (packaged in `src/catalogready/dashboard/`) audits pasted product pages,
  renders the score dial and pillar bars, collects merchant answers inline,
  drafts evidence-backed fixes with isolated-preview validation, and
  downloads the HTML report via the new `/v1/report/html` route.

- `catalogready chat` (also `catalogready-chat`) — an interactive agent
  session in the terminal: streamed tool traces, colored score cards,
  `/audit`, `/answers` (pause-and-resume merchant Q&A), `/draft` with
  isolated-preview validation, `/findings`, `/jsonld`, `/report`, and
  free-text questions answered deterministically from the audit result,
  with optional BYO-model answers grounded strictly in the audit JSON.
- Shared `reporting/terminal.py` renderers and a `fetch.py` single-page
  fetch helper used by both the CLI and the chat adapter.

### Removed

- The standalone `frontend/` directory and its second static-file server.
  The packaged dashboard replaces it with a single-command, same-origin
  setup (no CORS configuration, no separate `http.server`).

## 0.5.0 — 2026-07-10

First public-launch candidate. The project now leads with one product:
an offline product-page AI-readiness checker.

### Added

- `catalogready audit <url> [saved.html]` — one command that scores a
  product page, prints a terminal score card, and writes a self-contained
  HTML report (`catalogready <url>` works as a shorthand).
- Self-contained HTML report with score dial, six pillar bars, findings
  with rule IDs, merchant questions, a paste-ready recommended Product
  JSON-LD block, and a downloadable PNG score card.
- Deterministic claim-grounding rules (`CLAIM-*`): superlative, rating,
  scientific/medical, warranty, and performance claims in listing copy
  are checked against page evidence.
- Visible body text now becomes cited evidence: shipping, returns,
  warranty, care, materials, and limitations statements are extracted as
  `page.*` evidence.
- `render_html_report` service operation.
- LICENSE, CI workflow, CONTRIBUTING, SECURITY, and issue templates.

### Changed

- **Scoring is now deduction-based with hard gates.** Catalog scores
  subtract severity-weighted deductions and are capped by structural
  defects (duplicate IDs cap at 69, mixed-brand variant groups at 79).
  The bundled `messy-apparel.csv` example now scores 51/100 instead of 95/100.
- The page readiness score has six pillars (identity, offer, structured
  data, decision evidence, media & variants, claim grounding) and caps for
  unsupported high-risk claims (49), missing stable identifiers (59),
  incomplete offers (69), and missing Product structured data (74).
- The optimization score no longer grades generated content. Journey and
  listing completeness moved to an informational `generation_quality`
  section and contribute zero points.

### Contracts

- `product-optimization-result.schema.json`: `readiness.components` now
  contains only source-evidence components; `generation_quality` added.
