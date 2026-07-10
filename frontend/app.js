"use strict";

const STORAGE_KEY = "catalogready.frontend.settings.v1";
const MAX_WEIGHTS = {
  evidence_grounding: 30,
  journey_query_coverage: 20,
  decision_support: 20,
  feed_structured_data: 15,
  image_readiness: 10,
  clarity_compliance: 5,
};

const LABELS = {
  evidence_grounding: "Evidence grounding",
  journey_query_coverage: "Journey coverage",
  decision_support: "Decision support",
  feed_structured_data: "Feed + structured data",
  image_readiness: "Image readiness",
  clarity_compliance: "Clarity + compliance",
};

const DEMO_HTML = `<!doctype html>
<html lang="en-AU">
<head>
  <title>Commuter Shell | Northline</title>
  <link rel="canonical" href="https://demo.catalogready.ai/products/commuter-shell">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Commuter Shell",
    "description": "A lightweight recycled-nylon rain shell with sealed seams, an adjustable hood and two zip pockets.",
    "category": "Apparel > Outerwear > Rain Jackets",
    "brand": {"@type": "Brand", "name": "Northline"},
    "sku": "NLS-COMMUTER-OLV",
    "url": "https://demo.catalogready.ai/products/commuter-shell",
    "image": ["https://demo.catalogready.ai/images/commuter-shell-olive.jpg"],
    "color": "Olive",
    "material": "100% recycled nylon outer",
    "additionalProperty": [
      {"@type": "PropertyValue", "name": "Seams", "value": "Fully sealed"},
      {"@type": "PropertyValue", "name": "Pockets", "value": "Two zipped hand pockets"},
      {"@type": "PropertyValue", "name": "Care", "value": "Cold machine wash; line dry"}
    ],
    "offers": {
      "@type": "Offer",
      "price": "149.00",
      "priceCurrency": "AUD",
      "availability": "https://schema.org/InStock"
    },
    "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.6", "reviewCount": "87"}
  }
  <\/script>
</head>
<body><main><h1>Commuter Shell</h1></main></body>
</html>`;

const state = {
  source: "html",
  csvText: "",
  result: null,
};

const byId = (id) => document.getElementById(id);

function create(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function humanize(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function serverBase() {
  return byId("server-url").value.trim().replace(/\/+$/, "");
}

function settings() {
  return {
    serverUrl: serverBase(),
    provider: byId("provider").value,
    model: byId("model").value.trim(),
    market: byId("market").value.trim() || "en-AU",
  };
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    if (saved.serverUrl) byId("server-url").value = saved.serverUrl;
    if (saved.provider) byId("provider").value = saved.provider;
    if (saved.model) byId("model").value = saved.model;
    if (saved.market) byId("market").value = saved.market;
  } catch (_error) {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings()));
}

function setConnection(mode, label) {
  const pill = byId("connection-pill");
  pill.className = `connection-pill is-${mode}`;
  byId("connection-label").textContent = label;
}

async function checkHealth() {
  setConnection("checking", "Checking local agent");
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(`${serverBase()}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const body = await response.json();
    if (body.status !== "ok") throw new Error("Unexpected health response");
    setConnection("connected", "Local agent connected");
    return true;
  } catch (_error) {
    setConnection("disconnected", "Local agent offline");
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

function setStatus(message, isError = false) {
  const node = byId("run-status");
  node.textContent = message;
  node.classList.toggle("is-error", isError);
}

function selectSource(source) {
  state.source = source;
  document.querySelectorAll(".source-tab").forEach((tab) => {
    const active = tab.dataset.source === source;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  ["html", "csv", "shopify"].forEach((name) => {
    byId(`source-${name}`).hidden = name !== source;
  });
  setStatus("");
}

function selectedCustomers() {
  return Array.from(document.querySelectorAll('input[name="customer-type"]:checked')).map(
    (input) => input.value,
  );
}

function commonPayload() {
  const current = settings();
  return {
    provider: current.provider,
    model: current.model,
    market: current.market,
    target_customer_types: selectedCustomers(),
  };
}

function buildRequest() {
  const common = commonPayload();
  if (state.source === "html") {
    const url = byId("product-url").value.trim();
    const html = byId("product-html").value.trim();
    if (!url) throw new Error("Add the product URL.");
    if (!html) {
      throw new Error("Paste rendered product HTML, load the demo, or capture the page with the browser extension.");
    }
    return {path: "/v1/optimize/html", body: {...common, url, html}};
  }
  if (state.source === "csv") {
    if (!state.csvText) throw new Error("Choose a CSV file first.");
    return {
      path: "/v1/optimize/csv",
      body: {...common, csv_text: state.csvText, row_index: Number(byId("csv-row").value || 0)},
    };
  }
  const shopDomain = byId("shop-domain").value.trim();
  const productQuery = byId("shop-query").value.trim();
  if (!shopDomain || !productQuery) throw new Error("Add the Shopify domain and product query.");
  return {
    path: "/v1/optimize/shopify",
    body: {...common, shop_domain: shopDomain, product_query: productQuery},
  };
}

async function readResponse(response) {
  let body;
  try {
    body = await response.json();
  } catch (_error) {
    throw new Error(`The local agent returned HTTP ${response.status} without JSON.`);
  }
  if (!response.ok) throw new Error(body.detail || `Agent request failed with HTTP ${response.status}.`);
  return body;
}

async function runAgent() {
  const button = byId("run-agent");
  let request;
  try {
    request = buildRequest();
  } catch (error) {
    setStatus(error.message, true);
    return;
  }

  saveSettings();
  button.disabled = true;
  setStatus("Connecting to the local agent…");
  try {
    const available = await checkHealth();
    if (!available) {
      throw new Error("Cannot reach the local agent. Run: PYTHONPATH=src .venv/bin/python -m catalogready.local_server");
    }
    setStatus("Extracting evidence and mapping the buyer journey…");
    const response = await fetch(`${serverBase()}${request.path}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(request.body),
    });
    state.result = await readResponse(response);
    setStatus("Analysis complete.");
    renderResult(state.result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "The agent request failed.";
    setStatus(message, true);
  } finally {
    button.disabled = false;
  }
}

function renderHeader(result) {
  const record = result.evidence_record || {};
  const product = record.product || {};
  const source = record.source || {};
  const price = product.price || {};
  byId("result-source").textContent = `${humanize(source.kind || state.source)} analysis`;
  byId("result-product-title").textContent = product.title || "Untitled product";
  const meta = [product.brand, product.category, product.sku ? `SKU ${product.sku}` : ""];
  if (price.amount) meta.push(`${price.amount} ${price.currency || ""}`.trim());
  byId("result-product-meta").textContent = meta.filter(Boolean).join(" · ");

  const readiness = result.readiness || {};
  byId("readiness-score").textContent = Number.isFinite(readiness.score) ? readiness.score : "—";
  const status = byId("readiness-status");
  status.textContent = humanize(readiness.status || "Not scored");
  status.className = `status-badge ${String(readiness.status || "").replace(/_/g, "-")}`;
}

function renderMetrics(result) {
  const evaluation = result.evaluation || {};
  const counts = evaluation.counts || {};
  const claims = evaluation.claims || [];
  const supported = Number(counts.supported || 0);
  byId("supported-claims").textContent = supported;
  byId("claim-detail").textContent = `${supported} of ${claims.length} claims verified`;
  byId("question-count").textContent = (result.journey?.queries || []).length;
  byId("evidence-count").textContent = (result.evidence_record?.evidence || []).length;
  byId("approval-notice").textContent = result.approval?.notice || "No storefront or feed was modified.";
}

function renderComponents(result) {
  const container = byId("score-components");
  clear(container);
  const components = result.readiness?.components || {};
  Object.entries(MAX_WEIGHTS).forEach(([key, max]) => {
    const value = Number(components[key] || 0);
    const row = create("div", "component-row");
    row.appendChild(create("span", "", LABELS[key] || humanize(key)));
    const track = create("div", "component-track");
    const fill = create("span");
    fill.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(create("strong", "", value));
    container.appendChild(row);
  });
}

function renderCustomers(result) {
  const container = byId("customer-list");
  clear(container);
  const customers = result.journey?.customer_types || [];
  if (!customers.length) {
    container.appendChild(create("p", "result-meta", "No customer hypotheses generated."));
    return;
  }
  customers.forEach((customer) => {
    const item = create("div", "customer-item");
    item.appendChild(create("strong", "", customer.label || humanize(customer.id)));
    item.appendChild(create("small", "", customer.focus || "Merchant confirmation required"));
    container.appendChild(item);
  });
}

function renderJourney(result) {
  const container = byId("journey-timeline");
  clear(container);
  (result.journey?.stages || []).forEach((stage, index) => {
    const item = create("article", "journey-stage");
    item.appendChild(create("div", "journey-number", String(index + 1).padStart(2, "0")));
    const context = create("div");
    context.appendChild(create("h4", "", stage.name || humanize(stage.id)));
    context.appendChild(create("p", "", stage.intent || ""));
    item.appendChild(context);
    const questions = create("ol", "journey-questions");
    (stage.questions || []).forEach((question) => questions.appendChild(create("li", "", question)));
    item.appendChild(questions);
    container.appendChild(item);
  });
}

function appendList(id, values, fallback) {
  const container = byId(id);
  clear(container);
  const resolved = Array.isArray(values) && values.length ? values : [fallback];
  resolved.forEach((value) => container.appendChild(create("li", "", value)));
}

function renderListing(result) {
  const listing = result.draft?.listing || {};
  byId("draft-title").value = listing.title || "";
  byId("draft-description").value = listing.description || "";
  appendList("draft-bullets", listing.bullets, "No verified bullets generated.");
  appendList("draft-limitations", listing.limitations, "No limitations supplied.");
  const faq = byId("draft-faq");
  clear(faq);
  const items = listing.faq || [];
  if (!items.length) faq.appendChild(create("p", "result-meta", "No FAQ generated."));
  items.forEach((entry) => {
    const item = create("div", "faq-item");
    item.appendChild(create("strong", "", entry.question || "Question"));
    item.appendChild(create("span", "", entry.answer || ""));
    faq.appendChild(item);
  });
}

function statusClass(status) {
  return String(status || "requires_human_review").replace(/_/g, "-");
}

function renderEvidence(result) {
  const container = byId("claim-audit");
  clear(container);
  const claims = result.evaluation?.claims || [];
  if (!claims.length) container.appendChild(create("p", "result-meta", "No claims were available to audit."));
  claims.forEach((claim) => {
    const item = create("article", "audit-item");
    const head = create("div", "audit-item-head");
    head.appendChild(create("p", "", claim.text || "Untitled claim"));
    head.appendChild(create("span", `audit-status ${statusClass(claim.status)}`, humanize(claim.status)));
    item.appendChild(head);
    item.appendChild(create("p", "audit-reason", claim.reason || "No evaluator reason supplied."));
    const ids = (claim.evidence_ids || []).join(", ") || "No evidence IDs";
    item.appendChild(create("p", "audit-evidence", `Evidence: ${ids}`));
    container.appendChild(item);
  });

  const missing = byId("missing-information");
  clear(missing);
  const missingItems = result.draft?.missing_information || [];
  if (!missingItems.length) missing.appendChild(create("span", "tag", "No core gaps detected"));
  missingItems.forEach((value) => missing.appendChild(create("span", "tag", humanize(value))));

  const provider = result.provider || {};
  byId("provider-run").textContent = [
    `${provider.generator || "deterministic"} / ${provider.generator_model || "offline"}`,
    `evaluation: ${provider.evaluator || "deterministic"} / ${provider.evaluator_model || "offline"}`,
  ].join(" · ");
}

function renderResult(result) {
  renderHeader(result);
  renderMetrics(result);
  renderComponents(result);
  renderCustomers(result);
  renderJourney(result);
  renderListing(result);
  renderEvidence(result);
  byId("empty-state").hidden = true;
  byId("result-view").hidden = false;
  selectResultTab("overview");
  if (window.matchMedia("(max-width: 1050px)").matches) {
    byId("result-view").scrollIntoView({behavior: "smooth", block: "start"});
  }
}

function selectResultTab(name) {
  document.querySelectorAll(".result-tab").forEach((tab) => {
    const active = tab.dataset.resultTab === name;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  ["overview", "journey", "listing", "evidence"].forEach((panel) => {
    byId(`result-${panel}`).hidden = panel !== name;
  });
}

function listingText() {
  const listing = state.result?.draft?.listing || {};
  const bullets = (listing.bullets || []).map((item) => `• ${item}`).join("\n");
  const limits = (listing.limitations || []).map((item) => `• ${item}`).join("\n");
  const faq = (listing.faq || [])
    .map((item) => `Q: ${item.question || ""}\nA: ${item.answer || ""}`)
    .join("\n\n");
  return [listing.title, listing.description, bullets, "Known limitations", limits, "FAQ", faq]
    .filter(Boolean)
    .join("\n\n");
}

async function copyListing() {
  if (!state.result) return;
  try {
    await navigator.clipboard.writeText(listingText());
    byId("copy-listing").textContent = "Copied";
    window.setTimeout(() => { byId("copy-listing").textContent = "Copy listing"; }, 1600);
  } catch (_error) {
    setStatus("Clipboard access was blocked. Select the listing text manually.", true);
  }
}

function downloadReport() {
  if (!state.result) return;
  const product = state.result.evidence_record?.product || {};
  const slug = String(product.sku || product.title || "product")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  const blob = new Blob([JSON.stringify(state.result, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = create("a");
  link.href = url;
  link.download = `catalogready-${slug || "product"}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function bindEvents() {
  byId("settings-button").addEventListener("click", () => {
    const panel = byId("settings-panel");
    panel.hidden = !panel.hidden;
    byId("settings-button").setAttribute("aria-expanded", String(!panel.hidden));
  });
  ["server-url", "provider", "model", "market"].forEach((id) => {
    byId(id).addEventListener("change", () => {
      saveSettings();
      if (id === "server-url") checkHealth();
    });
  });
  document.querySelectorAll(".source-tab").forEach((tab) => {
    tab.addEventListener("click", () => selectSource(tab.dataset.source));
  });
  document.querySelectorAll(".result-tab").forEach((tab) => {
    tab.addEventListener("click", () => selectResultTab(tab.dataset.resultTab));
  });
  byId("load-demo").addEventListener("click", () => {
    byId("product-url").value = "https://demo.catalogready.ai/products/commuter-shell";
    byId("product-html").value = DEMO_HTML;
    setStatus("Demo product loaded. Run the agent to analyse it.");
  });
  byId("csv-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      state.csvText = await file.text();
      byId("csv-file-label").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
      setStatus("CSV ready.");
    } catch (_error) {
      state.csvText = "";
      setStatus("Could not read that CSV file.", true);
    }
  });
  byId("run-agent").addEventListener("click", runAgent);
  byId("copy-listing").addEventListener("click", copyListing);
  byId("download-report").addEventListener("click", downloadReport);
}

function init() {
  loadSettings();
  bindEvents();
  selectSource("html");
  checkHealth();
}

document.addEventListener("DOMContentLoaded", init);
