# Product Visibility Agent

> This document describes the earlier listing-optimization pipeline, which
> remains available through `optimize-*` operations and the standalone
> dashboard. The v0.4 browser extension uses the bounded Product Readiness Agent
> documented in `product-readiness-agent.md`.

## Product contract

CatalogReady turns one authorized product record into:

1. a source-attributed evidence record;
2. suggested target customer types;
3. a six-stage shopping journey;
4. up to 20 question hypotheses;
5. an evidence-backed listing draft and supporting-image briefs;
6. a claim-by-claim evaluation;
7. a transparent Product AI Readiness score;
8. a separate placeholder for later observed AI visibility.

No generated output is published automatically.

## Workflow

```text
URL HTML / CSV / Shopify
            │
            ▼
    Product evidence record
            │
            ▼
 Customer types and journey
            │
            ▼
  Question/query hypotheses
            │
            ▼
 BYO model listing generation
            │
            ▼
 Deterministic + model claim audit
            │
            ▼
 Readiness score and merchant review
```

## Inputs

- `evidence_from_html`: extracts Product JSON-LD and safe page metadata from HTML
  supplied by the caller or browser extension.
- `evidence_from_csv`: normalizes one selected CSV row.
- `evidence_from_shopify`: normalizes an authorized Shopify GraphQL product
  object.
- `fetch_shopify_product`: optional read-only Admin GraphQL fetch using the
  permanent `*.myshopify.com` domain and a server environment token.

The local server does not crawl arbitrary URLs on behalf of an unauthenticated
request. The browser extension reads the page the user already opened.

## BYO providers

All provider adapters implement:

```python
class JsonModelProvider(Protocol):
    name: str
    model: str

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
    ) -> dict: ...
```

Supported REST boundaries:

- OpenAI Responses API;
- Gemini `generateContent`;
- Claude Messages API;
- DeepSeek Chat Completions;
- deterministic offline fallback.

API keys are read from server environment variables. Agent tools and browser
requests contain only provider name, model ID, market, and product evidence.

The selected live provider is called once to generate the listing and again to
evaluate claims unless a different evaluator provider is specified through the
service operation. Deterministic checks always run and model evaluation is not
allowed to upgrade a deterministic failure.

## Customer journey

The operational journey contains:

1. Need recognition.
2. Exploration.
3. Evaluation.
4. Validation.
5. Purchase.
6. Post-purchase.

Questions generated from category templates use `source: generated_hypothesis`
and `frequency: null`. They must not be described as popular or frequently asked
until connected search, review, support, or sales evidence supports that claim.

## Claim evaluation

Each generated claim contains text, risk, and evidence IDs. The deterministic
evaluator checks:

- every evidence ID exists;
- numeric values appear in the cited evidence;
- high-risk and superlative terms appear explicitly in evidence;
- price and availability statements are represented in the claim ledger;
- undeclared high-signal listing statements are blocked.

A live evaluator can downgrade a claim to partially supported, unsupported,
contradicted, or human review. It cannot upgrade a deterministic failure.

## Readiness score

| Component | Weight |
|---|---:|
| Evidence grounding | 30 |
| Journey/query coverage | 20 |
| Decision support | 20 |
| Feed and structured-data readiness | 15 |
| Image readiness | 10 |
| Clarity and compliance | 5 |

Contradicted or unresolved high-risk claims cap the result at 49. Incomplete
price/currency or availability caps it at 79. Observed AI visibility is never
silently inferred from readiness.

## Browser extension

The Manifest V3 extension uses only:

- `activeTab` to access the page selected by the user;
- `scripting` to collect the rendered HTML;
- `storage` for local server URL, provider, model, and market;
- localhost host permission to call the CatalogReady API.

It has no general browsing history permission, no storefront write permission,
and no API-key field.

## Primary current API references

- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Gemini generateContent](https://ai.google.dev/api/generate-content)
- [Claude Messages](https://platform.claude.com/docs/en/api/messages/create)
- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion)
- [Shopify Product GraphQL object](https://shopify.dev/docs/api/admin-graphql/latest/objects/product)
- [Google AI-generated product content](https://support.google.com/merchants/answer/14743464)
