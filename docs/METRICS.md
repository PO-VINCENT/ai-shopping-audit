# Metrics: what the rules measure, and how this score relates to others

The six scoring pillars ([scoring-methodology.md](scoring-methodology.md))
are the *aggregation* layer. Underneath, the rules measure eight distinct
qualities — the diagnostic lens a data-quality engineer would use. This
page maps every rule family to its metric and places the score in the
landscape of comparable systems.

In page-agent results, these metrics are reorganized beneath six score views:
a comprehensive view plus OpenAI, Google, Microsoft, Anthropic, and Perplexity.
Each platform view lists the relevant finding count and deductions for every
metric. The numeric platform score uses the canonical readiness arithmetic;
the metric rows remain an explanation of that score, not separate composites.

## The eight metrics

| Metric | Question it answers | Rules |
|---|---|---|
| **Machine readability** | Can a parser extract the product at all? | GEO-PRODUCT-001, GEO-PRODUCT-002, SEO-JSONLD-001, SEO-LANG-001, GEO-EVIDENCE-001, prose-specification fallback parsing |
| **Validity** | Is the data well-formed against its standard? | GEO-GTIN-001 (GS1 check digit), GEO-CURRENCY-001 (ISO 4217), GEO-AVAILABILITY-002 (schema.org ItemAvailability), GEO-OFFER-002 (price > 0) |
| **Completeness** | Are the fields agents require present? | AGENT-IDENTITY/OFFER-PRICE/OFFER-CURRENCY/OFFER-AVAILABILITY/BRAND/CATEGORY/IMAGE/DESCRIPTION, CAT-COLUMN-\*, CAT-VALUE-\*, CAT-ATTR-\*, GEO-RETURNS-001, GEO-SHIPPING-001, GEO-RATING-001 |
| **Consistency** | Does the markup match reality? | GEO-PRODUCT-003 (markup name ↔ page), GEO-OFFER-003 (markup price ↔ page), CAT-IDENTITY-001 (duplicate IDs), CAT-VARIANT-003/004, CAT-TAXONOMY-001 |
| **Trust & claim integrity** | Can the statements be believed? | CLAIM-SUPERLATIVE-001, CLAIM-RATING-001, CLAIM-PROOF-001, CLAIM-WARRANTY-001, CLAIM-PERFORMANCE-001, CLAIM-INJECTION-001, SEO-TITLE-002 |
| **Agent accessibility** | Can the documented AI crawlers reach and cite it? | SEO-ROBOTS-\<crawler\> (googlebot, bingbot, oai-searchbot, perplexitybot, claude-searchbot), SEO-ROBOTS-001 (noindex), SEO-SNIPPET-001, SEO-CANONICAL-001/002/003, SEO-SITEMAP-001/002, SEO-TITLE-001, SEO-DESC-001, SEO-HTTPS-001, GEO-IMAGE-001, GEO-IMAGE-002 (online mode) |
| **Transactability** | Could an agent complete a purchase on this data? | GEO-POLICY-001 (privacy/terms links), GEO-SELLER-001, GEO-RETURNS-002, GEO-SHIPPING-002, GEO-CONDITION-001, GEO-PRODUCT-004 (entity ambiguity), GEO-VARIANT-001 |
| **Freshness** | Is the data current? | GEO-OFFER-004 (expired priceValidUntil), SEO-INDEXNOW-001 (online mode) |

Two observations from building this matrix:

- **Consistency and trust are the differentiators.** Every comparable
  system checks readability and completeness; almost none check whether
  the markup *tells the truth* about the visible page, or whether
  marketing claims have evidence.
- **Freshness is the thinnest column** (two rules) — the most natural
  direction for future work.

## How this score relates to existing metrics

### Page-quality composite scores

- **Google Lighthouse** — 0–100 per category from weighted blends of
  continuous measurements (log-normal scoring curves). CatalogReady
  borrows the presentation (score dial, category bars, audits with
  documentation links) but not the arithmetic: compliance facts are
  binary, so check-sums with severity deductions and hard caps fit
  better than curves.
- **Core Web Vitals** — threshold buckets over *field* data. Its core
  idea, the lab-metric/field-metric split, is exactly this project's
  architecture: the readiness score is the lab metric (deterministic,
  reproducible, actionable); the deliberately separate
  `observed_ai_visibility` slot is the field metric (what AI systems
  actually cite, measured over time).
- **Mozilla HTTP Observatory / SSL Labs** — deduction-based security
  grades; the closest arithmetic relatives. They established that
  "start perfect, deduct per violation, cap on critical failure" is a
  publicly defensible scoring shape.

### SEO suite health scores

Semrush Site Health, Ahrefs Health Score, Moz Domain Authority: useful,
but proprietary and unexplainable numbers draw practitioner skepticism.
CatalogReady's response is [RULES.md](RULES.md) — every rule carries a
primary-source citation, and every score decomposes to named checks.

### Commerce data-quality metrics (closest domain cousins)

- **Google Merchant Center diagnostics** — per-item disapprovals, no
  composite score. CatalogReady effectively converts GMC's documented
  disapproval causes into scored, explainable rules.
- **GS1 Data Quality Framework / GDSN validations** — the industrial
  ancestor: attribute completeness and validity for trading partners.
  The GTIN check-digit rule comes straight from this world.
- **PIM content-health scores** (Salsify, Syndigo, Akeneo) —
  channel-specific completeness percentages; enterprise-priced and
  feed-side only. They don't audit the public page an AI agent reads.
- **Amazon listing quality / retail readiness** — marketplace-internal
  and opaque.

### GEO/AEO visibility tools (the new category)

Tools in this space (Profound, Otterly, Peec, Scrunch, HubSpot's AEO
grader, and academic metrics from the Princeton GEO paper) measure
**share-of-voice in AI answers**: they prompt LLMs repeatedly and count
citations. Those are *outcome* metrics — probabilistic, panel-dependent,
different on every run — and they cannot tell a merchant *why* a page
lost or *what to change*.

The positioning in one line: **they measure whether you are cited;
CatalogReady measures whether you are citable.** Input metrics and
outcome metrics answer different questions, and mature measurement
practice uses both — which is why observed visibility is a separate,
clearly-labeled slot in every CatalogReady result rather than part of
the readiness score.

### The unoccupied box

No other current system combines: **open source + deterministic +
citation-grounded + page-level + claim truthfulness + checkout
transactability**. The transactability metric in particular has no
competition yet — the protocols it audits against (UCP, ACP checkout)
are months old.

*(The established systems above are stable references; the GEO-tool
roster changes monthly and should be read as representative, not
exhaustive.)*
