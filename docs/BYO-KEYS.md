# Bring your own model key

**You do not need any API key to use CatalogReady.** Scoring, findings,
fix drafts, and deterministic Q&A are fully offline. A key only unlocks
the optional model features: model-assisted planning, open-ended chat
answers, and generated listing copy.

## Where the key goes (and where it never goes)

The key lives in the **local server's environment** — nowhere else. It is
never entered into the dashboard, the browser extension, MCP tool
arguments, or HTTP request bodies; those surfaces only name a provider.
This is enforced by tests. The key travels only from your machine
directly to the provider over TLS.

## Setup (once)

1. Create a **restricted** key — for OpenAI, a project-scoped key with a
   monthly spend cap, not an org-wide key.
2. Put it in `.env` in the folder where you run CatalogReady
   (`.env` is git-ignored; copy `.env.example` to start):

   ```bash
   OPENAI_API_KEY=sk-proj-…
   OPENAI_MODEL=gpt-4o-mini      # optional default model
   ```

   Supported pairs: `OPENAI_API_KEY`/`OPENAI_MODEL`,
   `GEMINI_API_KEY`/`GEMINI_MODEL`, `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`,
   `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL`. Real environment variables always
   override `.env`.
3. **Restart the server** (`uv run catalogready dashboard`). The footer
   shows when a running server is older than the code or config around it.
4. Verify without exposing anything:

   ```bash
   uv run catalogready providers
   # → "openai": configured: true   (booleans only, never the key)
   ```

## Use it

- **CLI / chat**: `--provider openai` or `/provider openai`
- **Dashboard / extension**: pick the provider in settings; leave Model ID
  empty to use the `*_MODEL` default.

If you select a provider without a configured key, the error message
links back to this page — and everything deterministic keeps working.
