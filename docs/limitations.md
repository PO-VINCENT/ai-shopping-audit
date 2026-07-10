# Limitations

The reference implementation intentionally does not:

- crawl arbitrary websites;
- bypass robots, authentication, WAF or merchant access controls;
- call OpenAI, Anthropic, Google or other model providers automatically;
- modify a merchant catalog;
- validate all Google Merchant, Shopify, Schema.org or A2A fields;
- guarantee indexing, ranking, recommendation, citation or revenue impact;
- replace Search Console, Merchant Center or platform diagnostics;
- determine whether a product claim is legally substantiated.

The product agent is stateless and validates a normalized in-memory preview,
not a browser-rendered staging storefront. Resume requests must re-supply the
authorized HTML and verified merchant answers. The v1 agent exports proposed
changes but does not apply them.

The apparel taxonomy is deliberately small. Live providers should be added
behind `visibility/providers.py`, and every provider must preserve raw response,
timestamp, prompt ID and citation evidence.
