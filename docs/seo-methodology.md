# SEO methodology

The deterministic SEO audit works on content supplied by the caller. This keeps
authorization and network access with the host application.

Checks include:

- absolute canonical identity and canonical mismatch evidence;
- page-level `noindex` state;
- crawler access from supplied `robots.txt`;
- canonical URL inclusion in supplied sitemap XML;
- valid Product and Offer JSON-LD;
- title, description and visible text signals.

Structured data must match visible merchant content. A passing check indicates
technical eligibility, not guaranteed indexing or ranking.

