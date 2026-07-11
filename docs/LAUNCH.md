# Launch runbook

Everything below is either DONE (in the repo) or a manual step with the
copy pre-written. Work top to bottom.

## Phase 0 — already in the repo

- [x] LICENSE (Apache-2.0), CI, CONTRIBUTING, SECURITY, issue templates, CHANGELOG
- [x] Release workflow (`.github/workflows/release.yml`) — PyPI Trusted
  Publishing on `v*` tags + extension zip artifact
- [x] Extension icons (16/32/48/128) and packaging script
  (`scripts/package-extension.sh`)
- [x] Benchmark runner (`scripts/benchmark.py`)
- [x] `docs/BYO-KEYS.md` + friendly missing-key hints in dashboard/extension
- [x] Rules documented with primary sources (`docs/RULES.md`)

## Phase 1 — GitHub (you; ~30 min)

1. Create the repository, then:
   `git remote add origin git@github.com:<org>/catalogready.git && git push -u origin main`
2. Settings → About:
   - Description: `Open-source product-data readiness checker for AI shopping. Audit Product schema, feeds and claims locally — no API key required.`
   - Topics: `ecommerce ai-shopping product-feed structured-data schema-org merchant-center shopify seo geo mcp python`
   - Social preview: screenshot of a score card (dashboard, bad demo, dark mode).
3. Settings → Security: enable private vulnerability reporting.
4. Verify CI is green on the first push.

## Phase 2 — PyPI (you; ~30 min)

1. Create a PyPI account → Publishing → **add Trusted Publisher**:
   repository `<org>/catalogready`, workflow `release.yml`, environment `pypi`.
2. In the GitHub repo: Settings → Environments → create `pypi`.
3. `git tag v0.5.0 && git push origin v0.5.0` — the workflow tests, builds,
   and publishes.
4. Smoke-test from a clean machine:
   `uvx --from catalogready-ai catalogready https://www.deathwishcoffee.com/products/death-wish-coffee`

## Phase 3 — demo assets (you; ~1 hr)

- GIF (10–15 s) for the README top: dashboard → load bad demo → Audit →
  16/100 with cap banner → Fixes tab → validated 16 → 60. Record with Kap
  or QuickTime + gifski, ≤ 5 MB.
- Screenshots for the extension listing (1280×800): popup on a real
  product page, one English, one Chinese.

## Phase 4 — benchmark content (you + me)

1. Collect ~50 product URLs across known stores (mix of Shopify, big-box,
  marketplaces) into `urls.txt`.
2. `uv run python scripts/benchmark.py urls.txt BENCHMARK.md` (one GET per
   page, 3 s delay). Bot-blocked stores are reported, not scored.
3. Commit `BENCHMARK.md`; the closing line ("X% not ready") is the hook.

## Phase 5 — announce

**Show HN title:** `Show HN: CatalogReady – Lighthouse for AI shopping.
Is your product page readable by AI agents?`

**Show HN text (first comment):** built this after noticing product pages
that look perfect to humans are unreadable to ChatGPT/Perplexity/Copilot
shopping agents — a real supermarket marketplace page's markup names a
treadmill "Everfit 1EA". One command (`uvx --from catalogready-ai
catalogready <url>`) gives a 0–100 score from ~40 deterministic rules,
each cited to platform docs (docs/RULES.md). Offline, no API key, no
account; score is deduction-based with hard caps so it can't be gamed.
Also: local dashboard, Chrome extension, MCP server, and an agent that
drafts the JSON-LD fix and validates it against an in-memory preview —
it never writes to a store and never invents product facts.

**X/LinkedIn hook:** "Your store looks perfect to humans and invisible to
AI shopping agents. I audited 50 top stores — X% fail. Open-source
checker, no API key: [repo]" + score-card screenshot + benchmark table.

**MCP-audience post (separately):**
`claude mcp add catalogready -- uvx --from catalogready-ai catalogready-mcp`
"give your agent a product-page auditor."

Channels, in order: Show HN → X thread → r/ecommerce + r/shopify →
LinkedIn → MCP/dev-tools communities.

## Phase 6 — Chrome Web Store (you; ~1 hr + review days)

1. Register: https://chrome.google.com/webstore/devconsole ($5 one-time).
2. Package: `sh scripts/package-extension.sh` → upload
   `dist/catalogready-extension-v0.5.0.zip`.
3. Listing copy:
   - Name: `CatalogReady — AI Readiness Score`
   - Summary: `Score any product page 0–100 for AI shopping readiness. One click: findings, merchant questions, evidence-backed fixes.`
   - Category: Developer Tools (or Shopping)
   - Description: popup features + REQUIRED honesty line: *"Companion to
     the open-source CatalogReady tool. Requires the free local server —
     start it with one command (`uvx --from catalogready-ai catalogready
     dashboard`). Page data is sent only to your own machine."*
4. Privacy tab:
   - Single purpose: "Audit the current product page for AI shopping
     readiness using the user's local CatalogReady server."
   - Permission justifications — `activeTab`/`scripting`: "reads the
     rendered HTML of the current page when the user clicks the action";
     `storage`: "saves the local server URL, provider name, model ID, and
     language"; host permissions: "localhost only — results come from the
     user's own machine".
   - Data use: page content is transmitted only to the user's local
     server; no data is collected by the developer.
5. Submit; typical review is a few days. Until approved, README's
   load-unpacked instructions are the path.

## Launch-day checklist

- [ ] CI green, tag published, `uvx` one-liner works from a clean machine
- [ ] README GIF renders on GitHub
- [ ] BENCHMARK.md committed and linked from README
- [ ] Dashboard demo (`catalogready dashboard`) works from a fresh
      `uvx`/pip install (no repo checkout)
- [ ] Post Show HN in the morning (US time); reply fast for the first 3 h
- [ ] Rotate any API keys that were used during development
