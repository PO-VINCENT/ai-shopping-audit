# Scoring methodology

CatalogReady reports separate scores for separate questions. They must not
be combined into a claim about rankings, traffic, or conversion, and a high
score never guarantees citation by any AI system.

Two principles apply everywhere:

1. **Only the merchant's own data earns points.** Content that CatalogReady
   generates (journeys, queries, listing drafts) never contributes to a score.
2. **Blocking defects cap the score.** A page or feed with a defect that
   would mislead an AI shopping agent cannot present a high number, no
   matter how complete the rest of it is.

## Page AI readiness (the headline score)

Computed by `optimization/readiness.py` from page evidence and the page
audit. Six pillars, 100 points total:

| Pillar | Points | What it measures |
|---|---|---|
| Product identity | 20 | title, brand, category, stable ID (SKU/GTIN/MPN), canonical URL |
| Offer completeness | 20 | price, currency, availability, complete Offer markup |
| Structured data | 20 | Product JSON-LD present, identified, offer-complete, canonical, valid |
| Decision evidence | 15 | description, specifications, substantive visible text, evidence topics, reviews |
| Media & variants | 15 | primary image, multiple images, variant attributes, variant identity |
| Claim grounding | 10 | risky listing claims (superlatives, proof, warranty, performance) checked against evidence; deductions per finding |

Hard gates (the score is capped at the lowest triggered cap):

| Condition | Cap |
|---|---|
| Unsupported high-risk claim in listing copy | 49 |
| No stable product identifier | 59 |
| Price, currency, or availability incomplete | 69 |
| No Product structured data | 74 |

Status is `ready` only when the score is at least 80 and no cap fired.

## Catalog readiness

Computed by `catalog/scoring.py`:

```text
score = clamp( completeness − severity deductions, 0, cap )
```

- Completeness: populated required cells / total required cells × 100.
- Deductions per finding: high −10, medium −5, low −2.
- Caps: duplicate product IDs cap the score at 69; variant groups that mix
  brands cap it at 79.

The full breakdown (`base_completeness`, `severity_deductions`, `cap`,
`cap_reasons`) is reported in `summary.score_breakdown` so a screenshot of
the score can always be traced to its inputs.

## Discovery readiness

Page HTML contributes 75% of the discovery bundle score (title, canonical,
indexability, Product JSON-LD, product identity, complete Offer evidence,
substantive visible text). Crawler and sitemap checks contribute 25%
(Googlebot, OAI-SearchBot, and Bingbot access; canonical URL present in the
sitemap).

## Listing publish readiness (optimization workflow)

Computed by `optimization/scoring.py` for generated listings:

| Component | Points |
|---|---|
| Evidence grounding (supported claims / all claims) | 50 |
| Feed structured data completeness | 30 |
| Image readiness | 10 |
| Clarity and compliance | 10 |

Generated-content completeness (journey coverage, listing sections) is
reported in `generation_quality` and adds zero points. A contradicted or
unsupported high-risk claim caps the score at 49; incomplete price or
availability caps it at 79.

## Observed AI visibility

The headline score is the percentage of recorded observations that cite the
target domain. Product mentions, answer support, and citation share of voice
are reported separately. All observations should include provider and
timestamp. This score is always reported apart from readiness scores.
