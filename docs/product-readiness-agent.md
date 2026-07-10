# Product Readiness Agent

## Purpose

The first-version agent accepts one authorized product page as supplied HTML.
It does not crawl the URL. The agent:

1. extracts a source-attributed product evidence record;
2. measures product identity, offer, structured-data, decision-evidence, image,
   and variant readiness;
3. prioritizes up to five deterministic findings;
4. asks the merchant for facts it cannot verify;
5. optionally drafts reversible JSON-LD, canonical, metadata, or visible-spec
   changes;
6. validates the change set against an isolated in-memory preview; and
7. returns a structured run trace and approval boundary.

## Agent versus deterministic tools

An explicitly selected model provider may choose the priority order from the
allowlisted findings. The provider cannot add findings, change scores, approve
claims, call arbitrary tools, fetch URLs, or publish changes. With the default
`deterministic` provider, the same run uses severity-first planning without a
network call.

The bounded tool sequence is:

```text
inspect_product_page
  -> audit_product
  -> plan_actions
  -> request_merchant_evidence (when needed)
  -> build_change_set (draft mode)
  -> validate_change_set (draft mode)
```

Runs are limited to eight recorded steps. Tool traces contain action summaries,
not hidden model reasoning.

## Modes

- `audit` returns evidence, readiness, findings, a plan, and merchant questions.
- `draft` additionally creates reversible changes and validates an in-memory
  preview. Merchant approval remains required before publishing.

The core performs no storefront writes in either mode.

## Merchant answers and resumption

Missing price, currency, availability, or stable identity blocks a run in
`needs_input`. Optional fields such as category and image remain advisory. A
caller resumes by running the agent again with the original supplied HTML, a
`merchant_answers` object, and the previous ID in `resumed_from`.

Merchant answers become evidence with `source: merchant_answer`. The reference
service is deliberately stateless and does not retain raw HTML, answers, or run
state.

## Result contract

The public result is defined in
`contracts/product-agent-run.schema.json`. Product readiness and observed AI
visibility remain separate. A validated-after score describes only the isolated
preview; it does not guarantee indexing, ranking, citation, or sales impact.
