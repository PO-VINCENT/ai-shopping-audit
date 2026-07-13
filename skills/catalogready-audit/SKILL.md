---
name: catalogready-audit
description: Audit product pages, saved HTML, or CSV catalogs for AI-shopping readiness with CatalogReady and explain comprehensive, OpenAI, Google, Microsoft Bing, Anthropic, and Perplexity scores, evidence-based findings, deductions, and safe fixes. Use when a user asks to audit a product URL, product page, HTML file, or catalog; compare platform readiness; inspect structured product data, offer completeness, claim grounding, or crawler access; explain a CatalogReady result; or build a grounded remediation plan.
---

# CatalogReady Audit

Use CatalogReady's deterministic engine as the source of truth. Keep this skill
as a thin workflow over the CLI; do not recreate scoring rules in the prompt.

## Choose the workflow

- Product URL: run `audit <url> --json`.
- Saved product HTML: run `audit <canonical-url> <html-file> --json`.
- CSV product catalog: run `catalog <csv-file>`.
- Existing audit JSON: read it directly; do not rerun unless the user requests
  fresh results.
- Rendered browser page: when browser control is available and the user wants
  rendered-page evidence, save the supplied/captured HTML and use the saved-HTML
  workflow. Otherwise explain that URL audit measures fetched static HTML.

Use the bundled runner from the skill directory:

```bash
python3 scripts/run_catalogready.py audit "https://shop.example/product" --json
python3 scripts/run_catalogready.py audit "https://shop.example/product" product.html --json
python3 scripts/run_catalogready.py catalog products.csv
```

The runner prefers the current CatalogReady repository, then an installed
`catalogready` executable, then `uvx --from catalogready-ai`. If package download
is required, obtain any approval required by the execution environment.

## Present the result

1. Lead with the comprehensive score and status.
2. List platform scores in this order: OpenAI, Google, Microsoft Bing,
   Anthropic, Perplexity.
3. Explain the exact arithmetic: raw check points minus deductions, followed by
   any safety cap.
4. Prioritize high-severity findings, then medium and low findings. Preserve
   rule IDs, evidence, affected platforms, and recommendations.
5. Separate facts observed on the page from merchant-supplied facts and
   proposed fixes.
6. Give the smallest high-impact remediation plan. Mark generated JSON-LD or
   copy as a proposal until the merchant verifies missing facts.
7. Link the generated HTML report when the command creates one.

## Guardrails

- Never invent product attributes, citations, rankings, prices, availability,
  policies, reviews, or merchant answers.
- Never count proposed or generated content toward the current readiness score.
- Keep catalog readiness, discovery readiness, and observed AI visibility
  separate. A readiness score is not evidence of ranking or citation.
- Treat provider scores as requirement-specific readiness views, not observed
  performance on those platforms.
- Use deterministic mode unless the user explicitly requests a configured model
  provider. Never accept or place provider API keys in arguments, browser
  storage, outputs, or skill files; keys belong in server environment variables.
- Do not write to a storefront, feed, merchant account, or external service.
- If a fetch is blocked or incomplete, report the limitation and request saved
  HTML or recommend the CatalogReady browser extension. Do not fabricate a
  result.

## Verification

Confirm the command exits successfully and the result contains structured
scores and findings before interpreting it. For JSON output, verify that
`schema_version`, `operation`, and the relevant readiness section are present.
