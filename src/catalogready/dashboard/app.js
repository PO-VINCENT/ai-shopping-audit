"use strict";

/* CatalogReady dashboard — same-origin client for the local server API.
   All capability lives in the service; this file only renders results.
   UI strings come from i18n.js (browser-language default, header override). */

const DEMO_GOOD_URL = "https://example.com/products/cr-001";
const DEMO_GOOD_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="description" content="Waterproof commuter shoe with verified materials, shipping and returns information.">
  <title>CatalogReady Waterproof Commuter Shoe – Blue</title>
  <link rel="canonical" href="https://example.com/products/cr-001">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "CatalogReady Waterproof Commuter Shoe – Blue",
    "sku": "CR-001-BLU-M",
    "brand": {"@type": "Brand", "name": "CatalogReady"},
    "category": "Apparel & Accessories > Shoes",
    "image": [
      "https://example.com/images/cr-001-blue-side.jpg",
      "https://example.com/images/cr-001-blue-sole.jpg"
    ],
    "material": "Recycled polyester upper with verified waterproof membrane",
    "offers": {
      "@type": "Offer",
      "price": "149.00",
      "priceCurrency": "AUD",
      "availability": "https://schema.org/InStock",
      "url": "https://example.com/products/cr-001"
    }
  }
  <\/script>
</head>
<body>
  <main>
    <h1>Waterproof Commuter Shoe</h1>
    <p>This blue commuter shoe is designed for wet urban travel and everyday walking. The upper uses recycled polyester over a waterproof membrane. The product is intended for rain, puddles and normal city conditions; it is not designed for full submersion or technical hiking.</p>
    <h2>Specifications and materials</h2>
    <p>The shoe has a recycled polyester upper, rubber outsole, removable insole and sealed internal membrane. Size medium corresponds to the published size guide. Product dimensions and care instructions are shown before purchase so shoppers can verify suitability.</p>
    <h2>Delivery, returns and limitations</h2>
    <p>Orders dispatch within two business days. Standard delivery estimates are shown during checkout. Unworn products can be returned within thirty days in their original packaging. Customers should avoid machine washing, prolonged immersion and use as certified safety footwear.</p>
    <p>Price: AUD 149.00. Availability: in stock.</p>
  </main>
</body>
</html>`;

const DEMO_BAD_URL = "https://example.com/products/bad-shoe";
const DEMO_BAD_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>The #1 Best Commuter Shoe – Buy Now!</title>
</head>
<body>
  <main>
    <h1>The Best Commuter Shoe in the World</h1>
    <p>Clinically proven comfort. Lifetime warranty. 100% waterproof.
    This shoe changes everything. Order today!</p>
    <p>Trusted by thousands. You will never buy another shoe again.</p>
  </main>
</body>
</html>`;

const el = (id) => document.getElementById(id);
const state = { result: null, draft: null, answers: {}, grouping: "severity", metricFilter: null, htmlSource: "pasted" };

/* ---------- helpers ---------- */

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value == null ? "" : value);
  return div.innerHTML;
}

function scoreColor(ratio) {
  return ratio >= 0.8 ? "var(--good)" : ratio >= 0.5 ? "var(--warn)" : "var(--bad)";
}

function setStatus(message, isError) {
  const status = el("status");
  status.textContent = message || "";
  status.classList.toggle("error", Boolean(isError));
}

async function api(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function friendlyError(message) {
  if (/missing api key|model id is required/i.test(message)) {
    return `${message} — ${i18n.t("keyHint")}`;
  }
  return message;
}

/* ---------- fetch & agent runs ---------- */

async function fetchHtml() {
  const url = el("url").value.trim();
  if (!url) {
    setStatus(i18n.t("statusEnterUrl"), true);
    return false;
  }
  const button = el("fetch");
  button.disabled = true;
  setStatus(i18n.t("statusFetching"));
  try {
    const payload = await api("/v1/fetch", { url });
    el("html").value = payload.html;
    state.htmlSource = "fetched";
    if (/pardon our interruption|access denied|are you a robot|attention required|just a moment|verify you are human/i.test(payload.html)) {
      setStatus(i18n.t("statusBotWall"), true);
      return true; // still auditable — it shows what a generic crawler would see
    }
    setStatus(i18n.t("statusFetched", Math.round(payload.bytes / 1024)));
    return true;
  } catch (error) {
    setStatus(error.message, true);
    return false;
  } finally {
    button.disabled = false;
  }
}

function runOptions(mode) {
  const options = {
    url: el("url").value.trim(),
    html: el("html").value,
    mode,
    provider: el("provider").value,
    model: el("model").value.trim(),
  };
  if (Object.keys(state.answers).length) options.merchant_answers = state.answers;
  return options;
}

async function runAgent(mode) {
  const url = el("url").value.trim();
  if (!url) {
    setStatus(i18n.t("statusNeedUrl"), true);
    return;
  }
  if (!el("html").value.trim() && !(await fetchHtml())) return;
  const button = el("run");
  button.disabled = true;
  setStatus(mode === "draft" ? i18n.t("statusDrafting") : i18n.t("statusAuditing"));
  try {
    const result = await api("/v1/agent/html", runOptions(mode));
    if (mode === "draft") {
      state.draft = result;
    } else {
      state.result = result;
      state.draft = null;
    }
    render(state.result || result);
    if (mode === "draft") {
      renderFixes(result);
      renderSummary();
    }
    setStatus("");
    if (mode === "audit") autoDraft();
  } catch (error) {
    setStatus(friendlyError(error.message), true);
  } finally {
    button.disabled = false;
  }
}

async function autoDraft() {
  // Fix suggestions are drafted automatically after every audit. Deterministic,
  // in-memory, and never written anywhere — the Fixes tab shows the outcome.
  try {
    state.draft = await api("/v1/agent/html", runOptions("draft"));
    renderFixes(state.draft);
    renderSummary();
  } catch (error) {
    /* auto-suggestions are best-effort; the manual Draft button still works */
  }
  autoOnlineChecks();
}

async function autoOnlineChecks() {
  // Bounded image-size checks via the local server (max 3 fetches).
  // Informational: findings are appended, the score never changes.
  try {
    const images = state.result?.evidence_record?.product?.images || [];
    if (!images.length) return;
    const payload = await api("/v1/online-checks", {
      url: el("url").value.trim(),
      images,
    });
    if (payload.findings?.length) {
      state.result.findings.push(...payload.findings);
      renderFindings(state.result.findings);
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
  el("dial").innerHTML =
    `<circle cx="66" cy="66" r="56" fill="none" stroke="var(--chip)" stroke-width="10"/>` +
    `<circle cx="66" cy="66" r="56" fill="none" stroke="${scoreColor(score / 100)}" stroke-width="10"` +
    ` stroke-linecap="round" stroke-dasharray="${filled.toFixed(1)} ${circumference.toFixed(1)}"` +
    ` transform="rotate(-90 66 66)"/>` +
    `<text x="66" y="62" text-anchor="middle" font-size="34" font-weight="700">${score}</text>` +
    `<text x="66" y="86" text-anchor="middle" font-size="12" opacity="0.7">/ 100</text>`;
}

function renderPillars(components) {
  const labels = i18n.pillars();
  const explain = i18n.pillarExplain();
  el("pillars").innerHTML = Object.entries(components)
    .map(([key, section]) => {
      const max = section.max_score || 1;
      const ratio = section.score / max;
      const checks = Object.entries(section.checks || {})
        .map(
          ([check, passed]) =>
            `<li class="${passed ? "pass" : "fail"}">` +
            `<span aria-hidden="true">${passed ? "✓" : "✗"}</span> ${escapeHtml(i18n.checkLabel(check))}</li>`
        )
        .join("");
      return (
        `<div class="pillar-group">` +
        `<button class="pillar" type="button" data-pillar="${escapeHtml(key)}" aria-expanded="false">` +
        `<span><span class="chev" aria-hidden="true">▸</span>${escapeHtml(labels[key] || key)}</span>` +
        `<span class="bar"><i style="width:${Math.round(ratio * 100)}%;background:${scoreColor(ratio)}"></i></span>` +
        `<span>${section.score}/${max}</span></button>` +
        `<div class="pillar-detail" hidden>` +
        `<p>${escapeHtml(explain[key] || "")}</p>` +
        `<ul class="checks">${checks}</ul>` +
        `</div></div>`
      );
    })
    .join("");
}

function renderCaps(readiness) {
  const reasons = readiness.cap_reasons || [];
  el("caps").innerHTML = reasons.length
    ? `<div class="cap"><strong>${escapeHtml(i18n.t("capBanner", readiness.safety_cap))}</strong> ` +
      reasons.map(escapeHtml).join(" ") + `</div>`
    : "";
}

function renderScoreBreakdown(readiness) {
  const comprehensive = (readiness.platform_scores || {}).comprehensive || readiness;
  const raw = Number(comprehensive.raw_score || 0);
  const deductions = Number(comprehensive.deductions || 0);
  const beforeCap = Math.max(1, raw - deductions);
  const score = Number(comprehensive.score || readiness.score || 0);
  const cap = Number(comprehensive.safety_cap || 100);
  const items = comprehensive.deduction_items || [];
  const rows = items.length
    ? items.map((item) =>
        `<li><span><span class="chip">${escapeHtml(item.rule_id)}</span> ` +
        `${escapeHtml(item.title)} <span class="deduction-meta">${escapeHtml(item.severity)} · ` +
        `${escapeHtml(i18n.metricInfo(item.metric || "").name)}</span></span>` +
        `<strong>−${Number(item.points || 0)}</strong></li>`
      ).join("")
    : `<li class="no-deduction">${escapeHtml(i18n.t("noDeductions"))}</li>`;
  const capLine = cap < beforeCap
    ? `<div class="cap-equation">${escapeHtml(i18n.t("scoreBeforeCap", beforeCap))} ` +
      `<span>→</span> ${escapeHtml(i18n.t("scoreCapApplied", cap, score))}</div>`
    : "";
  el("score-breakdown").innerHTML =
    `<div class="score-breakdown-head"><strong>${escapeHtml(i18n.t("scoreBreakdownTitle"))}</strong>` +
    `<strong>${score}/100</strong></div>` +
    `<div class="score-equation"><span>${escapeHtml(i18n.t("checkPoints", raw))}</span>` +
    `<b>−</b><span>${escapeHtml(i18n.t("deductionPoints", deductions))}</span>` +
    `<b>=</b><strong>${beforeCap}</strong></div>${capLine}` +
    `<div class="deduction-title">${escapeHtml(i18n.t("deductionListTitle"))}</div>` +
    `<ul class="deduction-list">${rows}</ul>`;
}

function renderTrace(result) {
  el("trace").innerHTML = (result.trace || [])
    .map((event) => `<div><span class="dot">●</span>${escapeHtml(event.tool)} — ${escapeHtml(event.summary)}</div>`)
    .join("");
}

const METRIC_ORDER = [
  "machine_readability", "validity", "completeness", "consistency",
  "trust", "accessibility", "transactability", "freshness",
];

function metricStatuses(findings) {
  const status = {};
  METRIC_ORDER.forEach((key) => (status[key] = { level: "clean", count: 0 }));
  findings.forEach((item) => {
    const entry = status[item.metric] || (status[item.metric] = { level: "clean", count: 0 });
    entry.count += 1;
    if (item.severity === "high") entry.level = "bad";
    else if (entry.level !== "bad") entry.level = "warn";
  });
  return status;
}

function renderPlatformScores(readiness) {
  const scores = readiness.platform_scores || {};
  el("metric-strip").innerHTML = Object.entries(scores).map(([platform, section]) => {
    const metrics = section.metrics || {};
    const metricTiles = METRIC_ORDER.filter((key) => (metrics[key]?.findings || 0) > 0)
      .map((key) => {
        const info = i18n.metricInfo(key);
        const active = state.metricFilter === key ? " is-active" : "";
        return `<button class="metric-tile warn${active}" type="button" data-metric="${key}"` +
          ` title="${escapeHtml(info.question)}">${escapeHtml(info.name)}` +
          `<span class="m-count">${metrics[key].findings}</span></button>`;
      }).join("");
    const surfaces = (section.surfaces || []).join(" · ");
    return `<section class="platform-card ${platform === "comprehensive" ? "comprehensive" : ""}">` +
      `<div class="platform-head"><strong>${escapeHtml(section.label || platform)}</strong>` +
      `<span style="color:${scoreColor((section.score || 0) / 100)}">${section.score}/100</span></div>` +
      `<div class="platform-surfaces">${escapeHtml(surfaces)}</div>` +
      `<div class="platform-metrics">${metricTiles || `<span class="metric-clear">${escapeHtml(i18n.t("platformClear"))}</span>`}</div>` +
      `</section>`;
  }).join("");
}

function findingCard(item) {
  const metricName = i18n.metricInfo(item.metric || "").name;
  return (
    `<div class="finding"><h4><span class="sev ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span> ` +
    `${escapeHtml(item.title)}<span class="chip">${escapeHtml(item.rule_id)}</span>` +
    (item.metric ? `<span class="chip metric-chip">${escapeHtml(metricName)}</span>` : "") +
    `</h4><p>${escapeHtml(item.evidence)}</p><p class="fix">→ ${escapeHtml(item.recommendation)}</p></div>`
  );
}

function renderFindings(findings) {
  const order = { high: 0, medium: 1, low: 2 };
  let visible = [...findings].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
  if (state.metricFilter) {
    visible = visible.filter((item) => item.metric === state.metricFilter);
  }
  const list = el("findings-list");
  if (!visible.length) {
    list.innerHTML = `<p>${escapeHtml(i18n.t("noFindings"))}</p>`;
  } else if (state.grouping === "metric") {
    list.innerHTML = METRIC_ORDER.map((key) => {
      const group = visible.filter((item) => item.metric === key);
      if (!group.length) return "";
      const info = i18n.metricInfo(key);
      return (
        `<div class="metric-group"><h3>${escapeHtml(info.name)} ` +
        `<span class="note">${escapeHtml(info.question)}</span></h3>` +
        group.map(findingCard).join("") + `</div>`
      );
    }).join("");
  } else {
    list.innerHTML = visible.map(findingCard).join("");
  }
  el("findings-count").textContent = String(visible.length);
  el("metric-filter-label").textContent = state.metricFilter
    ? `· ${i18n.metricInfo(state.metricFilter).name}`
    : "";
}

function renderQuestions(questions) {
  const container = el("questions");
  container.innerHTML = questions.length
    ? questions
        .map(
          (item, index) =>
            `<div class="question"><div class="q">` +
            (item.blocking ? `<span class="blocking-tag">${escapeHtml(i18n.t("blocking"))}</span>` : "") +
            `${escapeHtml(item.question)}</div>` +
            `<div class="why">${escapeHtml(item.reason)}</div>` +
            `<input data-field="${escapeHtml(item.field)}" data-question="${index}" type="text"` +
            ` placeholder="${escapeHtml(i18n.t("answerPlaceholder", item.field))}" value="${escapeHtml(state.answers[item.field] || "")}"></div>`
        )
        .join("")
    : `<p>${escapeHtml(i18n.t("noQuestions"))}</p>`;
  el("resume").hidden = !questions.length;
  el("questions-count").textContent = String(questions.length);
}

function renderFixes(result) {
  const changes = result.proposed_changes || [];
  el("changes").innerHTML = changes.length
    ? `<p class="note">${escapeHtml(i18n.t("proposedChanges", changes.length))}</p>` +
      changes
        .map(
          (item) =>
            `<div class="change"><strong>${escapeHtml(item.id)}</strong> · ${escapeHtml(item.operation)}` +
            ` <span class="muted">(${escapeHtml(i18n.t("reversible"))}, ${escapeHtml(item.status)})</span></div>`
        )
        .join("")
    : "";
  const validation = result.validation || {};
  if (validation.after_score != null && changes.length) {
    const delta = validation.score_delta || 0;
    const deltaText = `${delta >= 0 ? "+" : ""}${delta}`;
    el("validation").innerHTML =
      `<div class="delta${delta < 0 ? " negative" : ""}">` +
      escapeHtml(i18n.t("validationLine", validation.before_score, validation.after_score, deltaText, validation.status)) +
      `</div>`;
  } else {
    el("validation").innerHTML = "";
  }
  const jsonldChange = changes.find((item) => item.operation === "replace_product_jsonld");
  el("jsonld-wrap").hidden = !jsonldChange;
  if (jsonldChange) el("jsonld").textContent = JSON.stringify(jsonldChange.value, null, 2);
}

function renderSummary() {
  const result = state.result;
  if (!result) return;
  const readiness = (result.readiness || {}).before || {};
  const score = readiness.score || 0;
  const findings = result.findings || [];
  const high = findings.filter((f) => f.severity === "high").length;
  const medium = findings.filter((f) => f.severity === "medium").length;
  const blocking = (result.merchant_questions || []).filter((q) => q.blocking).length;

  let verdict;
  if (score >= 80 && (readiness.cap_reasons || []).length === 0) {
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
  if (readiness.deductions) {
    points.push(escapeHtml(i18n.t("summaryDeductions", readiness.deductions, readiness.raw_score)));
  }
  if (high || medium) {
    points.push(escapeHtml(i18n.t("summaryFindings", high, medium)));
  }
  const status = metricStatuses(findings);
  const worst = METRIC_ORDER.filter((key) => status[key].level === "bad")
    .sort((a, b) => status[b].count - status[a].count)[0];
  if (worst) {
    const highInWorst = findings.filter(
      (f) => f.metric === worst && f.severity === "high"
    ).length;
    points.push(
      escapeHtml(i18n.t("summaryWeakest", i18n.metricInfo(worst).name, highInWorst, status[worst].count))
    );
  }
  if (blocking) {
    points.push(escapeHtml(i18n.t("summaryBlocking", blocking)));
  }
  const topAction = (result.plan || [])[0];
  if (topAction) {
    points.push(escapeHtml(i18n.t("summaryStart", topAction.action)));
  }
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

  el("summary").innerHTML =
    `<div class="verdict">${escapeHtml(verdict)} (${escapeHtml(i18n.t("scoreLine", score, readiness.status || ""))})</div>` +
    (points.length ? `<ul>${points.map((p) => `<li>${p}</li>`).join("")}</ul>` : "");
}

function renderEvidence(record) {
  el("evidence").innerHTML = (record.evidence || [])
    .map(
      (item) =>
        `<tr><td>${escapeHtml(item.id)}</td><td>${escapeHtml(item.field)}</td>` +
        `<td>${escapeHtml(item.value)}</td><td>${escapeHtml(item.source)}</td></tr>`
    )
    .join("");
}

function render(result) {
  el("empty").hidden = true;
  el("result").hidden = false;
  const readiness = (result.readiness || {}).before || {};
  const product = (result.evidence_record || {}).product || {};
  el("product-title").textContent = product.title || "Product page";
  el("product-url").textContent = (result.input || {}).url || "";
  el("html-source").textContent = i18n.t(state.htmlSource === "fetched" ? "sourceFetched" : "sourcePasted");
  renderDial(readiness.score || 0);
  renderPillars(readiness.components || {});
  renderScoreBreakdown(readiness);
  renderPlatformScores(readiness);
  renderCaps(readiness);
  renderTrace(result);
  renderFindings(result.findings || []);
  renderQuestions(result.merchant_questions || []);
  renderFixes(state.draft || result);
  renderEvidence(result.evidence_record || {});
  renderSummary();
}

/* ---------- chat ---------- */

function appendMessage(role, text, mode) {
  const log = el("chat-log");
  const modeTag = mode ? `<span class="mode">${escapeHtml(i18n.t("answeredBy", mode))}</span>` : "";
  log.insertAdjacentHTML(
    "beforeend",
    `<div class="msg ${role}"><div class="bubble">${escapeHtml(text)}${modeTag}</div></div>`
  );
  log.scrollTop = log.scrollHeight;
}

async function sendChat() {
  const input = el("chat-input");
  const question = input.value.trim();
  if (!question) return;
  const context = state.draft || state.result;
  if (!context) {
    appendMessage("agent", i18n.t("chatNeedsAudit"));
    return;
  }
  input.value = "";
  appendMessage("user", question);
  el("chat-send").disabled = true;
  try {
    const reply = await api("/v1/agent/ask", {
      audit_result: context,
      question,
      provider: el("provider").value,
      model: el("model").value.trim(),
    });
    appendMessage("agent", reply.answer, reply.mode);
  } catch (error) {
    appendMessage("agent", i18n.t("error", friendlyError(error.message)));
  } finally {
    el("chat-send").disabled = false;
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

/* ---------- server health ---------- */

async function loadHealth() {
  const info = el("server-info");
  try {
    const response = await fetch("/health");
    const health = await response.json();
    const started = new Date(health.started_at).toLocaleTimeString();
    if (health.stale) {
      info.textContent = i18n.t("serverStale", health.version, started);
      info.classList.add("stale");
    } else {
      info.textContent = i18n.t("serverInfo", health.version, started);
      info.classList.remove("stale");
    }
  } catch (error) {
    info.textContent = i18n.t("serverUnreachable");
    info.classList.add("stale");
  }
}

/* ---------- wiring ---------- */

i18n.set(i18n.detect());
el("lang").value = i18n.lang;
loadHealth();
setInterval(loadHealth, 30000);

el("lang").addEventListener("change", () => {
  i18n.set(el("lang").value);
  if (state.result) render(state.result);
  loadHealth();
});

el("pillars").addEventListener("click", (event) => {
  const button = event.target.closest(".pillar");
  if (!button) return;
  const detail = button.parentElement.querySelector(".pillar-detail");
  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!expanded));
  button.querySelector(".chev").textContent = expanded ? "▸" : "▾";
  detail.hidden = expanded;
});

el("metric-strip").addEventListener("click", (event) => {
  const tile = event.target.closest(".metric-tile");
  if (!tile || !state.result) return;
  state.metricFilter = state.metricFilter === tile.dataset.metric ? null : tile.dataset.metric;
  renderFindings(state.result.findings || []);
  renderPlatformScores((state.result.readiness || {}).before || {});
});

document.querySelectorAll(".group-btn").forEach((button) => {
  button.addEventListener("click", () => {
    state.grouping = button.dataset.group;
    document.querySelectorAll(".group-btn").forEach((item) =>
      item.classList.toggle("is-active", item === button)
    );
    if (state.result) renderFindings(state.result.findings || []);
  });
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("is-active", item === tab));
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.hidden = panel.id !== `panel-${tab.dataset.tab}`;
    });
  });
});

el("demo-good").addEventListener("click", () => {
  el("url").value = DEMO_GOOD_URL;
  el("html").value = DEMO_GOOD_HTML;
  state.answers = {};
  setStatus(i18n.t("demoGoodLoaded"));
});

el("demo-bad").addEventListener("click", () => {
  el("url").value = DEMO_BAD_URL;
  el("html").value = DEMO_BAD_HTML;
  state.answers = {};
  setStatus(i18n.t("demoBadLoaded"));
});

el("fetch").addEventListener("click", fetchHtml);

el("html").addEventListener("input", () => {
  state.htmlSource = "pasted";
});

el("url").addEventListener("input", () => {
  // A new URL means the pasted/fetched HTML no longer matches it.
  if (state.result && el("url").value.trim() !== (state.result.input || {}).url) {
    el("html").value = "";
  }
});

el("run").addEventListener("click", () => {
  state.answers = {};
  state.metricFilter = null;
  runAgent("audit");
});

el("resume").addEventListener("click", () => {
  document.querySelectorAll("#questions input").forEach((input) => {
    const value = input.value.trim();
    if (value) state.answers[input.dataset.field] = value;
  });
  runAgent("audit");
});

el("draft").addEventListener("click", () => runAgent("draft"));

el("chat-send").addEventListener("click", sendChat);
el("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") sendChat();
});

el("copy-jsonld").addEventListener("click", (event) => {
  navigator.clipboard.writeText(el("jsonld").textContent).then(() => {
    event.target.textContent = i18n.t("copied");
    setTimeout(() => (event.target.textContent = i18n.t("copy")), 1200);
  });
});

el("download-json").addEventListener("click", () => {
  if (state.result) download("catalogready-result.json", JSON.stringify(state.draft || state.result, null, 2), "application/json");
});

el("download-report").addEventListener("click", async () => {
  if (!state.result) return;
  try {
    const payload = await api("/v1/report/html", { audit_result: state.result });
    download("catalogready-report.html", payload.html, "text/html");
  } catch (error) {
    setStatus(error.message, true);
  }
});
