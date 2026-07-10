# Changelog

## Unreleased

### Added

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
