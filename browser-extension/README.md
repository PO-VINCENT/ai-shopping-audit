# CatalogReady browser extension

This Manifest V3 extension works in Chrome, Edge, Brave, and other Chromium
browsers. It sends the active page URL and rendered HTML to a locally running
CatalogReady API. The bounded agent inspects evidence, prioritizes findings,
drafts reversible structured-data changes, and validates them in an isolated
preview. It never stores model-provider API keys.

## Install

1. Start the local API with
   `PYTHONPATH=src .venv/bin/python -m catalogready.local_server`. The full
   FastAPI server (`uv run catalogready-api`) is also compatible.
2. Open `chrome://extensions`.
3. Enable **Developer mode**.
4. Select **Load unpacked** and choose this `browser-extension/` directory.
5. Open a public product page and click the CatalogReady extension.

For a live model, set the provider key and model environment variables before
starting the server. The extension stores only the local server URL, provider
name, model ID, and agent mode in browser-local storage.

The extension does not publish changes. It returns a product-readiness score,
priority plan, merchant questions, proposed changes, and validation result.
