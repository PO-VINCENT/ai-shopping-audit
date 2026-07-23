// parity.mjs — cross-language release gate: JS engine vs the Python oracle.
// Run from anywhere inside the repo:  node browser-extension-standalone/parity/parity.mjs
// Requires the Python package importable (pip install -e .) so `python3 -m catalogready.cli` works.
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { auditProductPage } from "../engine.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));      // …/browser-extension-standalone/parity
const REPO = resolve(HERE, "..", "..");                    // repo root (Python package lives here)
const DEMO = join(REPO, "examples", "demo-store");
const URL = "https://demo.example/p/1";

const FIXTURES = [
  { name: "demo/index.html", file: join(DEMO, "index.html") },
  { name: "demo/bad-product.html", file: join(DEMO, "bad-product.html") },
  { name: "fixtures/proof.html", file: join(HERE, "fixtures", "proof.html") },
  { name: "fixtures/injection.html", file: join(HERE, "fixtures", "injection.html") },
  { name: "fixtures/zero-price.html", file: join(HERE, "fixtures", "zero-price.html") },
  { name: "fixtures/clean.html", file: join(HERE, "fixtures", "clean.html") },
];

function runPython(url, file) {
  const out = execFileSync("python3", ["-m", "catalogready.cli", "audit", url, file, "--json"], {
    cwd: REPO, encoding: "utf-8", maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(out);
}
const sortedRuleIds = (f) => f.map((x) => String(x.rule_id)).sort();

function compare(name, py, js) {
  const before = py.readiness.before;
  const diffs = []; const fieldPass = {};
  const check = (field, a, b) => { const eq = JSON.stringify(a) === JSON.stringify(b); fieldPass[field] = eq; if (!eq) diffs.push({ field, python: a, js: b }); };
  check("score", before.score, js.score);
  check("raw_score", before.raw_score, js.raw_score);
  check("deductions", before.deductions, js.deductions);
  check("safety_cap", before.safety_cap, js.safety_cap);
  check("cap_reasons", [...before.cap_reasons].sort(), [...js.cap_reasons].sort());
  for (const pillar of ["product_identity","offer_completeness","structured_data","decision_evidence","media_variants","claim_grounding"])
    check(`pillar.${pillar}`, before.components[pillar].score, js.components[pillar].score);
  for (const p of ["comprehensive","openai","google","microsoft","anthropic","perplexity"])
    check(`platform.${p}`, before.platform_scores[p].score, js.platform_scores[p].score);
  check("findings", sortedRuleIds(py.findings), sortedRuleIds(js.findings));
  return { name, pass: diffs.length === 0, diffs, fieldPass };
}

const FIELDS = ["score","raw_score","deductions","safety_cap","cap_reasons",
  "pillar.product_identity","pillar.offer_completeness","pillar.structured_data",
  "pillar.decision_evidence","pillar.media_variants","pillar.claim_grounding",
  "platform.comprehensive","platform.openai","platform.google","platform.microsoft",
  "platform.anthropic","platform.perplexity","findings"];

let anyFail = false; const results = [];
for (const fx of FIXTURES) {
  const html = readFileSync(fx.file, "utf-8");
  const py = runPython(URL, fx.file);
  const js = auditProductPage(html, URL);
  const r = compare(fx.name, py, js); results.push(r); if (!r.pass) anyFail = true;
}
const nameW = Math.max(...results.map((r) => r.name.length), 8);
console.log("\nPARITY TABLE (fixture x field)\n");
for (const r of results) console.log(`${r.name.padEnd(nameW)}  [${FIELDS.map((f) => (r.fieldPass[f] ? "." : "X")).join("")}]  ${r.pass ? "PASS" : "FAIL"}`);
console.log("\n( . = match, X = mismatch ) fields:", FIELDS.length);
for (const r of results) { if (r.pass) continue; console.log(`--- DIFFS ${r.name} ---`); for (const d of r.diffs) console.log(`  ${d.field}: python=${JSON.stringify(d.python)} js=${JSON.stringify(d.js)}`); }
console.log(anyFail ? "\nRESULT: FAIL\n" : "\nRESULT: ALL FIXTURES PASS\n");
process.exit(anyFail ? 1 : 0);
