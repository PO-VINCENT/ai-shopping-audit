# CatalogReady AI frontend

A dependency-free interface for the earlier product visibility optimisation
workflow. It accepts rendered product HTML, a CSV row, or a live Shopify
product, then displays the buyer journey, listing, claim audit, and readiness
score. The browser extension is the focused v0.4 Product Readiness Agent client.

## Run locally

From the repository root, start the local agent API:

```bash
PYTHONPATH=src .venv/bin/python -m catalogready.local_server
```

In a second terminal, serve the frontend on a different port:

```bash
python3 -m http.server 9001 --directory frontend
```

Open `http://127.0.0.1:9001` and choose **Load evidence-rich demo product** for an offline deterministic run.

Do not open `index.html` directly as a `file://` URL. Serving it over localhost gives the browser a valid CORS origin for the local API.

## BYO model providers

Choose OpenAI, Gemini, Claude, or DeepSeek in **Settings**. Configure the matching API key in the local server process environment; never paste keys into this page and never commit them to the repository. The interface stores only the local server URL, provider name, model ID, and market in browser local storage.

See the repository setup documentation for the provider-specific environment variable names. The deterministic provider works without a key or network request.

## Product page capture

Browsers generally block a local page from fetching arbitrary storefront HTML. Paste rendered HTML into the product-page input or use the included browser extension to capture the current product page and send it to the localhost agent.
