# Quick start with ChatGPT, Claude, Gemini, Copilot, and DeepSeek

CatalogReady meets each AI assistant in two ways:

1. **As a tool the assistant can call** (MCP) — your coding agent audits
   product pages itself: *"fetch this page and run the CatalogReady agent
   on its HTML."*
2. **As the model inside CatalogReady** (BYO key) — the audit stays
   deterministic; the model powers planning, open-ended chat answers, and
   evidence-grounded listing drafts. See [BYO-KEYS.md](BYO-KEYS.md).

The audit itself needs **no key and no account** either way.

Command note: once the package is on PyPI, `uvx --from catalogready-ai
catalogready-mcp` works from anywhere with no checkout. From a git clone,
use `uv run catalogready-mcp` with the repo as working directory — the
snippets below show the clone form; swap in the `uvx` form after release.

---

## ChatGPT / Codex (OpenAI)

**As a tool — Codex CLI (MCP).** Add to `~/.codex/config.toml` (or a
trusted project's `.codex/config.toml`; this repo ships the same block in
`integrations/codex/config.toml.example`):

```toml
[mcp_servers.catalogready]
command = "uv"
args = ["run", "catalogready-mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 120
```

Then ask Codex: *"Fetch https://store.example/products/x and run
catalogready_run_product_agent on the HTML. Summarize the score and the
top fixes."*

ChatGPT's web/desktop connectors expect remote MCP servers; for a local
audit tool, Codex CLI is the supported path today.

**As the model inside CatalogReady:**

```bash
# .env next to where you run the server
OPENAI_API_KEY=sk-proj-…
OPENAI_MODEL=gpt-4o-mini
```

Then pick **OpenAI** in the dashboard/extension, or `--provider openai`
on the CLI, `/provider openai` in `catalogready chat`.

---

## Claude (Anthropic)

**As a tool — Claude Code (one line):**

```bash
claude mcp add catalogready -- uv run catalogready-mcp
```

(Working inside this repo, the checked-in `.mcp.json` registers the
server automatically — Claude Code will prompt to trust it.)

**Claude Desktop** — add to `claude_desktop_config.json` → `mcpServers`:

```json
{
  "mcpServers": {
    "catalogready": {
      "command": "uv",
      "args": ["run", "catalogready-mcp"],
      "cwd": "/path/to/ai-shopping-audit"
    }
  }
}
```

Then: *"Use the catalogready tools to audit the product page HTML I
paste next, and explain the score caps."*

**As the model inside CatalogReady:** `ANTHROPIC_API_KEY=…` and
`ANTHROPIC_MODEL=…` in `.env`, then provider **Claude** / `--provider
anthropic`.

---

## Gemini (Google)

**As a tool — Gemini CLI.** This repo ships `.gemini/settings.json`; for
your own projects add:

```json
{
  "mcpServers": {
    "catalogready": {
      "command": "uv",
      "args": ["run", "catalogready-mcp"],
      "cwd": "/path/to/ai-shopping-audit",
      "trust": false
    }
  }
}
```

Gemini Enterprise can instead use the **A2A** surface: run
`uv run catalogready-api` and register
`http://<host>:8080/.well-known/agent-card.json`
(see [INTEROPERABILITY.md](INTEROPERABILITY.md)).

**As the model inside CatalogReady:** `GEMINI_API_KEY=…` and
`GEMINI_MODEL=…`, then provider **Gemini**.

---

## Copilot (Microsoft / GitHub)

**As a tool — VS Code Copilot agent mode.** Create `.vscode/mcp.json` in
your workspace:

```json
{
  "servers": {
    "catalogready": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "catalogready-mcp"],
      "cwd": "/path/to/ai-shopping-audit"
    }
  }
}
```

Enable the server when Copilot Chat (agent mode) prompts, then ask
Copilot to audit a page's HTML with the CatalogReady tools.

There is no BYO-key slot for Copilot inside CatalogReady — Microsoft
doesn't expose Copilot as a key-based API. What CatalogReady *does* do
for Copilot is audit your pages against Bing's documented Copilot
grounding rules (`noarchive`/`nocache` effects, prompt-injection abuse
policy — see [RULES.md](RULES.md)).

---

## DeepSeek

DeepSeek has no MCP client today, so the integration runs the other way:
**as the model inside CatalogReady**.

```bash
DEEPSEEK_API_KEY=…
DEEPSEEK_MODEL=deepseek-chat
```

Then provider **DeepSeek** / `--provider deepseek`. Note for site owners:
DeepSeek publishes no crawler documentation, so there are no
DeepSeek-specific audit rules to pass — see the verified-absence note in
[RULES.md](RULES.md).

---

## What the assistant gets (MCP tool set)

`catalogready-mcp` exposes the same operations as every other surface:
`catalogready_run_product_agent` (score + findings + questions + drafted
fixes from URL + HTML), `catalogready_audit_page_html`,
`catalogready_audit_catalog` (CSV), `catalogready_audit_discovery_bundle`
(robots/sitemap), and more — run `catalogready_describe` to list them.
Provider keys are **never** accepted through tool arguments; they come
from the server's environment only.
