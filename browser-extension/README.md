# CatalogReady browser extension

One click on any product page: capture the rendered HTML, score it 0–100
for AI shopping readiness, and get findings, merchant questions, and
auto-drafted evidence-backed fixes — all against your locally running
CatalogReady server. Works in Chrome, Edge, Brave, and other Chromium
browsers (Manifest V3).

Because the extension reads the page your browser actually rendered, it
also works on bot-protected storefronts where a plain fetch gets blocked.

## Install

1. Start the local server:
   `uv run catalogready dashboard --no-open` (or `catalogready-local`).
2. Open `chrome://extensions` and enable **Developer mode**.
3. Select **Load unpacked** and choose this `browser-extension/` directory.
4. Open a product page and click **Score this product page**.

## What the popup shows

- Plain-language verdict, score dial, and six expandable pillars with the
  exact ✓/✗ checks behind each number.
- Findings with stable rule IDs (documented in `docs/RULES.md`).
- Merchant questions with inline answers — fill them in and re-run.
- Auto-drafted fix suggestions with an isolated preview validation and a
  copyable recommended Product JSON-LD block.
- An "ask the agent" box, answered deterministically from the audit result
  (or by a BYO model when a provider is selected in settings).
- **Two view modes, right under the score**: "Rendered · 78 | Crawler · 65"
  tabs switch the whole popup (dial, pillars, findings) between what a
  browsing agent sees and what non-rendering AI crawlers receive, with a
  one-line gap explanation (your page's JavaScript dependence). If the
  crawler fetch hits bot protection, it says so: crawlers may be blocked
  entirely.
- Downloads: self-contained HTML report, full JSON result.
- The popup follows your browser language (English / 中文) with a selector
  in the header; findings from the engine remain English.

## Support

Questions or fix help: open an issue at
[github.com/PO-VINCENT/ai-shopping-audit](https://github.com/PO-VINCENT/ai-shopping-audit/issues)
or email [vincentli802@hotmail.com](mailto:vincentli802@hotmail.com).
The popup's "ask the agent" box links here too.

## Privacy and safety

- Page HTML is sent **only** to the local server URL in settings
  (default `http://127.0.0.1:8080`) — never to a third party.
- Provider API keys stay in the local server environment. The extension
  never asks for or stores them; settings hold only the server URL,
  provider name, and model ID.
- The agent is read-only: it never writes to a storefront or feed.
