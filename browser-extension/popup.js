"use strict";

/* CatalogReady extension popup. Captures the active tab's rendered HTML and
   sends it to the LOCAL CatalogReady server only. No provider keys are ever
   requested or stored; settings hold server URL, provider name, model ID. */

const $ = (id) => document.getElementById(id);
const state = { page: null, result: null, draft: null, answers: {} };

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

function friendlyError(message) {
  if (/missing api key|model id is required/i.test(message)) {
    return `${message} — ${i18n.t("keyHint")}`;
  }
  return message;
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
    throw new Error(i18n.t("errNoPage"));
  }
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => ({ url: window.location.href, html: document.documentElement.outerHTML }),
  });
  if (!results[0]?.result?.html) throw new Error(i18n.t("errNoHtml"));
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
      throw new Error(i18n.t("errServer", serverBase()));
    }
    setStatus(i18n.t("statusReading"));
    state.page = await currentPage();
    state.answers = {};
    setStatus(i18n.t("statusAuditing"));
    state.result = await runAgent("audit");
    state.draft = null;
    render();
    setStatus("");
    autoDraft();
    autoOnlineChecks();
  } catch (error) {
    setStatus(friendlyError(error.message), true);
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
  setStatus(i18n.t("statusRerunning"));
  try {
    state.result = await runAgent("audit");
    state.draft = null;
    render();
    setStatus("");
    autoDraft();
    autoOnlineChecks();
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

async function autoOnlineChecks() {
  // Bounded image-size checks via the local server (max 3 fetches).
  // Informational: findings are appended, the score never changes.
  try {
    const images = state.result?.evidence_record?.product?.images || [];
    if (!images.length) return;
    const payload = await api("/v1/online-checks", {
      url: state.page.url,
      images,
    });
    if (payload.findings?.length) {
      state.result.findings.push(...payload.findings);
      renderFindings();
      renderSummary();
    }
  } catch (error) {
    /* online checks are best-effort */
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
            `${escapeHtml(i18n.checkLabel(check))}</li>`
        )
        .join("");
      return (
        `<div><button class="pillar" type="button">` +
        `<span>${escapeHtml(i18n.pillarLabel(key))}</span>` +
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
    verdict = i18n.t("verdictReady");
  } else if (score >= 50) {
    verdict = i18n.t("verdictPartial");
  } else {
    verdict = i18n.t("verdictPoor");
  }
  const points = [];
  if ((readiness.cap_reasons || []).length) {
    points.push(escapeHtml(i18n.t("summaryCapped", readiness.safety_cap, readiness.cap_reasons.join(" "))));
  }
  if (high) points.push(escapeHtml(i18n.t("summaryCritical", high)));
  if (blocking) points.push(escapeHtml(i18n.t("summaryBlocking", blocking)));
  const validation = (state.draft || {}).validation || {};
  if ((state.draft?.proposed_changes || []).length && validation.after_score != null) {
    points.push(
      `<span class="autofix">` +
      escapeHtml(
        i18n.t(
          "summaryAutofix",
          state.draft.proposed_changes.length,
          validation.before_score,
          validation.after_score
        )
      ) +
      `</span>`
    );
  }
  $("summary").innerHTML =
    `<div class="verdict">${escapeHtml(verdict)} (${score}/100)</div>` +
    (points.length ? `<ul>${points.map((p) => `<li>${p}</li>`).join("")}</ul>` : "");
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
    : `<p class='note'>${escapeHtml(i18n.t("noFindings"))}</p>`;
  $("findings-count").textContent = String(sorted.length);
}

function renderQuestions() {
  const questions = state.result.merchant_questions || [];
  $("questions").innerHTML = questions
    .map(
      (item) =>
        `<div class="question"><div>` +
        (item.blocking ? `<span class="blocking-tag">${escapeHtml(i18n.t("blocking"))}</span>` : "") +
        `${escapeHtml(item.question)}</div>` +
        `<div class="why">${escapeHtml(item.reason)}</div>` +
        `<input data-field="${escapeHtml(item.field)}" type="text"` +
        ` placeholder="${escapeHtml(i18n.t("answerPlaceholder", item.field))}" value="${escapeHtml(state.answers[item.field] || "")}"></div>`
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
    : `<p class='note'>${escapeHtml(i18n.t("fixesPending"))}</p>`;
  const validation = source.validation || {};
  $("validation").innerHTML =
    changes.length && validation.after_score != null
      ? `<div class="delta">${escapeHtml(i18n.t("validationLine", validation.before_score, validation.after_score))}</div>`
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
    ? `<div class="cap"><strong>${escapeHtml(i18n.t("capBanner", readiness.safety_cap))}</strong> ` +
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
    appendAsk("agent", i18n.t("error", friendlyError(error.message)));
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

document.addEventListener("DOMContentLoaded", () => {
  i18n.set(i18n.detect());
  $("lang").value = i18n.lang;
  loadSettings();
});
$("lang").addEventListener("change", () => {
  i18n.set($("lang").value);
  if (state.result) render();
});
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
    event.target.textContent = i18n.t("copied");
    setTimeout(() => (event.target.textContent = i18n.t("copy")), 1200);
  });
});
$("copy-json").addEventListener("click", async () => {
  if (!state.result) return;
  await navigator.clipboard.writeText(JSON.stringify(state.draft || state.result, null, 2));
  setStatus(i18n.t("statusJsonCopied"));
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
