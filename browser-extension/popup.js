"use strict";

/* CatalogReady extension popup. Captures the active tab's rendered HTML and
   sends it to the LOCAL CatalogReady server only. No provider keys are ever
   requested or stored; settings hold server URL, provider name, model ID. */

const $ = (id) => document.getElementById(id);
const state = { page: null, result: null, draft: null, answers: {} };

const PILLAR_LABELS = {
  product_identity: "Product identity",
  offer_completeness: "Offer completeness",
  structured_data: "Structured data",
  decision_evidence: "Decision evidence",
  media_variants: "Media & variants",
  claim_grounding: "Claim grounding",
};

const CHECK_LABELS = {
  stable_identifier: "stable identifier (SKU / GTIN / MPN)",
  complete_offer_markup: "complete Offer markup",
  product_node: "Product JSON-LD present",
  valid_json_ld: "JSON-LD parses",
  substantive_page: "120+ words visible",
  evidence_topics: "3+ evidence topics",
  review_evidence: "rating + review count",
  variant_attribute: "variant attribute",
  variant_identity: "variant identifier",
  no_high_risk_claims: "no high-risk claims",
  no_unsupported_claims: "no unsupported claims",
};

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value == null ? "" : value);
  return div.innerHTML;
}

function scoreColor(ratio) {
  return ratio >= 0.8 ? "var(--good)" : ratio >= 0.5 ? "var(--warn)" : "var(--bad)";
}

function setStatus(message, isError = false) {
  $("status").textContent = message || "";
  $("status").classList.toggle("error", isError);
}

function serverBase() {
  return $("server").value.trim().replace(/\/$/, "");
}

async function api(path, body) {
  const response = await fetch(`${serverBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `Server returned ${response.status}`);
  return payload;
}

/* ---------- settings ---------- */

async function loadSettings() {
  try {
    const settings = await chrome.storage.local.get(["server", "provider", "model"]);
    if (settings.server) $("server").value = settings.server;
    if (settings.provider) $("provider").value = settings.provider;
    if (settings.model) $("model").value = settings.model;
  } catch (error) {
    /* not running as an extension (layout preview) */
  }
}

async function saveSettings() {
  try {
    await chrome.storage.local.set({
      server: serverBase(),
      provider: $("provider").value,
      model: $("model").value.trim(),
    });
  } catch (error) {
    /* not running as an extension */
  }
}

/* ---------- page capture ---------- */

async function currentPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id || !/^https?:/.test(tab.url || "")) {
    throw new Error("Open a public product page, then click the extension.");
  }
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => ({ url: window.location.href, html: document.documentElement.outerHTML }),
  });
  if (!results[0]?.result?.html) throw new Error("The page HTML could not be read.");
  return results[0].result;
}

/* ---------- agent runs ---------- */

async function runAgent(mode) {
  const body = {
    url: state.page.url,
    html: state.page.html,
    mode,
    provider: $("provider").value,
    model: $("model").value.trim(),
  };
  if (Object.keys(state.answers).length) body.merchant_answers = state.answers;
  return api("/v1/agent/html", body);
}

async function analyze() {
  const button = $("analyze");
  button.disabled = true;
  $("result").hidden = true;
  try {
    await saveSettings();
    try {
      const health = await fetch(`${serverBase()}/health`);
      if (!health.ok) throw new Error();
    } catch (error) {
      throw new Error(
        `Cannot reach ${serverBase()}. Start it with: uv run catalogready dashboard --no-open`
      );
    }
    setStatus("Reading this page…");
    state.page = await currentPage();
    state.answers = {};
    setStatus("Auditing locally…");
    state.result = await runAgent("audit");
    state.draft = null;
    render();
    setStatus("");
    autoDraft();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function resume() {
  document.querySelectorAll("#questions input").forEach((input) => {
    const value = input.value.trim();
    if (value) state.answers[input.dataset.field] = value;
  });
  const button = $("resume");
  button.disabled = true;
  setStatus("Re-running with your answers…");
  try {
    state.result = await runAgent("audit");
    state.draft = null;
    render();
    setStatus("");
    autoDraft();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function autoDraft() {
  try {
    state.draft = await runAgent("draft");
    renderFixes();
    renderSummary();
  } catch (error) {
    /* fix suggestions are best-effort */
  }
}

/* ---------- rendering ---------- */

function renderDial(score) {
  const circumference = 2 * Math.PI * 56;
  const filled = (circumference * Math.max(0, Math.min(score, 100))) / 100;
  $("dial").innerHTML =
    `<circle cx="66" cy="66" r="56" fill="none" stroke="var(--chip)" stroke-width="11"/>` +
    `<circle cx="66" cy="66" r="56" fill="none" stroke="${scoreColor(score / 100)}" stroke-width="11"` +
    ` stroke-linecap="round" stroke-dasharray="${filled.toFixed(1)} ${circumference.toFixed(1)}"` +
    ` transform="rotate(-90 66 66)"/>` +
    `<text x="66" y="64" text-anchor="middle" font-size="36" font-weight="700">${score}</text>` +
    `<text x="66" y="88" text-anchor="middle" font-size="13" opacity="0.7">/ 100</text>`;
}

function renderPillars(components) {
  $("pillars").innerHTML = Object.entries(components)
    .map(([key, section]) => {
      const max = section.max_score || 1;
      const ratio = section.score / max;
      const checks = Object.entries(section.checks || {})
        .map(
          ([check, passed]) =>
            `<li class="${passed ? "pass" : "fail"}"><span>${passed ? "✓" : "✗"}</span> ` +
            `${escapeHtml(CHECK_LABELS[check] || check.replace(/_/g, " "))}</li>`
        )
        .join("");
      return (
        `<div><button class="pillar" type="button">` +
        `<span>${escapeHtml(PILLAR_LABELS[key] || key)}</span>` +
        `<span class="bar"><i style="width:${Math.round(ratio * 100)}%;background:${scoreColor(ratio)}"></i></span>` +
        `<span>${section.score}/${max}</span></button>` +
        `<div class="pillar-detail" hidden><ul>${checks}</ul></div></div>`
      );
    })
    .join("");
}

function renderSummary() {
  const readiness = (state.result.readiness || {}).before || {};
  const score = readiness.score || 0;
  const findings = state.result.findings || [];
  const high = findings.filter((f) => f.severity === "high").length;
  const blocking = (state.result.merchant_questions || []).filter((q) => q.blocking).length;
  let verdict;
  if (score >= 80 && !(readiness.cap_reasons || []).length) {
    verdict = "Ready for AI shopping agents.";
  } else if (score >= 50) {
    verdict = "Partially readable by AI shopping agents.";
  } else {
    verdict = "Largely invisible or untrustworthy to AI shopping agents.";
  }
  const points = [];
  if ((readiness.cap_reasons || []).length) {
    points.push(`Capped at ${readiness.safety_cap}: ${readiness.cap_reasons.join(" ")}`);
  }
  if (high) points.push(`${high} critical finding${high > 1 ? "s" : ""}.`);
  if (blocking) points.push(`${blocking} blocking merchant question${blocking > 1 ? "s" : ""}.`);
  const validation = (state.draft || {}).validation || {};
  if ((state.draft?.proposed_changes || []).length && validation.after_score != null) {
    points.push(
      `<span class="autofix">${state.draft.proposed_changes.length} auto-drafted fix(es): ` +
      `${validation.before_score} → ${validation.after_score} validated.</span>`
    );
  }
  $("summary").innerHTML =
    `<div class="verdict">${escapeHtml(verdict)} (${score}/100)</div>` +
    (points.length
      ? `<ul>${points.map((p) => `<li>${p.startsWith("<span") ? p : escapeHtml(p)}</li>`).join("")}</ul>`
      : "");
}

function renderFindings() {
  const findings = state.result.findings || [];
  const order = { high: 0, medium: 1, low: 2 };
  const sorted = [...findings].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
  $("findings").innerHTML = sorted.length
    ? sorted
        .map(
          (item) =>
            `<div class="finding"><h4><span class="sev ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span> ` +
            `${escapeHtml(item.title)}<span class="chip">${escapeHtml(item.rule_id)}</span></h4>` +
            `<p>${escapeHtml(item.evidence)}</p><p class="fix">→ ${escapeHtml(item.recommendation)}</p></div>`
        )
        .join("")
    : "<p class='note'>No findings. Everything checked is machine-readable.</p>";
  $("findings-count").textContent = String(sorted.length);
}

function renderQuestions() {
  const questions = state.result.merchant_questions || [];
  $("questions").innerHTML = questions
    .map(
      (item) =>
        `<div class="question"><div>` +
        (item.blocking ? `<span class="blocking-tag">blocking</span>` : "") +
        `${escapeHtml(item.question)}</div>` +
        `<div class="why">${escapeHtml(item.reason)}</div>` +
        `<input data-field="${escapeHtml(item.field)}" type="text"` +
        ` placeholder="Verified ${escapeHtml(item.field)}" value="${escapeHtml(state.answers[item.field] || "")}"></div>`
    )
    .join("");
  $("resume").hidden = !questions.length;
  $("questions-count").textContent = String(questions.length);
  $("questions-block").open = questions.some((item) => item.blocking);
}

function renderFixes() {
  const source = state.draft || state.result;
  const changes = source.proposed_changes || [];
  $("changes").innerHTML = changes.length
    ? changes
        .map((item) => `<div class="change"><strong>${escapeHtml(item.id)}</strong> · ${escapeHtml(item.operation)}</div>`)
        .join("")
    : "<p class='note'>Fix suggestions are drafted automatically after the audit.</p>";
  const validation = source.validation || {};
  $("validation").innerHTML =
    changes.length && validation.after_score != null
      ? `<div class="delta">Validated preview: ${validation.before_score} → ${validation.after_score}. ` +
        `Nothing was written to your store.</div>`
      : "";
  const jsonldChange = changes.find((item) => item.operation === "replace_product_jsonld");
  $("jsonld-wrap").hidden = !jsonldChange;
  if (jsonldChange) $("jsonld").textContent = JSON.stringify(jsonldChange.value, null, 2);
  if (changes.length) $("fixes-block").open = true;
}

function render() {
  $("result").hidden = false;
  const readiness = (state.result.readiness || {}).before || {};
  const product = (state.result.evidence_record || {}).product || {};
  $("product-title").textContent = product.title || state.page.url;
  renderDial(readiness.score || 0);
  renderPillars(readiness.components || {});
  $("caps").innerHTML = (readiness.cap_reasons || []).length
    ? `<div class="cap"><strong>Score capped at ${readiness.safety_cap}.</strong> ` +
      readiness.cap_reasons.map(escapeHtml).join(" ") + `</div>`
    : "";
  renderSummary();
  renderFindings();
  renderQuestions();
  renderFixes();
  $("ask-log").replaceChildren();
}

/* ---------- ask the agent ---------- */

function appendAsk(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("ask-log").appendChild(div);
}

async function ask() {
  const input = $("ask-input");
  const question = input.value.trim();
  if (!question || !state.result) return;
  input.value = "";
  appendAsk("user", question);
  $("ask-send").disabled = true;
  try {
    const reply = await api("/v1/agent/ask", {
      audit_result: state.draft || state.result,
      question,
      provider: $("provider").value,
      model: $("model").value.trim(),
    });
    appendAsk("agent", reply.answer);
  } catch (error) {
    appendAsk("agent", `Error: ${error.message}`);
  } finally {
    $("ask-send").disabled = false;
    input.focus();
  }
}

/* ---------- downloads ---------- */

function download(filename, text, type) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([text], { type }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

/* ---------- wiring ---------- */

document.addEventListener("DOMContentLoaded", loadSettings);
$("settings-toggle").addEventListener("click", () => {
  $("settings").hidden = !$("settings").hidden;
});
$("analyze").addEventListener("click", analyze);
$("resume").addEventListener("click", resume);
$("ask-send").addEventListener("click", ask);
$("ask-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") ask();
});
$("pillars").addEventListener("click", (event) => {
  const button = event.target.closest(".pillar");
  if (!button) return;
  const detail = button.parentElement.querySelector(".pillar-detail");
  detail.hidden = !detail.hidden;
});
$("copy-jsonld").addEventListener("click", (event) => {
  navigator.clipboard.writeText($("jsonld").textContent).then(() => {
    event.target.textContent = "Copied";
    setTimeout(() => (event.target.textContent = "Copy"), 1200);
  });
});
$("copy-json").addEventListener("click", async () => {
  if (!state.result) return;
  await navigator.clipboard.writeText(JSON.stringify(state.draft || state.result, null, 2));
  setStatus("Full JSON result copied.");
});
$("download-report").addEventListener("click", async () => {
  if (!state.result) return;
  try {
    const payload = await api("/v1/report/html", { audit_result: state.result });
    download("catalogready-report.html", payload.html, "text/html");
  } catch (error) {
    setStatus(error.message, true);
  }
});
