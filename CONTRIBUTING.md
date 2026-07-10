# Contributing to CatalogReady

Thanks for helping merchants become readable to AI shopping agents.

## Ground rules

- The core stays **deterministic and offline**: no network calls, no model
  calls, and no API keys in the default test path.
- Audit rules live in `catalog/`, `discovery/`, `visibility/`, and
  `optimization/`. Protocol adapters (CLI, MCP, HTTP, A2A) stay thin.
- Never invent product attributes, citations, or rankings. Findings must
  quote observable evidence.
- Never commit API keys, tokens, or merchant customer data.

## Development setup

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run catalogready audit https://example.com/products/cr-001 examples/demo-store/index.html
```

Python 3.11+ is required. The test suite must pass offline.

## Proposing a new audit rule

Rules are the heart of the project. Read [docs/RULES.md](docs/RULES.md)
first — it documents every implemented rule with its platform source and
lists sourced candidate rules waiting for an implementation. A good rule
proposal includes:

1. A rule ID following the existing pattern (`CAT-`, `SEO-`, `GEO-`, `CLAIM-`, `AGENT-`).
2. The observable evidence it checks (never an inference).
3. Severity (`high` blocks trust, `medium` degrades it, `low` is polish).
4. A recommendation a merchant can act on.
5. A deterministic test with a minimal HTML or CSV fixture.

Open an issue with the **rule proposal** template before writing large PRs.

## Scoring changes

The public score must survive scrutiny. Any change to weights, caps, or
pillars needs an update to `docs/scoring-methodology.md` in the same PR,
plus updated expectations in the test suite.

## Pull requests

- Run `python -m unittest discover -s tests` before pushing.
- Update the JSON contracts in `contracts/` when a public result shape changes.
- Document compatibility limitations in `docs/INTEROPERABILITY.md`.
- Keep commits focused; one behavior change per PR is ideal.
