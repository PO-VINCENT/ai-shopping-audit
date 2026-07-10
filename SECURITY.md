# Security policy

## Supported versions

The latest minor release receives security fixes.

## Reporting a vulnerability

Please report vulnerabilities privately via GitHub Security Advisories
("Report a vulnerability" on the repository's Security tab). Do not open
public issues for exploitable problems. You should receive a response
within 7 days.

## Design guarantees we treat as security boundaries

- Provider API keys are read only from server-side environment variables.
  They are never accepted in MCP tool arguments, HTTP request bodies, A2A
  payloads, or browser extension storage. A report that shows a key
  crossing one of these boundaries is a valid vulnerability.
- The deterministic core makes no network calls. The CLI `audit` command
  performs exactly one HTTP GET for the page the user names.
- CatalogReady never writes to a storefront, feed, or merchant system.
- Raw page HTML and merchant answers are processed in memory and are not
  persisted by the core.
