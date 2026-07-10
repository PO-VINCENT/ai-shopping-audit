# Architecture

CatalogReady uses a ports-and-adapters design. Domain modules do not import a
model SDK, web framework, MCP SDK, or A2A SDK.

```text
Browser UI / extension ─ REST ─┐
Claude Code ─┐                 │
Codex ───────┼─ MCP ───────────┤
Gemini CLI ──┘                 │
Gemini Enterprise ─ A2A ──────┤
Third parties ─ REST/OpenAPI ──┤
CLI ──────────────────────────┘
                               ↓
                    service.py application facade
                               ↓
              agent/ bounded orchestration
                               ↓
 catalog/ + discovery/ + visibility/ + optimization/ + reporting/
                               ↓
                   versioned JSON result contracts
```

## Package responsibilities

- `agent/`: bounded orchestration, tool policy, merchant questions, reversible change sets and preview validation.
- `catalog/`: feed schemas, apparel taxonomy, variant consistency and scoring.
- `discovery/`: HTML evidence, canonical, robots, sitemap and Product JSON-LD.
- `visibility/`: prompts, provider boundary, citations, competitors, snapshots and metrics.
- `optimization/`: product evidence, customer journey, generation, claim evaluation and readiness scoring.
- `model_providers/`: vendor-neutral OpenAI, Gemini, Claude and DeepSeek adapters.
- `reporting/`: presentation of the shared result contract.
- `service.py`: stable dispatch facade used by every external adapter.
- `frontend/` and `browser-extension/`: human review and active-page capture surfaces.
- `cli.py`, `mcp_server.py`, `api_server.py`, `local_server.py`: thin protocol adapters.

Adapters may validate transport concerns but must not implement retail rules.
Public changes must preserve or version `contracts/audit-result.schema.json`.

The complete file-by-file design is documented in `repository-design.md`.
The bounded v1 workflow is documented in `product-readiness-agent.md`. The
existing frontend and product-optimization data flow are documented in
`frontend-agent-architecture.md`.
