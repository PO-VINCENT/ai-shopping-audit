# Rule reference

Every CatalogReady finding carries a stable rule ID. This page documents
what each rule checks, why it exists, and where its requirement comes
from. Sources are labeled:

- **Standard** — a web standard or platform-published requirement, linked.
- **Platform-derived** — modeled on documented platform behavior, linked.
- **CatalogReady convention** — an editorial choice of this project. Weights,
  severities, and caps are always in this category; the arithmetic is in
  [scoring-methodology.md](scoring-methodology.md).

Severity semantics: **high** = an AI shopping agent would be misled or
blocked; **medium** = machine readability or trust is degraded; **low** =
polish. Some high-severity defects also cap the total score; caps are noted
with the rule.

All platform citations below were verified against the linked primary
sources in July 2026. Propose new rules with the **rule proposal** issue
template.

---

## What the platforms actually require

The rules are grounded in what six AI/search platforms publish. Summary of
the load-bearing facts, with primary sources:

### OpenAI (ChatGPT search & shopping)

- Search inclusion is controlled by **OAI-SearchBot** in robots.txt: "Sites
  that are opted out of OAI-SearchBot will not be shown in ChatGPT search
  answers." Allowing OAI-SearchBot is independent of **GPTBot** (training):
  a site can be searchable without opting into model training.
  ([OpenAI crawler docs](https://developers.openai.com/api/docs/bots))
- Shopping results use "structured metadata … (e.g., price, product
  description)" and rank merchants by "availability, price, quality, and
  whether they are the maker or primary seller."
  ([Shopping with ChatGPT search](https://help.openai.com/en/articles/11128490-shopping-with-chatgpt-search))
- The **Agentic Commerce Protocol** product feed requires: stable `item_id`
  (≤100 chars), `title` (≤150), `description` (≤5,000), resolving `url`,
  `brand`, `price` + ISO 4217 currency, `availability` enum, `image_url`,
  seller name/URL, and a **return-policy URL**; variants use `group_id` with
  distinct per-variant title/url/price/availability. Shopify and Etsy
  catalogs are integrated automatically.
  ([ACP product schema](https://developers.openai.com/commerce/specs/file-upload/products),
  [merchants page](https://chatgpt.com/merchants/))
- Notable: OpenAI's own docs do not recommend JSON-LD for ChatGPT inclusion —
  their documented levers are OAI-SearchBot access and the ACP feed.

### Google (merchant listings, Shopping, AI Overviews / AI Mode)

- Merchant listing structured data requires `Product.name`, `Product.image`,
  and an `Offer` with `price` (> 0) and ISO 4217 `priceCurrency`;
  `availability`, identifiers (`gtin`/`mpn`), `brand`, `category` (Text or
  `CategoryCode`, per the July 7 2026 update), return and shipping details
  are recommended.
  ([Merchant listing structured data](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing),
  [documentation updates](https://developers.google.com/search/updates))
- Put Product structured data "in the initial HTML for best results";
  JavaScript-rendered markup can reduce crawl freshness for price and
  availability. Structured data "must be a true representation of the page
  content." ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing),
  [structured data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies))
- Merchant Center requires per product: unique stable `id` (≤50 chars),
  `title` (≤150), `description`, `link`, `image_link`, `price` (must match
  the landing page and checkout), `availability` (must match the page),
  `brand` for new branded products, valid `gtin` where one exists, and
  coherent `item_group_id` variants. Duplicate IDs and feed/page mismatches
  are documented disapproval causes.
  ([product data specification](https://support.google.com/merchants/answer/7052112))
- AI Overviews/AI Mode eligibility rides on ordinary Search indexing and
  snippet eligibility via **Googlebot** — "no additional requirements," no
  special AI files or markup. **Google-Extended** controls Gemini training
  and grounding, not Search or AI Overviews.
  ([AI features](https://developers.google.com/search/docs/appearance/ai-features),
  [common crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers))

### Microsoft Bing (search, Shopping, Copilot)

- The Bing Webmaster Guidelines now govern "Bing search experiences,
  Copilot, and grounding API results" — same crawl/index/rank foundation.
  `noarchive` prevents content use in Copilot responses; `nocache` limits
  Copilot to URL/title/snippet; structured data must "accurately reflect
  visible content" and is validated (wrongly-typed values are ignored).
  A documented abuse category covers prompt injection / AI manipulation.
  ([Bing Webmaster Guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a),
  [structured data markup](https://www.bing.com/webmasters/help/marking-up-your-site-with-structured-data-3a93e731))
- **Bingbot** is the crawler (`bingbot/2.0` UA family); a `User-agent:
  Bingbot` robots group must repeat generic directives because Bing ignores
  the generic section when a specific one exists.
  ([Bing crawlers](https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0),
  [robots.txt guidance](https://www.bing.com/webmasters/help/how-to-create-a-robots-txt-file-cb7c31ec))
- **IndexNow** signals freshness for "a price drop, restock, or product
  launch," paired with schema.org Product markup: "IndexNow tells search
  engines *that* something has changed, while structured data tells them
  *what* has changed."
  ([IndexNow for Shopping](https://blogs.bing.com/webmaster/May-2025/IndexNow-Enables-Faster-and-More-Reliable-Updates-for-Shopping-and-Ads),
  [IndexNow documentation](https://www.indexnow.org/documentation))
- Microsoft Merchant Center requires `id`, `title` (≤150), `description`,
  `link` (same domain as store, no redirects), `image_link` (min 220×220,
  crawlable), `price` + ISO 4217 (must match the landing page); GTIN+brand+MPN
  for new branded products. Copilot shopping uses "both information found on
  the web and … a merchant's feed."
  ([MMC product attributes](https://help.ads.microsoft.com/apex/index/3/en/51084),
  [Copilot agentic commerce](https://about.ads.microsoft.com/en/solutions/technology/agentic-commerce))

### Perplexity

- **PerplexityBot** surfaces sites in Perplexity search results and respects
  robots.txt; **Perplexity-User** performs user-initiated fetches and
  "generally ignores robots.txt." Perplexity builds no foundation models, so
  blocked content is not a training question — blocking PerplexityBot removes
  citation eligibility.
  ([Perplexity crawlers](https://docs.perplexity.ai/guides/bots),
  [robots.txt FAQ](https://www.perplexity.ai/hub/technical-faq/how-does-perplexity-follow-robots-txt))
- The Merchant Program defines required product data: "product title, price,
  product description, brand or source, model, weight, in-stock and
  availability status, country of origin, shipping lead time, shipping
  options … dimensions," delivered as CSV/XML and kept "accurate at all
  times." Shopify integration powers discovery.
  ([Merchant Program terms](https://www.perplexity.ai/hub/legal/merchant-program-terms-of-service),
  [Shop Like a Pro](https://www.perplexity.ai/hub/blog/shop-like-a-pro))

### Anthropic (Claude)

- Three documented agents: **Claude-SearchBot** (search index quality),
  **Claude-User** (user-initiated fetches), **ClaudeBot** (training).
  All "respect 'do not crawl' signals … in robots.txt"; opt-outs are per
  subdomain; published IPs at claude.com/crawling/bots.json.
  ([Anthropic crawler documentation](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler))

### DeepSeek

- **No official crawler or site-owner documentation exists** — no published
  user agent, IP list, or robots.txt guidance anywhere on deepseek.com or
  api-docs.deepseek.com (verified July 2026). Third-party UA claims
  ("DeepseekBot/1.0") are unconfirmed. CatalogReady therefore ships no
  DeepSeek-specific rule: there is nothing documented to check against.

### The agentic checkout layer (UCP · ACP checkout · AP2)

Verified July 2026 — the protocols that let agents *transact*, not just read:

- **UCP (Universal Commerce Protocol)** is a cross-industry open standard
  co-developed by Google and Shopify (participants include Etsy, Target,
  Walmart, Amazon, Microsoft, Meta, Stripe; Apache-2.0, spec at
  [ucp.dev](https://ucp.dev/)). Google gates AI-Mode Buy buttons on the
  `native_commerce` feed attribute and requires a Merchant Center return
  policy and customer-support contact
  ([Google UCP guide](https://developers.google.com/merchant/ucp/guides/merchant-center),
  [Merchant Center help](https://support.google.com/merchants/answer/16837055));
  Microsoft's MMC adds `return_policy_labels` and
  `consumer_message_type/content` (legal/safety/Prop-65 warnings shown
  before purchase) as "UCP readiness" fields
  ([MMC product attributes](https://help.ads.microsoft.com/apex/index/3/en/51084)).
- **OpenAI ACP checkout**: `return_policy` (URL) is required
  unconditionally; `seller_name`/`seller_url` are required; and
  `seller_privacy_policy` + `seller_tos` become **required when a product
  is checkout-eligible**. OpenAI's production checklist verifies "Terms of
  Service and Privacy Policy links are present and functional"
  ([ACP product schema](https://developers.openai.com/commerce/specs/file-upload/products),
  [production guide](https://developers.openai.com/commerce/guides/production)).
  Microsoft's MMC store review likewise rejects sites for "lack of a
  'real' privacy policy" and non-SSL checkout
  ([MMC store setup](https://help.ads.microsoft.com/apex/index/3/en/60048)).
- **AP2 (Agent Payments Protocol)** — Google-led payment-mandate layer with
  60+ partners — imposes **no product-data or product-page requirements**
  (verified absence; [ap2-protocol.org](https://ap2-protocol.org/)). No
  CatalogReady rule derives from it.

The feed-only attributes (`native_commerce`, `consumer_message_*`,
`return_policy_labels`) are documented here for merchants but are not page
rules — CatalogReady audits their page-level counterparts below.

---

## Implemented rules

### `SEO-*` — page structure & crawler access (`discovery/`)

| Rule | Severity | Checks | Source |
|---|---|---|---|
| SEO-TITLE-001 | high | non-empty `<title>` | Platform-derived: Bing warns missing/duplicate titles "may reduce indexing reliability, ranking, and eligibility for grounding results" ([guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a)) |
| SEO-ROBOTS-001 | high | page does not request `noindex` | Standard: robots meta; Google requires snippet-eligible indexing for AI features ([AI features](https://developers.google.com/search/docs/appearance/ai-features)); OpenAI honors `noindex` even for link surfacing ([publishers FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)) |
| SEO-JSONLD-001 | medium | all JSON-LD blocks parse | Platform-derived: Bing validates annotations and ignores invalid ones ([markup docs](https://www.bing.com/webmasters/help/marking-up-your-site-with-structured-data-3a93e731)) |
| SEO-CANONICAL-001 | medium | canonical link present | Standard: RFC 6596 canonical link relation |
| SEO-CANONICAL-002 | medium | canonical is absolute http(s) | Standard: RFC 6596; Google canonicalization guidance |
| SEO-CANONICAL-003 | low | page canonicalizes to a different URL (confirm intent) | CatalogReady convention |
| SEO-SITEMAP-001 | low | sitemap supplied to the discovery bundle | Standard: [sitemaps.org](https://www.sitemaps.org); Bing asks for canonical-only sitemaps with accurate `lastmod` |
| SEO-SITEMAP-002 | medium | audited URL present in the sitemap | Same as above |
| SEO-TITLE-002 | medium | title ≤150 chars, no promotional text, not all-caps | Platform-derived: GMC and MMC title rules; OpenAI ACP title ≤150 ([GMC spec](https://support.google.com/merchants/answer/7052112), [MMC attributes](https://help.ads.microsoft.com/apex/index/3/en/51084), [ACP schema](https://developers.openai.com/commerce/specs/file-upload/products)) |
| SEO-SNIPPET-001 | medium | robots meta does not set `noarchive`/`nocache`/`nosnippet`/`max-snippet:0` | Platform-derived: Bing — `noarchive` blocks Copilot use entirely, `nocache` limits citations to URL/title/snippet; Google snippet controls gate AI Overviews ([Bing guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a), [Google AI features](https://developers.google.com/search/docs/appearance/ai-features)) |
| SEO-DESC-001 | low | a meta description exists on product pages | Platform-derived: Bing — missing/short descriptions "may reduce indexing reliability, ranking, and eligibility for grounding results" |
| SEO-LANG-001 | low | the `html` element declares `lang` | Standard: HTML language declaration; helps agents parse and localize |
| SEO-HTTPS-001 | medium | canonical and product image URLs use HTTPS | Platform-derived: agent checkout and crawling trust; CatalogReady convention on severity |
| SEO-ROBOTS-\<crawler\> | high | robots.txt does not block the crawlers that decide AI-answer inclusion: **googlebot** ([controls AI Overviews access](https://developers.google.com/search/docs/appearance/ai-features)), **bingbot** ([Bing/Copilot](https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0)), **oai-searchbot** ([ChatGPT search](https://developers.openai.com/api/docs/bots)), **perplexitybot** ([Perplexity](https://docs.perplexity.ai/guides/bots)), **claude-searchbot** ([Claude](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)) | Platform-derived (one rule per blocked crawler). Training bots (GPTBot, ClaudeBot, Google-Extended) are deliberately **not** flagged — blocking them does not affect search/answer inclusion, per each vendor's docs |

### `GEO-*` — machine-readable product data (`discovery/structured_data.py`)

| Rule | Severity | Checks | Source |
|---|---|---|---|
| GEO-PRODUCT-001 | medium (caps page score at 74) | a JSON-LD `@type: Product` node exists | Platform-derived: required for Google merchant listings ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)); Bing supports Product/Offer annotations ([markup docs](https://www.bing.com/webmasters/help/marking-up-your-site-with-structured-data-3a93e731)) |
| GEO-PRODUCT-002 | medium | Product node has a `name` | Standard: `name` is a required merchant-listing property (Google, above) |
| GEO-PRODUCT-003 | medium (fails the structured-data identity check) | the JSON-LD `name` appears in the visible page title or text — catches feed-artifact names like "Brand 1EA" that agents would read as the product name | Platform-derived: structured data "must be a true representation of the page content" ([Google SD policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)); Bing ignores markup that misrepresents visible content ([Bing guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a)) |
| GEO-OFFER-001 | medium | an offer combines `price` + `priceCurrency` + `availability` | Standard: `price`/`priceCurrency` required, `availability` recommended by Google (above); the same trio is required in OpenAI's ACP feed and ranks ChatGPT merchant lists ([ACP schema](https://developers.openai.com/commerce/specs/file-upload/products), [shopping help](https://help.openai.com/en/articles/11128490-shopping-with-chatgpt-search)) |
| GEO-OFFER-002 | high | machine-readable price is greater than zero (also fails the offer pillar checks) | Standard: "Merchant listing experiences require a price greater than zero"; GMC does not accept a price of 0 ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing), [GMC spec](https://support.google.com/merchants/answer/7052112)) |
| GEO-OFFER-003 | low | the markup price appears in the visible page text | Platform-derived: Google structured data must be "a true representation of the page content"; feed/page price mismatch is a GMC disapproval cause; Bing validates markup against visible content. Kept low severity because prices rendered by JavaScript are invisible to a static audit |
| GEO-RETURNS-001 | medium | returns info exists — `hasMerchantReturnPolicy` markup or visible returns text | Platform-derived: `return_policy` is a **required** OpenAI ACP feed field; recommended Offer property at Google; MMC UCP-readiness field ([ACP schema](https://developers.openai.com/commerce/specs/file-upload/products)) |
| GEO-SHIPPING-001 | low | shipping info exists — `shippingDetails` markup or visible shipping text | Platform-derived: Google recommended Offer property; Perplexity Merchant Program product data ([terms](https://www.perplexity.ai/hub/legal/merchant-program-terms-of-service)) |
| GEO-IMAGE-001 | low | product image URLs are absolute, crawlable http(s) URLs | Platform-derived: Google requires crawlable, indexable image URLs; MMC requires a crawlable image ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)) |
| GEO-VARIANT-001 | low | variant attributes (color/size/pattern) carry `inProductGroupWithID`/`isVariantOf` markup | Platform-derived: Google merchant-listing variant properties; ACP `group_id` ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)) |
| GEO-RATING-001 | low | visible review mentions have `aggregateRating` markup | Platform-derived: Google recommended property; ChatGPT shopping displays ratings from metadata ([shopping help](https://help.openai.com/en/articles/11128490-shopping-with-chatgpt-search)) |
| GEO-GTIN-001 | high | GTIN values pass GS1 validation (length 8/12/13/14 + mod-10 check digit) | Standard: GS1 check digit; GMC documents an incorrect GTIN as a disapproval cause ([GMC spec](https://support.google.com/merchants/answer/7052112)) |
| GEO-CURRENCY-001 | medium | `priceCurrency` is a recognized ISO 4217 code | Standard: ISO 4217; required format at Google, OpenAI ACP, and MMC |
| GEO-AVAILABILITY-002 | medium | `availability` is a schema.org ItemAvailability value, not free text | Standard: [schema.org ItemAvailability](https://schema.org/ItemAvailability); GMC and ACP define closed availability vocabularies |
| GEO-OFFER-004 | medium | `priceValidUntil` is not in the past | Platform-derived: recommended Offer property at Google; an expired date signals stale price data ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)) |
| GEO-PRODUCT-004 | medium | at most one ungrouped Product-with-offer per page (variants must use `isVariantOf`/`inProductGroupWithID`) | Platform-derived: Bing's "focus each URL on a single topic" entity-clarity guidance; Google merchant-listing variant properties |
| GEO-CONDITION-001 | medium | pages mentioning "refurbished"/"pre-owned"/"open box" declare `itemCondition` | Platform-derived: GMC requires `condition` for used/refurbished products ([GMC spec](https://support.google.com/merchants/answer/7052112)) |
| GEO-RETURNS-002 | medium | `hasMerchantReturnPolicy`, when present, is complete: `applicableCountry` + `returnPolicyCategory`, or a `merchantReturnLink` | Standard: Google's documented MerchantReturnPolicy requirement options ([return-policy markup](https://developers.google.com/search/docs/appearance/structured-data/return-policy)) |
| GEO-SHIPPING-002 | low | `shippingDetails`, when present, carries at least one of `shippingRate`/`shippingDestination`/`deliveryTime` | Platform-derived: documented OfferShippingDetails sub-properties ([merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)) |
| GEO-SELLER-001 | low | someone machine-readable sells the product: `brand`, `offers.seller`, or an `Organization` node | Platform-derived: OpenAI ACP requires `seller_name`/`seller_url` on every product ([ACP schema](https://developers.openai.com/commerce/specs/file-upload/products)) |
| GEO-POLICY-001 | medium | the page links a privacy policy and terms of service | Platform-derived: ACP requires `seller_privacy_policy`/`seller_tos` for checkout eligibility and verifies the links pre-launch; MMC rejects stores lacking "a 'real' privacy policy" ([ACP schema](https://developers.openai.com/commerce/specs/file-upload/products), [MMC store setup](https://help.ads.microsoft.com/apex/index/3/en/60048)) |
| GEO-EVIDENCE-001 | medium | ≥120 words of visible text | CatalogReady convention, aligned with Bing's "keep facts explicit and independently verifiable" content guidance |
| GEO-EVIDENCE-002 | low | shopper-evidence topics present (specs, limitations, shipping, returns) | Platform-derived: return policy is a required ACP feed field (OpenAI); shipping/returns are Perplexity Merchant Program product data ([terms](https://www.perplexity.ai/hub/legal/merchant-program-terms-of-service)) |

### `AGENT-*` — missing verified facts (`agent/tools.py`)

Each rule fires when the evidence record lacks a verified value, and pairs
with a merchant question instead of a guessed value (CatalogReady's
"never invent product facts" principle). The *fields themselves* are the
intersection of the three published feed specs (Google Merchant Center,
OpenAI ACP, Microsoft MMC), which agree on: stable id, title, description,
brand, image, price + ISO 4217 currency, availability.

| Rule | Severity | Missing fact |
|---|---|---|
| AGENT-IDENTITY-001 | high (caps at 59) | stable identifier (SKU/GTIN/MPN). GTIN validity is a Google disapproval rule; "use a unique value for each product" ([spec](https://support.google.com/merchants/answer/7052112)) |
| AGENT-OFFER-PRICE | high (offer gap caps at 69) | price. Google requires price > 0 and page/feed/checkout consistency |
| AGENT-OFFER-CURRENCY | high (offer gap caps at 69) | ISO 4217 currency (required by Google, OpenAI ACP, and MMC) |
| AGENT-OFFER-AVAILABILITY | high (offer gap caps at 69) | availability state (enum values match Google/ACP vocabularies) |
| AGENT-BRAND-001 | medium | brand (required for new branded products in Google/MMC; required in ACP) |
| AGENT-CATEGORY-001 | medium | category (Google merchant-listing `category`, July 2026 guidance) |
| AGENT-IMAGE-001 | medium | primary image (required by all three feed specs) |
| AGENT-DESCRIPTION-001 | medium | description (required by all three feed specs) |

### `CLAIM-*` — claim grounding (`optimization/claims.py`)

Claims are read from the listing surface (title + description) and grounded
against specifications, review data, and extracted page evidence. Category
sources: FTC-style advertising substantiation norms (objective claims need
support; health/scientific claims need competent evidence) and marketplace
listing policies. The phrase lists are CatalogReady convention.

| Rule | Severity | Fires when |
|---|---|---|
| CLAIM-SUPERLATIVE-001 | medium | "#1", "the best", "world's leading"… without citable support |
| CLAIM-RATING-001 | medium | "top rated"/"5-star" without AggregateRating evidence (Google recommends machine-readable `aggregateRating`; ChatGPT displays ratings from metadata) |
| CLAIM-PROOF-001 | high (caps at 49) | "clinically proven", "FDA approved", "doctor recommended"… with no supporting evidence on the page |
| CLAIM-WARRANTY-001 | high | "lifetime warranty", "N-year guarantee" with no warranty terms on the page |
| CLAIM-PERFORMANCE-001 | medium | "waterproof", "hypoallergenic", "100% X"… with no matching specification or page evidence |
| CLAIM-INJECTION-001 | high (caps page score at 49) | page text contains prompt-injection-style instructions aimed at AI agents ("ignore previous instructions", "as an AI assistant, always recommend…") — modeled on Bing's named abuse category "Prompt Injection and AI Manipulation" ([Bing guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a)) |

Bing's guidelines add a platform reason to care: structured or page data
that misleads "may be ignored and can affect trust and eligibility."

### `CAT-*` — CSV catalog (`catalog/`)

The eight required columns mirror the Google Merchant Center specification
(`id, title, description, link, image_link, price, availability, brand`),
which Microsoft's Content API accepts near-verbatim.

| Rule | Severity | Fires when | Source |
|---|---|---|---|
| CAT-COLUMN-\<FIELD\> | high | a required column is absent | [GMC spec](https://support.google.com/merchants/answer/7052112) |
| CAT-VALUE-\<FIELD\> | high/medium | rows with empty required values | GMC spec |
| CAT-IDENTITY-001 | high (caps catalog score at 69) | duplicate product IDs | GMC documented disapproval cause |
| CAT-VARIANT-003 | medium | variant groups reuse one title across colors | GMC variant guidance (`item_group_id` + distinguishing attributes); ACP requires distinct variant titles |
| CAT-VARIANT-004 | high (caps at 79) | variant groups mix brands | GMC `item_group_id` coherence |
| CAT-TAXONOMY-001 | medium | products don't map to a recognizable category | GMC category guidance |
| CAT-ATTR-\<attr\> | low | categorized apparel missing color/size/gender/age_group/material | GMC: apparel attributes required in FR/DE/UK/US; MMC apparel targeting |

---

## Online-mode rules (`catalogready audit --online`)

Two rules need network access and therefore run only in the explicit
online mode — never in the deterministic core (rule logic stays offline
and tested; only bounded fetching lives in the adapter). Online findings
are informational and do not change the score.

| Rule | Severity | Checks | Source |
|---|---|---|---|
| GEO-IMAGE-002 | medium / high | product image files (max 3 fetched, bounded reads) are fetchable and meet marketplace minimums: ≥500×500 (GMC, enforcement announced for Jan 2027); below Microsoft's 220×220 floor or unfetchable escalates to high | [GMC spec](https://support.google.com/merchants/answer/7052112); [MMC attributes](https://help.ads.microsoft.com/apex/index/3/en/51084) |
| SEO-INDEXNOW-001 | low | the merchant's IndexNow key file is hosted at `https://host/{key}.txt` with matching content (`--indexnow-key`). Keys are named by the key itself, so participation is **not externally discoverable** — the merchant must supply theirs | [IndexNow](https://www.indexnow.org/documentation); [Bing shopping-freshness blog](https://blogs.bing.com/webmaster/May-2025/IndexNow-Enables-Faster-and-More-Reliable-Updates-for-Shopping-and-Ads) |

Every candidate rule collected from platform documentation is now
implemented. Not implemented by design: DeepSeek-specific rules (no
documented requirements exist) and training-crawler rules
(GPTBot / ClaudeBot / Google-Extended do not affect answer inclusion,
per each vendor's documentation).

---

## Primary sources

- OpenAI: [crawler docs](https://developers.openai.com/api/docs/bots) · [shopping help](https://help.openai.com/en/articles/11128490-shopping-with-chatgpt-search) · [ACP feed spec](https://developers.openai.com/commerce/specs/file-upload/products) · [merchants](https://chatgpt.com/merchants/) · [publishers FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)
- Google: [merchant listing structured data](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing) · [product data spec](https://support.google.com/merchants/answer/7052112) · [AI features](https://developers.google.com/search/docs/appearance/ai-features) · [common crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers) · [structured data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) · [doc updates](https://developers.google.com/search/updates)
- Microsoft: [Bing Webmaster Guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a) · [structured data](https://www.bing.com/webmasters/help/marking-up-your-site-with-structured-data-3a93e731) · [crawlers](https://www.bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0) · [MMC product attributes](https://help.ads.microsoft.com/apex/index/3/en/51084) · [IndexNow](https://www.indexnow.org/documentation) · [Copilot agentic commerce](https://about.ads.microsoft.com/en/solutions/technology/agentic-commerce)
- Perplexity: [crawlers](https://docs.perplexity.ai/guides/bots) · [robots FAQ](https://www.perplexity.ai/hub/technical-faq/how-does-perplexity-follow-robots-txt) · [Merchant Program terms](https://www.perplexity.ai/hub/legal/merchant-program-terms-of-service) · [Shop Like a Pro](https://www.perplexity.ai/hub/blog/shop-like-a-pro)
- Anthropic: [crawler documentation](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
- DeepSeek: no crawler/site-owner documentation published (verified July 2026)
