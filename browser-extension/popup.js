const $ = (id) => document.getElementById(id);
let lastReport = null;

function setStatus(message, isError = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", isError);
}

function addListItems(element, values) {
  element.replaceChildren();
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    element.appendChild(item);
  }
}

async function loadSettings() {
  const settings = await chrome.storage.local.get(["server", "provider", "model", "mode"]);
  if (settings.server) $("server").value = settings.server;
  if (settings.provider) $("provider").value = settings.provider;
  if (settings.model) $("model").value = settings.model;
  if (settings.mode) $("mode").value = settings.mode;
}

async function saveSettings() {
  await chrome.storage.local.set({
    server: $("server").value.trim(),
    provider: $("provider").value,
    model: $("model").value.trim(),
    mode: $("mode").value,
  });
}

async function currentPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id || !/^https?:/.test(tab.url || "")) {
    throw new Error("Open a public product page before running the agent.");
  }
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => ({
      url: window.location.href,
      html: document.documentElement.outerHTML,
    }),
  });
  if (!results[0]?.result?.html) throw new Error("The page HTML could not be read.");
  return results[0].result;
}

function render(report) {
  lastReport = report;
  const readiness = report.readiness?.before || {};
  const afterScore = report.validation?.after_score;
  $("score").textContent = report.validation?.status === "validated" && Number.isFinite(afterScore)
    ? `${readiness.score ?? 0} → ${afterScore}`
    : `${readiness.score ?? 0}/100`;
  $("score-status").textContent = (report.status || "needs_review").replaceAll("_", " ");
  $("score-status").classList.toggle("ready", report.status === "ready_for_approval");

  const product = report.evidence_record?.product || {};
  $("listing-title").textContent = product.title || "Untitled product";
  $("description").textContent = report.planner_summary || "Deterministic priority plan.";
  addListItems(
    $("bullets"),
    (report.plan || []).map((item) => `${item.priority}. ${item.action}`),
  );
  const changes = (report.proposed_changes || []).map(
    (item) => `${item.operation.replaceAll("_", " ")} · ${item.evidence_ids.length} evidence source${item.evidence_ids.length === 1 ? "" : "s"}`,
  );
  addListItems($("customers"), changes.length ? changes : ["Audit mode produced no changes."]);
  const questions = (report.merchant_questions || []).map(
    (item) => `${item.blocking ? "Required" : "Optional"}: ${item.question}`,
  );
  if (!questions.length) questions.push("No merchant questions remain.");
  addListItems($("questions"), questions);

  $("claim-summary").replaceChildren();
  const good = document.createElement("div");
  good.className = "claim-good";
  good.textContent = "Storefront writes disabled";
  const bad = document.createElement("div");
  bad.className = report.validation?.accepted ? "claim-good" : "claim-bad";
  bad.textContent = report.validation?.accepted
    ? "Isolated preview validated"
    : "Merchant input or review required";
  $("claim-summary").append(good, bad);
  $("result").classList.remove("hidden");
}

async function analyze() {
  const button = $("analyze");
  const server = $("server").value.trim().replace(/\/$/, "");
  button.disabled = true;
  $("result").classList.add("hidden");
  setStatus("Reading the current product page…");
  try {
    await saveSettings();
    let health;
    try {
      health = await fetch(`${server}/health`);
    } catch (error) {
      throw new Error(
        `Cannot reach ${server}. Start the local server with: PYTHONPATH=src .venv/bin/python -m catalogready.local_server`,
      );
    }
    if (!health.ok) throw new Error(`The local agent health check returned ${health.status}.`);
    const page = await currentPage();
    setStatus("Inspecting evidence, planning fixes, and validating a safe preview…");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    const response = await fetch(`${server}/v1/agent/html`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...page,
        provider: $("provider").value,
        model: $("model").value.trim(),
        mode: $("mode").value,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || `Local agent returned ${response.status}.`);
    render(body);
    setStatus("Agent run complete. No storefront changes were made.");
  } catch (error) {
    setStatus(error.name === "AbortError" ? "The analysis timed out." : error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function copyReport() {
  if (!lastReport) return;
  await navigator.clipboard.writeText(JSON.stringify(lastReport, null, 2));
  setStatus("Complete JSON report copied.");
}

document.addEventListener("DOMContentLoaded", loadSettings);
$("analyze").addEventListener("click", analyze);
$("copy").addEventListener("click", copyReport);
