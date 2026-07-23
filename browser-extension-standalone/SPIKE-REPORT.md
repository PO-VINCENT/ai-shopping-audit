# CatalogReady — standalone extension spike

**Goal (path C):** move the deterministic audit engine *into* the extension so a
Chrome Web Store user gets a score with **no local Python server**, while
model-assisted features (fix drafts, ask-the-agent) stay optional behind the server.

**Result: proven.** A dependency-free JavaScript port of the six-pillar product-page
audit runs in the browser and reproduces the Python score **exactly** on every fixture
tested. The extension now audits locally; the server is only touched for opt-in AI features.

---

## What was built

| File | What it is | Lines |
|---|---|---|
| `engine.mjs` | Dependency-free ES-module port of the deterministic audit. Exports `auditProductPage(html, url)` → the same `readiness.before` object Python emits, plus the display `findings`. Runs in Node **and** the browser (no `fs`/`require`/`DOMParser`). | ~1840 |
| `entities.mjs` | The HTML5 named-entity table, dumped from Python so `html.unescape` behaves identically. | 1 const |
| `parity.mjs` | Node harness: runs Python (`catalogready audit … --json`) vs the JS engine on each fixture and deep-compares 18 fields. Exits non-zero on any mismatch. | ~104 |
| `fixtures/` | Derived parity fixtures (clean / clinically-proven / injection / zero-price). | — |
| `extension-standalone/` | The loadable MV3 extension, rewired to the local engine. | — |

## Parity — Python is the oracle, JS must match

`node parity.mjs` → **ALL FIXTURES PASS** on all 18 compared fields:
score, raw_score, deductions, safety_cap, cap_reasons, the six pillar scores,
all six platform scores (comprehensive + 5 engines), and the findings rule-id set.

```
demo/index.html           PASS      fixtures/proof.html       PASS   (cap 49)
demo/bad-product.html     PASS      fixtures/injection.html   PASS   (cap 49)
fixtures/clean.html       PASS      fixtures/zero-price.html  PASS   (GEO-OFFER-002)
```

The port replicates CPython's `html.parser` tokenization by hand (not DOMParser/jsdom),
so `visible_words`, evidence topics, and spec extraction match byte-for-byte in both runtimes.

## How the extension changed (3 surgical edits)

The extension already captured the **rendered** HTML client-side
(`chrome.scripting.executeScript` → `document.documentElement.outerHTML`). Only the
audit itself lived on the server. Changes:

1. **Local audit.** `analyze()` and `resume()` call `localAudit(url, html)` — which calls
   the bundled engine — instead of POSTing to `127.0.0.1:8080`. The server `/health` gate is gone.
2. **Crawler view without a server.** `activateCrawlerView()` now does `fetch(url)` from the
   popup (raw static HTML = what non-rendering crawlers see) and audits it locally. The
   Rendered-vs-Crawler gap is computed entirely in the browser.
3. **Manifest.** `host_permissions` widened to `https://*/*`, `http://*/*` (needed for the
   crawler-view fetch). The engine is loaded into the popup via a tiny `engine-global.mjs`
   module shim; nothing is injected into pages.

**Still optional-server (opt-in, degrade quietly offline):** AI fix drafts (`draft` mode),
ask-the-agent, and the server-rendered HTML report. Keys never enter the extension. This
preserves your "nothing leaves the browser" default while keeping model features available.

## Load & try it

```
chrome://extensions → Developer mode → Load unpacked → select extension-standalone/
```
Open any product page → click the icon → **Score this product page**. No server running.

## Honest limits / recommended next steps

- **Single source of truth for rules.** This is a hand port; `parity.mjs` is the guard against
  drift and should run in CI as a cross-language release gate (mirrors your `evaluate.py` gate).
  The cleaner end-state is to externalize the rule tables into one JSON spec both Python and JS
  read — a follow-on refactor, not required for the extension to ship.
- **`resume()` with merchant answers** isn't ported (the standalone path returns no
  merchant-questions yet). Deterministic audit + score is fully local; answer-and-rerun is a follow-up.
- **Report/ask buttons** currently need the optional server; offline they should degrade to a
  friendly "optional feature" message or a locally-generated HTML report (small follow-up).
- **Web Store review:** broad `host_permissions` for the crawler fetch will draw an extra review
  pass; the justification (read-only audit of the page you're on) is defensible. Alternatively
  scope the fetch to `activeTab`-derived origins to narrow it.
- This spike was built against the **public GitHub** engine. If your local working copy has
  diverged, re-run `parity.mjs` against it before shipping.
