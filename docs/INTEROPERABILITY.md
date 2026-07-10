# Agent interoperability

CatalogReady exposes one evidence-grounded application service through several
protocol adapters. The deterministic path remains available offline, while an
operator can explicitly select a BYO model for listing generation and a second
claim-evaluation pass.

## Compatibility matrix

| Consumer | Primary integration | Repository configuration | Notes |
|---|---|---|---|
| OpenAI Codex | MCP over stdio | `AGENTS.md` plus `integrations/codex/config.toml.example` | Copy the MCP block into a trusted Codex config. |
| Claude Code | MCP over stdio | `.mcp.json` and `CLAUDE.md` | Claude prompts before accepting project-scoped MCP servers. |
| Gemini CLI | MCP over stdio | `.gemini/settings.json` and `GEMINI.md` | `trust` remains false so tool calls retain confirmation. |
| Gemini Enterprise | A2A 0.3 JSON-RPC | Hosted agent card and `/a2a` endpoint | Host the service on HTTPS and register its agent card. |
| Other agent platforms | MCP, A2A, or HTTP/OpenAPI | Client-specific | Prefer MCP for tools, A2A for peer-agent delegation, and REST as fallback. |
| Chrome/Edge/Brave | Local HTTP API | `browser-extension/` | Reads the active product page and never stores provider keys. |

## Why there are three interfaces

- **MCP** is the tool boundary. A host model discovers focused tools and decides
  when to invoke them.
- **A2A** is the peer-agent boundary. An enterprise orchestrator discovers an
  agent card and delegates a task to a separately hosted agent.
- **HTTP/OpenAPI** is the universal boundary for platforms that implement
  neither protocol.

The protocol files contain no retail scoring logic. All adapters call
`catalogready.service`, and all public audit responses follow
`contracts/audit-result.schema.json`.

Product agent runs follow `contracts/product-agent-run.schema.json`. The
reference service is stateless: to resume a paused agent run, send the original
supplied HTML again with verified `merchant_answers` and the earlier run ID in
`resumed_from`. No adapter accepts provider API keys.

## Codex

Codex reads the repository-level `AGENTS.md`. Copy the MCP server block from
`integrations/codex/config.toml.example` into a trusted project's
`.codex/config.toml` or into the user-level Codex config:

```bash
uv sync
codex
```

Then ask Codex to list the CatalogReady tools or audit
`examples/messy-apparel.csv`.

The optimization tools accept `provider` and `model` but never an API key.
Credentials are inherited by the MCP server through its environment.

## Claude Code

`CLAUDE.md` imports the shared `AGENTS.md`, while `.mcp.json` declares the same
stdio server:

```bash
uv sync
claude
```

Review and approve the project-scoped MCP server when Claude Code prompts.

## Gemini CLI

The project `.gemini/settings.json` declares the stdio server:

```bash
uv sync
gemini
```

Use `/mcp list` to confirm that `catalogready` is connected.

## Gemini Enterprise through A2A

Run locally:

```bash
uv sync
uv run catalogready-api
```

For deployment, set `CATALOGREADY_PUBLIC_URL` to the public HTTPS origin. The
service publishes its card at `/.well-known/agent-card.json` and receives
JSON-RPC `message/send` requests at `/a2a`.

The reference card advertises A2A protocol version `0.3` with non-streaming
capabilities because Gemini Enterprise currently documents its v0.3
compatibility path. Before production, add OAuth or workload identity, request
validation, rate limiting, audit logs, tenant isolation, and an official A2A SDK
compatibility test.

An A2A caller selects an operation with request metadata:

```json
{
  "jsonrpc": "2.0",
  "id": "audit-1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "messageId": "message-1",
      "parts": [{ "kind": "text", "text": "Build a visibility prompt pack" }]
    },
    "metadata": {
      "operation": "build_visibility_prompt_pack",
      "arguments": {
        "domain": "example.com",
        "category": "commuter shoes",
        "market": "en-AU"
      }
    }
  }
}
```

## Generic HTTP clients

Call `POST /v1/execute`:

```json
{
  "operation": "build_visibility_prompt_pack",
  "arguments": {
    "domain": "example.com",
    "category": "commuter shoes"
  }
}
```

FastAPI serves the generated OpenAPI document at `/openapi.json` and an
interactive explorer at `/docs`.

Product optimization has focused endpoints:

- `POST /v1/agent/html`
- `POST /v1/optimize/html`
- `POST /v1/optimize/csv`
- `POST /v1/optimize/evidence`
- `POST /v1/optimize/shopify-payload`
- `POST /v1/optimize/shopify`
- `GET /v1/providers`

Example:

```json
{
  "url": "https://example.com/products/cr-001",
  "html": "<html>...</html>",
  "provider": "openai",
  "model": "",
  "market": "en-AU"
}
```

Bounded product-agent example:

```json
{
  "url": "https://example.com/products/cr-001",
  "html": "<html>...</html>",
  "mode": "draft",
  "provider": "deterministic",
  "merchant_answers": {
    "category": "Apparel > Footwear"
  },
  "resumed_from": "optional-prior-run-id"
}
```

The MCP tool exposing the same contract is
`catalogready_run_product_agent`. Model-assisted planning is optional and may
only reorder allowlisted deterministic findings. Draft validation uses an
isolated preview and does not mutate merchant HTML or Shopify data.

When `model` is empty, the server uses the matching provider model environment
variable. `deterministic` is the default provider and performs no external call.

## Security boundary

- The checked-in configuration contains no credentials.
- The reference core performs no live crawling. Model-provider calls occur only
  when the caller explicitly selects a live provider.
- The CLI `audit` command performs exactly one HTTP GET for the page the user
  names, and only when no saved HTML file is supplied. This fetch lives in the
  CLI adapter; the service layer and every other adapter accept supplied HTML
  only, and the test suite runs without network access.
- Provider API keys are read only from server-side environment variables.
- The browser extension never accepts or stores provider keys.
- A host agent must obtain authorization before fetching private merchant data.
- Keep write operations out of the default tool set; add them as separate,
  approval-gated tools later.
- Treat tool descriptions and third-party agent metadata as untrusted input.
- Generated listings always require merchant review and are not written back.
