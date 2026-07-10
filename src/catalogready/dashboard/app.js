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
const state = { result: null, draft: null, answers: {} };

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
    setStatus(error.message, true);
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

function renderTrace(result) {
  el("trace").innerHTML = (result.trace || [])
    .map((event) => `<div><span class="dot">●</span>${escapeHtml(event.tool)} — ${escapeHtml(event.summary)}</div>`)
    .join("");
}

function renderFindings(findings) {
  const order = { high: 0, medium: 1, low: 2 };
  const sorted = [...findings].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
  el("panel-findings").innerHTML = sorted.length
    ? sorted
        .map(
          (item) =>
            `<div class="finding"><h4><span class="sev ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span> ` +
            `${escapeHtml(item.title)}<span class="chip">${escapeHtml(item.rule_id)}</span></h4>` +
            `<p>${escapeHtml(item.evidence)}</p><p class="fix">→ ${escapeHtml(item.recommendation)}</p></div>`
        )
        .join("")
    : `<p>${escapeHtml(i18n.t("noFindings"))}</p>`;
  el("findings-count").textContent = String(sorted.length);
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
  if (high || medium) {
    points.push(escapeHtml(i18n.t("summaryFindings", high, medium)));
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
  renderDial(readiness.score || 0);
  renderPillars(readiness.components || {});
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
    appendMessage("agent", i18n.t("error", error.message));
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

/* ---------- wiring ---------- */

i18n.set(i18n.detect());
el("lang").value = i18n.lang;

el("lang").addEventListener("change", () => {
  i18n.set(el("lang").value);
  if (state.result) render(state.result);
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

el("url").addEventListener("input", () => {
  // A new URL means the pasted/fetched HTML no longer matches it.
  if (state.result && el("url").value.trim() !== (state.result.input || {}).url) {
    el("html").value = "";
  }
});

el("run").addEventListener("click", () => {
  state.answers = {};
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
