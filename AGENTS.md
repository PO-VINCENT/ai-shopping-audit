# Repository guidance

## Architecture

- Keep retail audit rules inside `catalog/`, `discovery/`, `visibility/`, and
  `optimization/`.
- Keep provider HTTP details inside `model_providers/`; provider adapters must
  return the same JSON contract.
- Keep `service.py` as a stable vendor-neutral application facade.
- Treat CLI, MCP, HTTP, and A2A as thin adapters over the same service functions.
- Return structured evidence; never invent product attributes, citations, or rankings.
- Keep catalog readiness, discovery readiness, and observed AI visibility separate.

## Development

- Use Python 3.11 or newer.
- Run `python3 -m unittest discover -s tests -v` after changing core behavior.
- Run `uv run catalogready catalog examples/messy-apparel.csv` after changing an adapter.
- Do not add provider-specific business logic to protocol adapters.
- Never commit API keys, OAuth secrets, access tokens, or merchant customer data.
- Never accept provider API keys in MCP, A2A, HTTP request bodies, or browser
  extension storage; use server environment variables.

## Completion

- Update the JSON contracts when a public result shape changes.
- Document any compatibility limitation in `docs/INTEROPERABILITY.md`.
- Preserve the no-network, deterministic core test path.
