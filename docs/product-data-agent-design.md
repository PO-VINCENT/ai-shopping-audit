# Product Data Agent design

## 1. Goal and scope

The Product Data Agent gives a retailer one read-only, evidence-backed view of:

1. **Product data** from commerce platforms, marketplaces, cloud data stores,
   files and internal APIs, including specifications, listings and prices.
2. **Product feedback** from native reviews, review providers, support systems,
   returns, surveys and approved social channels.
3. **Product inventory** by variant, location and sales channel.

This document interprets “product inventor information” as **product inventory
information**. Manufacturer, brand owner and designer provenance can also be
stored as optional catalog attributes if “inventor” was meant literally.

The first release is intentionally narrow. It reads and normalizes authorized
data, reports quality and freshness, and exposes the result to agents. It does
not write to merchant systems, forecast demand, scrape protected sites or let a
model manufacture missing product facts.

## 2. Product promise

> Connect a store or product feed and receive a source-attributed product,
> feedback and inventory health report that any MCP, A2A or HTTP client can use.

This is a strong open-source demonstration because it combines retail domain
modeling, data engineering, API integration, evidence handling and safe agent
design without requiring a large feature surface.

## 3. Architecture

```text
Authorized sources
  ├─ Commerce: Shopify, WooCommerce, internal commerce APIs
  ├─ Cloud: GCS/BigQuery/Pub/Sub, S3/EventBridge, Blob/Event Grid
  ├─ Feedback: native reviews, Bazaarvoice, Trustpilot, support, returns
  └─ Inventory: commerce, ERP, WMS, OMS, marketplace and supplier feeds
                         │
                         ▼
                 Connector runtime
        discovery · auth · full sync · delta · webhook
                         │
                         ▼
             Immutable raw source envelopes
            payload · cursor · checksum · provenance
                         │
                         ▼
       Normalization and product identity resolution
                         │
             ┌───────────┼────────────┐
             ▼           ▼            ▼
          catalog/   feedback/    inventory/
             └───────────┼────────────┘
                         ▼
           Quality, freshness and reconciliation
                         │
                         ▼
              Vendor-neutral service facade
              CLI · MCP · A2A · REST/OpenAPI
```

### Deterministic core and model-assisted edge

The deterministic core owns authentication boundaries, pagination, parsing,
identity, quantity math, evidence, scoring and contract validation. A host model
may help explain findings, group feedback themes or propose mappings, but its
output is marked as derived and cannot overwrite source facts without approval.

## 4. Proposed repository extension

The existing `catalog/`, `discovery/` and `visibility/` packages remain intact.
The Product Data Agent adds reusable ingestion and three retail data domains.

```text
src/catalogready/
├── ingestion/
│   ├── base.py                 # Connector protocol and capability types
│   ├── registry.py             # Connector registration and selection
│   ├── config.py               # Secret-free connection configuration
│   ├── cursors.py              # Incremental-sync cursor state
│   ├── envelopes.py            # Raw payload and provenance envelope
│   ├── orchestration.py        # Full, delta and event sync workflow
│   ├── webhooks.py             # Signature verification and deduplication
│   └── health.py               # Rate limit, lag and connector health
├── connectors/
│   ├── shopify.py              # Admin GraphQL products and inventory
│   ├── woocommerce.py          # REST products, stock and native reviews
│   ├── generic_http.py         # REST/GraphQL/OpenAPI mapping connector
│   ├── object_storage.py       # CSV/JSON/JSONL from GCS, S3 and Azure Blob
│   ├── bigquery.py             # Later: warehouse query connector
│   ├── amazon_sp_api.py        # Later: catalog, feedback and FBA inventory
│   ├── bigcommerce.py          # Later
│   ├── adobe_commerce.py       # Later
│   └── commercetools.py        # Later
├── catalog/
│   ├── schemas.py              # Product, Variant, Specification, Listing, Price
│   ├── normalization.py        # Source record to canonical catalog entity
│   ├── specifications.py       # Attribute names, values, units and vocabularies
│   ├── listings.py             # Channel publication and listing quality
│   ├── pricing.py              # Price types, validity and observations
│   ├── taxonomy.py
│   ├── variants.py
│   └── scoring.py
├── feedback/
│   ├── schemas.py              # Review, support, return and survey feedback
│   ├── channel_discovery.py    # Evidence-based provider/channel candidates
│   ├── normalization.py        # Channel payload to canonical feedback
│   ├── product_linking.py      # SKU/GTIN/source-ID/URL linkage
│   ├── topics.py               # Deterministic and optional model-assisted tags
│   ├── metrics.py              # Ratings, volume, trend and coverage
│   └── privacy.py              # PII minimization and deletion propagation
├── inventory/
│   ├── schemas.py              # Location, inventory state and inventory event
│   ├── normalization.py        # Provider quantities to canonical states
│   ├── ledger.py               # Append-only change ledger
│   ├── precedence.py           # Configurable source-of-truth rules
│   ├── reconciliation.py       # Difference detection, never silent merging
│   ├── freshness.py            # Staleness and SLA evaluation
│   └── alerts.py               # Stockout, stale feed and mismatch findings
├── identity/
│   ├── graph.py                # Canonical IDs to provider IDs
│   ├── matching.py             # Exact identifiers first; fuzzy suggestions only
│   └── conflicts.py            # Ambiguous and duplicate product handling
├── storage/
│   ├── raw.py                  # Immutable payload interface
│   ├── canonical.py            # Current canonical state interface
│   └── state.py                # Cursor, job and idempotency state interface
├── reporting/
├── service.py
├── cli.py
├── mcp_server.py
└── api_server.py

contracts/
├── connector.schema.json
├── raw-envelope.schema.json
├── canonical-product.schema.json
├── specification.schema.json
├── listing.schema.json
├── price-observation.schema.json
├── feedback.schema.json
├── inventory-snapshot.schema.json
└── data-health-result.schema.json

examples/
├── connectors/
│   ├── shopify.example.yaml
│   ├── woocommerce.example.yaml
│   └── object-storage.example.yaml
├── product-data/
├── feedback/
└── inventory/

tests/
├── fixtures/                   # Recorded, redacted provider responses
├── test_ingestion.py
├── test_identity.py
├── test_feedback.py
├── test_inventory.py
└── contract/
```

## 5. Connector contract

Every connector implements the same small interface. Provider-specific behavior
stays inside the connector; domain rules stay in domain packages.

```python
class ProductDataConnector(Protocol):
    descriptor: ConnectorDescriptor

    def discover(self) -> DiscoveryResult: ...
    def test_connection(self) -> ConnectionHealth: ...
    def full_sync(self, resource: ResourceKind) -> Iterable[RawEnvelope]: ...
    def delta_sync(
        self, resource: ResourceKind, cursor: SyncCursor
    ) -> SyncBatch: ...
    def verify_event(self, headers: Mapping[str, str], body: bytes) -> Event: ...
```

`ConnectorDescriptor` declares capabilities instead of relying on connector
names:

```text
resources: catalog | inventory | reviews | orders | returns | support
sync_modes: full_pull | cursor_pull | timestamp_pull | webhook | event_stream
auth: oauth2 | api_key | signed_request | workload_identity | service_account
limits: page_size, request_cost, concurrency and retry hints
freshness_sla: expected maximum observation lag
```

The orchestration layer must support pagination, checkpointing, exponential
backoff, rate-limit headers, idempotent replay and dead-letter capture.

## 6. Module 1 — product data extraction

### 6.1 Source categories

| Category | Initial connectors | Later connectors | Typical mode |
|---|---|---|---|
| Commerce | Shopify, WooCommerce | BigCommerce, Adobe Commerce, commercetools, Salesforce Commerce Cloud | full pull + delta/webhook |
| Marketplace | — | Amazon SP-API, Walmart Marketplace, eBay | pull + reports/events |
| Internal APIs | REST, GraphQL, OpenAPI-driven mapping | gRPC and custom SDK adapters | timestamp/cursor pull |
| Cloud files | GCS, S3, Azure Blob CSV/JSON/JSONL | Parquet and Avro | object event + file read |
| Warehouses | file export first | BigQuery, Redshift/Athena, Snowflake, Synapse | scheduled query/CDC |
| Enterprise | SFTP CSV first | PIM, ERP, WMS, OMS and supplier EDI | scheduled pull/event |

Cloud vendors are transports, not catalog systems. The connector therefore
separates storage access from a merchant-owned mapping profile. For example,
the same CSV schema can be read from GCS, S3 or Azure Blob.

### 6.2 Canonical catalog model

The minimum entities are:

- `Product`: merchant product concept, title, description, brand, taxonomy,
  lifecycle and source timestamps.
- `Variant`: SKU-level option combination and identifiers such as GTIN/MPN.
- `Specification`: typed product or variant fact with value, unit, group,
  vocabulary and source, such as material, capacity, dimensions or care.
- `Listing`: a product/variant presentation on one channel and market, including
  seller, title, description, URL, publication status and channel identifiers.
- `Offer`: a purchasable listing/variant combination with seller, market,
  condition, fulfillment terms and availability.
- `PriceObservation`: a time-bound price attached to an offer, with price type,
  currency, tax treatment, effective dates and source.
- `Asset`: image/video URL, role, dimensions, alt text and checksum.
- `Party`: brand owner, manufacturer, designer or supplier when supplied.
- `SourceRef`: provider, tenant, resource type, external ID and source URL.

### 6.2.1 Product specifications

Specifications must not be stored as an unstructured dictionary only. Each
source fact should be representable as:

```text
Specification
├── owner_type: product | variant
├── owner_id
├── name_source                  # e.g. "Screen Size"
├── name_normalized              # e.g. "display.diagonal"
├── value_source                 # e.g. "6.1 inches"
├── value_normalized             # e.g. 6.1
├── data_type: text | number | boolean | enum | measurement
├── unit_source and unit_normalized
├── group                        # dimensions, materials, compatibility, care...
├── vocabulary and vocabulary_version
├── locale and market
├── source_ref
└── normalization_status: exact | mapped | suggested | unresolved
```

Keep original and normalized values together. Unit conversion is deterministic
and versioned. Model-proposed attribute mappings remain suggestions until an
operator approves them. Variant-specific facts must not be promoted to the
parent product when variants disagree.

### 6.2.2 Listings

A product can have many listings: Shopify AU, Amazon US and a Google Merchant
listing are separate records even when they refer to the same variant.

```text
Listing
├── listing_id and source_ref
├── product_id and optional variant_id
├── channel, seller_id, market and locale
├── external_listing_id
├── title, description and product_url
├── status: draft | active | paused | rejected | archived
├── category_source and category_normalized
├── identifiers presented on the listing
├── shipping/returns summary when supplied
├── published_at, source_updated_at and observed_at
└── issues supplied by the channel
```

This lets the agent report title/specification drift, missing identifiers,
channel rejection reasons, stale content and duplicate listings without treating
the commerce source as the only truth.

### 6.2.3 Prices

Price is not a stable Product field. It belongs to an offer, market, currency
and period. Preserve observations so changes are explainable.

```text
PriceObservation
├── offer_id
├── kind: current | list | compare_at | sale | msrp | map | cost | unit
├── amount and currency
├── tax_included and tax_rate (when explicitly supplied)
├── unit_quantity and unit_measure (for unit pricing)
├── quantity_min and quantity_max (for tiered pricing)
├── customer_segment            # public, member, B2B tier; no PII
├── promotion_id
├── valid_from and valid_to
├── observed_at
└── source_ref
```

The agent may calculate deterministic facts such as discount percentage when
both compatible current and list prices are present. It must not compare prices
across currencies, tax treatments, pack sizes or customer segments without an
explicit normalization rule. Cost, MAP and private B2B prices require stricter
authorization than public selling prices.

Identity resolution uses exact identifiers in this order:

1. Existing `SourceRef` mapping.
2. Merchant-scoped SKU.
3. Valid GTIN plus brand/manufacturer context.
4. MPN plus brand/manufacturer context.
5. Merchant-approved mapping table.
6. Fuzzy title/attribute match as a **suggestion only**.

An unresolved record is quarantined for review rather than silently attached to
the wrong product.

### 6.3 Source-specific design notes

- **Shopify:** use the Admin GraphQL product model for products and variants.
  Inventory is represented by inventory items and location-specific inventory
  levels. Webhooks cover product and inventory changes and can target HTTPS,
  Google Pub/Sub or AWS EventBridge.
- **WooCommerce:** use authenticated REST endpoints for merchant catalog and
  stock. Its product model exposes stock-management fields, while the Store API
  provides public catalog and product-review reads. Paginate all collection
  endpoints.
- **Internal APIs:** accept a declarative field map, pagination strategy,
  authentication reference, modified-time field and deletion/tombstone policy.
  Generate a dry-run mapping report before the first sync.
- **GCP/AWS/Azure:** support object storage first. Object-created notifications
  enqueue a sync; the worker then reads and checksums the file. Add warehouse
  and stream connectors only after the canonical contracts are stable.

## 7. Module 2 — product reviews and feedback

### 7.1 Recommended channel map

The agent should discover and recommend channels, not assume every retailer has
them all.

| Signal | Example channels | Value | Product linkage |
|---|---|---|---|
| Native product reviews | WooCommerce reviews; store-specific review data | Direct product experience | product ID, SKU, URL |
| Review platforms | Bazaarvoice, Yotpo, Trustpilot, Judge.me, Okendo, PowerReviews, Stamped | Rating, text, aspects, helpfulness | provider product ID, SKU, URL |
| Marketplaces | Amazon Customer Feedback insights and approved marketplace APIs | Topic and return trends | ASIN/listing/SKU |
| Search/merchant programs | Google Merchant product reviews | Product-rating visibility and feed health | GTIN, SKU, product URL |
| Customer support | Zendesk, Gorgias, Intercom, Freshdesk | Defects, fit, setup and delivery pain | SKU/order line when present |
| Returns/refunds | Shopify/Woo returns, Loop, Narvar, AfterShip, OMS | Concrete failure reasons | order line and variant |
| Surveys | Qualtrics, Medallia, SurveyMonkey, Typeform | Structured CSAT/NPS and verbatim text | explicit product question/order |
| Community/social | Reddit, YouTube, approved social APIs | Emerging language and issues | URL, explicit identifier, reviewed match |

First-party reviews, returns and support tickets should be prioritized because
the merchant controls access and product linkage is usually stronger. Social
content should be optional and collected only through permitted APIs and terms.

### 7.2 Channel discovery workflow

`feedback.channel_discovery` returns candidates with evidence and confidence:

1. Inspect supplied storefront HTML for known review-widget scripts and app
   embeds.
2. Parse Product JSON-LD for `aggregateRating` and `review`, recording the page
   as evidence but not treating rendered markup as the system of record.
3. Inspect merchant-provided installed-app or integration metadata when the
   platform API permits it.
4. Ask the operator which help desk, returns platform, survey platform and
   marketplace accounts they control.
5. Test read-only API access and return available resource types and date range.
6. Require explicit authorization before a sync is enabled.

Example result:

```json
{
  "channel": "bazaarvoice",
  "kind": "product_reviews",
  "confidence": 0.96,
  "evidence": [
    {"type": "script_host", "value": "display.ugc.bazaarvoice.com"},
    {"type": "json_ld", "value": "Product.aggregateRating"}
  ],
  "status": "authorization_required",
  "recommended_connector": "bazaarvoice"
}
```

### 7.3 Canonical feedback model

```text
Feedback
├── feedback_id and SourceRef
├── kind: review | support | return | survey | social
├── product_id / variant_id / offer_id (nullable until resolved)
├── linkage_method and linkage_confidence
├── rating, title, body, language
├── verified_purchase, incentivized, syndicated
├── helpful_count and moderation_status
├── return_reason or support_category
├── occurred_at, created_at, updated_at, observed_at
├── source_author_hash (no raw PII by default)
└── provenance and deletion_state
```

Derived fields such as sentiment, topic and summary must name the algorithm or
model, version, generation timestamp and source feedback IDs. Raw text and
derived interpretation must remain separable.

### 7.4 Metrics

- Review coverage: reviewed products / active products.
- Verified purchase ratio and incentivized/syndicated ratios when available.
- Rating distribution and change over comparable time windows.
- Feedback volume by product, variant, market and channel.
- Recurring topic rate and return/support co-occurrence.
- Unlinked feedback rate and average linkage confidence.
- Deletion synchronization health and data freshness.

These are observed metrics, not causal claims. The report must not claim that a
review trend caused sales or search ranking without appropriate analysis.

## 8. Module 3 — inventory information

### 8.1 Canonical model

Inventory exists at a `variant × location × channel` grain. Flattening it to a
single number causes overselling and misleading reports.

```text
InventorySnapshot
├── inventory_id
├── product_id and variant_id
├── sku
├── location_id and channel_id
├── on_hand
├── reserved
├── committed
├── available_to_sell
├── incoming
├── damaged
├── safety_stock
├── backorderable
├── lead_time_days and restock_eta
├── effective_at and observed_at
├── source_ref and source_event_id
└── freshness_status
```

Quantity names vary by provider. Normalizers retain the original name and map
only meanings that are documented. If a provider supplies `available` but not
`on_hand`, the agent stores `on_hand = null`; it does not reverse-engineer a
physical quantity.

### 8.2 Source precedence

The merchant configures precedence at the location/channel level. A common
starting policy is:

```text
WMS or ERP > commerce platform > marketplace copy > supplier feed > manual file
```

This is not universal. When two authoritative sources disagree, the agent emits
an `inventory_mismatch` finding containing both values, observation times and
sources. It never averages or silently chooses a number.

### 8.3 Ledger and event handling

- Store every accepted stock change as an append-only event.
- Deduplicate using provider event ID, or a stable content fingerprint when no
  ID exists.
- Partition processing by variant/location to preserve order.
- Track event time separately from ingestion time.
- Handle out-of-order events by rebuilding the affected current snapshot.
- Run periodic full reconciliation because webhooks and streams are not a
  complete historical ledger.
- Alert on feed lag, cursor stalls, negative available-to-sell and missing
  locations.

### 8.4 Inventory outputs

- Current stock by SKU, location and channel with freshness.
- Stockout and near-stockout findings based on explicit thresholds.
- Inventory mismatches across systems.
- Stale inventory feeds and missing updates.
- Incoming stock and restock dates when supplied by the source.
- Catalog-to-inventory orphan detection in both directions.

Demand forecasts, reorder quantities and autonomous stock writes are later,
separately permissioned capabilities.

## 9. Data contracts and provenance

Every provider payload is wrapped before transformation:

```json
{
  "envelope_version": "1.0",
  "source": "shopify",
  "connection_id": "conn_public_id",
  "resource": "inventory_level",
  "external_id": "gid://shopify/InventoryLevel/...",
  "operation": "upsert",
  "source_updated_at": "2026-07-10T01:00:00Z",
  "observed_at": "2026-07-10T01:00:03Z",
  "cursor": "opaque-provider-cursor",
  "checksum": "sha256:...",
  "payload": {}
}
```

Canonical fields store field-level lineage where sources can conflict:

```text
field: product.description
value: ...
source_ref: shopify/product/123
source_updated_at: ...
transform: html_to_text@1
confidence: 1.0
```

This makes reports reproducible and allows an agent to answer “where did this
fact come from?” without guessing.

## 10. Agent tools

Expose the same operations through MCP, A2A, HTTP and CLI:

| Tool | Purpose | Mutates merchant systems? |
|---|---|---|
| `sources_discover` | Find likely catalog, review and inventory channels | No |
| `sources_test` | Validate authorization and report capabilities | No |
| `sync_plan` | Dry-run resources, mappings and expected volume | No |
| `sync_run` | Pull authorized data into the agent store | No |
| `sync_status` | Show cursor, lag, errors and last successful run | No |
| `product_get` | Return product, variant and specifications with provenance | No |
| `listing_compare` | Compare channel listing content and status | No |
| `price_history` | Return source-attributed price observations | No |
| `feedback_summary` | Return observed metrics and source-linked themes | No |
| `inventory_status` | Return location/channel stock with freshness | No |
| `data_health_audit` | Run catalog, feedback and inventory checks | No |

Mutating tools such as `catalog_write_back` or `inventory_adjust` are excluded
from the first release. Later they must require a separate scope, explicit
human approval, an idempotency key and a before/after audit record.

## 11. Security, privacy and platform rules

- Store secret references, never access tokens, in connection configuration.
- Prefer OAuth and cloud workload identity over long-lived keys.
- Request minimum read scopes and isolate tenants at every storage boundary.
- Verify webhook signatures before parsing; record failed verification without
  persisting sensitive payloads.
- Hash or remove customer identifiers not needed for product analysis.
- Keep private support content separate from publicly reusable review evidence.
- Implement source deletion feeds and retention rules. For example, Trustpilot
  tells API consumers storing review data to mirror deletions at least every 28
  days.
- Use official and contractually permitted APIs. Do not make scraping the
  default fallback for unavailable review data.
- Log agent/tool access without logging secrets or full private payloads.

## 12. MVP and roadmap

### MVP: reputation-building release

Ship only the following:

1. Shopify read-only catalog and inventory sync using GraphQL plus recorded
   webhook fixtures.
2. WooCommerce read-only products, inventory fields and native product reviews.
3. Generic REST/OpenAPI connector with declarative pagination and field maps.
4. CSV/JSON object-storage connector for GCS, S3 and Azure Blob.
5. Canonical Product, Variant, Specification, Listing, Offer,
   PriceObservation, Feedback, Location and InventorySnapshot.
6. Exact identifier linking, conflict quarantine and field-level provenance.
7. Channel discovery from supplied storefront evidence.
8. Catalog completeness, feedback coverage, inventory freshness and mismatch
   reports, plus listing drift and price consistency checks.
9. Recorded fixtures and a no-network test suite.
10. The same read tools over CLI, MCP, A2A and REST.

This scope is large enough to demonstrate professional retail AI engineering
and small enough for an open-source maintainer to finish and explain.

### Next

- Amazon SP-API catalog, Customer Feedback insights and FBA inventory.
- Bazaarvoice and Trustpilot product-review connectors.
- BigQuery/Redshift/Synapse warehouse reads.
- Support and returns connectors with stricter PII controls.
- Approved topic extraction and multilingual feedback summaries.
- Operator-reviewed write-back proposals.

### Later, private/custom work

- Merchant-specific PIM/ERP/WMS/OMS adapters.
- Custom identity rules and taxonomy mappings.
- Demand forecasting and replenishment optimization.
- Autonomous write-back with merchant-specific approval policy.
- Enterprise data residency, private networking and customer-managed keys.

## 13. Acceptance criteria

The first release is complete when:

- the same fixture produces the same canonical entities through every adapter;
- every canonical fact is traceable to a source envelope;
- full sync and replay are idempotent;
- incremental cursors survive process restart;
- ambiguous product links are quarantined;
- inventory reports preserve variant, location and channel grain;
- specifications preserve original values, normalized values, units and scope;
- listings preserve channel, market, seller and publication status;
- prices preserve currency, type, validity window, segment and observation time;
- deleted reviews are removed or tombstoned according to source policy;
- agent summaries link back to structured evidence;
- the core test suite runs offline with no merchant credentials.

## 14. Official API references used for this design

- [Shopify Product GraphQL object](https://shopify.dev/docs/api/admin-graphql/latest/objects/product)
- [Shopify InventoryItem](https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryItem)
- [Shopify InventoryLevel](https://shopify.dev/docs/api/admin-graphql/latest/objects/inventorylevel)
- [Shopify webhook subscription](https://shopify.dev/docs/api/admin-graphql/latest/mutations/webhooksubscriptioncreate)
- [WooCommerce REST products](https://developer.woocommerce.com/docs/apis/rest-api/v1/products/)
- [WooCommerce Store API product reviews](https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/product-reviews)
- [Amazon Customer Feedback API](https://developer-docs.amazon.com/sp-api/lang-en_EN/docs/customer-feedback-api-v2024-06-01-use-case-guide)
- [Amazon FBA inventory summaries](https://developer-docs.amazon.com/sp-api/lang-US/docs/get-fba-inventory-summaries)
- [Google Merchant API product reviews](https://developers.google.com/merchant/api/guides/reviews/products)
- [Bazaarvoice review display](https://developers.bazaarvoice.com/v1.0-ConversationsAPI/docs/review-display)
- [Trustpilot Product Reviews API](https://developers.trustpilot.com/product-reviews-api)
- [Google Cloud Pub/Sub to BigQuery](https://docs.cloud.google.com/pubsub/docs/bigquery)
- [Amazon S3 events through EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventBridge.html)
- [Azure Blob Storage as an Event Grid source](https://learn.microsoft.com/en-us/azure/event-grid/event-schema-blob-storage)
