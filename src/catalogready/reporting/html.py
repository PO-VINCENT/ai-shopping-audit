"""Render a self-contained HTML report from an audit or agent result.

The output embeds all styles and scripts, loads no external resources,
and works as a single file that can be attached, hosted, or shared.
"""

from __future__ import annotations

import html
import json
from typing import Any

PILLAR_LABELS = {
    "product_identity": "Product identity",
    "offer_completeness": "Offer completeness",
    "structured_data": "Structured data",
    "decision_evidence": "Decision evidence",
    "media_variants": "Media & variants",
    "claim_grounding": "Claim grounding",
}

_SEVERITY_ORDER = ("high", "medium", "low")

_CSS = """
:root {
  --bg: #ffffff; --fg: #1a1f2b; --muted: #5b6472; --card: #f5f7fa;
  --border: #e2e7ee; --good: #14803c; --warn: #b45309; --bad: #b91c1c;
  --accent: #2456d6; --chip: #e8edf5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12151c; --fg: #e8ecf3; --muted: #9aa4b5; --card: #1a1f2a;
    --border: #2a3140; --good: #34c46b; --warn: #f5a542; --bad: #f26d6d;
    --accent: #6c96f5; --chip: #242c3b;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1rem; background: var(--bg); color: var(--fg);
  font: 16px/1.55 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 880px; margin: 0 auto; }
h1 { font-size: 1.35rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; margin: 2rem 0 .75rem; }
.sub { color: var(--muted); font-size: .9rem; word-break: break-all; }
.brand { font-weight: 700; letter-spacing: .02em; color: var(--accent); font-size: .85rem;
  text-transform: uppercase; margin-bottom: 1.25rem; }
.hero { display: flex; gap: 2rem; align-items: center; flex-wrap: wrap;
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 1.5rem; margin-top: 1rem; }
.dial { width: 132px; height: 132px; flex: 0 0 auto; }
.dial text { fill: var(--fg); }
.pillars { flex: 1 1 320px; min-width: 260px; }
.pillar { display: grid; grid-template-columns: 11rem 1fr 3.5rem; gap: .6rem;
  align-items: center; font-size: .88rem; margin: .3rem 0; }
.bar { height: 8px; border-radius: 4px; background: var(--chip); overflow: hidden; }
.bar > i { display: block; height: 100%; border-radius: 4px; }
.cap { border-left: 4px solid var(--bad); background: var(--card); padding: .75rem 1rem;
  border-radius: 0 10px 10px 0; margin-top: 1rem; font-size: .92rem; }
.finding { border: 1px solid var(--border); border-radius: 10px; padding: .8rem 1rem;
  margin: .6rem 0; background: var(--card); }
.finding h3 { margin: 0 0 .3rem; font-size: .95rem; }
.finding p { margin: .2rem 0; font-size: .88rem; color: var(--muted); }
.finding .fix { color: var(--fg); }
.chip { display: inline-block; font: 600 .72rem/1 ui-monospace, Menlo, monospace;
  background: var(--chip); border-radius: 999px; padding: .3rem .55rem; margin-left: .5rem;
  vertical-align: middle; }
.sev { font-weight: 700; font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; }
.sev.high { color: var(--bad); } .sev.medium { color: var(--warn); } .sev.low { color: var(--muted); }
pre { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1rem; overflow-x: auto; font-size: .8rem; }
button { background: var(--accent); color: #fff; border: 0; border-radius: 8px;
  padding: .55rem .9rem; font-size: .85rem; cursor: pointer; }
button:hover { opacity: .9; }
.actions { display: flex; gap: .6rem; margin: .75rem 0; flex-wrap: wrap; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; }
td, th { border-bottom: 1px solid var(--border); padding: .4rem .5rem; text-align: left; }
footer { margin-top: 2.5rem; color: var(--muted); font-size: .8rem; }
.badges { color: var(--muted); font-size: .82rem; margin-top: .5rem; }
"""


def _score_color(score: int) -> str:
    if score >= 80:
        return "var(--good)"
    if score >= 50:
        return "var(--warn)"
    return "var(--bad)"


def _dial(score: int) -> str:
    circumference = 2 * 3.14159 * 56
    filled = circumference * max(0, min(score, 100)) / 100
    color = _score_color(score)
    return (
        f'<svg class="dial" viewBox="0 0 132 132" role="img" '
        f'aria-label="Readiness score {score} out of 100">'
        f'<circle cx="66" cy="66" r="56" fill="none" stroke="var(--chip)" stroke-width="10"/>'
        f'<circle cx="66" cy="66" r="56" fill="none" stroke="{color}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{filled:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 66 66)"/>'
        f'<text x="66" y="62" text-anchor="middle" font-size="34" font-weight="700">{score}</text>'
        f'<text x="66" y="86" text-anchor="middle" font-size="12" opacity="0.7">/ 100</text>'
        f"</svg>"
    )


def _pillar_rows(components: dict[str, Any]) -> str:
    rows: list[str] = []
    for key, section in components.items():
        label = PILLAR_LABELS.get(key, key.replace("_", " ").title())
        score = int(section.get("score") or 0)
        maximum = int(section.get("max_score") or 0) or 1
        width = round(100 * score / maximum)
        color = _score_color(round(100 * score / maximum))
        rows.append(
            f'<div class="pillar"><span>{html.escape(label)}</span>'
            f'<span class="bar"><i style="width:{width}%;background:{color}"></i></span>'
            f"<span>{score}/{maximum}</span></div>"
        )
    return "".join(rows)


def _findings_section(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "<p>No findings were produced. Everything checked is machine-readable.</p>"
    parts: list[str] = []
    for severity in _SEVERITY_ORDER:
        for item in findings:
            if item.get("severity") != severity:
                continue
            parts.append(
                '<div class="finding">'
                f'<h3><span class="sev {severity}">{severity}</span> '
                f"{html.escape(str(item.get('title', 'Finding')))}"
                f'<span class="chip">{html.escape(str(item.get("rule_id", "")))}</span></h3>'
                f"<p>{html.escape(str(item.get('evidence', '')))}</p>"
                f'<p class="fix">→ {html.escape(str(item.get("recommendation", "")))}</p>'
                "</div>"
            )
    return "".join(parts)


def _share_script(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (
        "<script>\n"
        f"const CARD = {data};\n"
        """
function copyText(id, button) {
  const text = document.getElementById(id).textContent;
  navigator.clipboard.writeText(text).then(() => {
    const old = button.textContent; button.textContent = "Copied";
    setTimeout(() => { button.textContent = old; }, 1200);
  });
}
function scoreColor(ratio) {
  return ratio >= 0.8 ? "#17a34a" : ratio >= 0.5 ? "#d97706" : "#dc2626";
}
function downloadCard() {
  const canvas = document.createElement("canvas");
  canvas.width = 840; canvas.height = 440;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#141821"; ctx.fillRect(0, 0, 840, 440);
  ctx.fillStyle = "#6c96f5"; ctx.font = "700 20px sans-serif";
  ctx.fillText("CATALOGREADY", 48, 58);
  ctx.fillStyle = "#9aa4b5"; ctx.font = "16px sans-serif";
  ctx.fillText(CARD.domain, 48, 86);
  ctx.fillStyle = scoreColor(CARD.score / 100);
  ctx.font = "700 96px sans-serif";
  ctx.fillText(String(CARD.score), 48, 190);
  ctx.fillStyle = "#9aa4b5"; ctx.font = "24px sans-serif";
  ctx.fillText("/ 100 AI readiness", 48 + ctx.measureText(String(CARD.score)).width + 130, 190);
  let y = 240;
  ctx.font = "16px sans-serif";
  for (const p of CARD.pillars) {
    ctx.fillStyle = "#e8ecf3"; ctx.fillText(p.label, 48, y + 13);
    ctx.fillStyle = "#242c3b"; ctx.fillRect(280, y, 380, 14);
    ctx.fillStyle = scoreColor(p.score / p.max);
    ctx.fillRect(280, y, 380 * (p.score / p.max), 14);
    ctx.fillStyle = "#9aa4b5"; ctx.fillText(p.score + "/" + p.max, 680, y + 13);
    y += 30;
  }
  ctx.fillStyle = "#9aa4b5"; ctx.font = "15px sans-serif";
  ctx.fillText(CARD.issues, 48, 424);
  const link = document.createElement("a");
  link.download = "catalogready-score.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
}
</script>"""
    )


def _agent_report(result: dict[str, Any]) -> str:
    from ..agent.tools import build_product_jsonld

    readiness = (result.get("readiness") or {}).get("before") or {}
    evidence_record = result.get("evidence_record") or {}
    product = evidence_record.get("product") or {}
    url = str((result.get("input") or {}).get("url", ""))
    domain = url.split("//")[-1].split("/")[0] if url else "product page"
    score = int(readiness.get("score") or 0)
    components = readiness.get("components") or {}
    findings = result.get("findings") or []
    counts = {
        severity: sum(1 for item in findings if item.get("severity") == severity)
        for severity in _SEVERITY_ORDER
    }
    issue_line = (
        f"{counts['high']} critical · {counts['medium']} recommended · "
        f"{counts['low']} minor findings"
    )

    cap_html = ""
    if readiness.get("cap_reasons"):
        reasons = "".join(
            f"<div>{html.escape(str(reason))}</div>" for reason in readiness["cap_reasons"]
        )
        cap_html = (
            f'<div class="cap"><strong>Score capped at {readiness.get("safety_cap")}.</strong>'
            f"{reasons}</div>"
        )

    jsonld, _ = build_product_jsonld(evidence_record)
    jsonld_text = json.dumps(jsonld, indent=2, ensure_ascii=False)

    questions = result.get("merchant_questions") or []
    questions_html = ""
    if questions:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('field', '')))}</td>"
            f"<td>{html.escape(str(item.get('question', '')))}</td>"
            f"<td>{'blocking' if item.get('blocking') else 'advisory'}</td>"
            "</tr>"
            for item in questions
        )
        questions_html = (
            "<h2>Facts only the merchant can supply</h2>"
            "<p class='sub'>CatalogReady never invents these. Answer them with "
            "<code>--answers</code> to complete the audit.</p>"
            f"<table><tr><th>Field</th><th>Question</th><th>Type</th></tr>{rows}</table>"
        )

    pillars_payload = [
        {
            "label": PILLAR_LABELS.get(key, key.replace("_", " ").title()),
            "score": int(section.get("score") or 0),
            "max": int(section.get("max_score") or 0) or 1,
        }
        for key, section in components.items()
    ]
    share_payload = {
        "score": score,
        "domain": domain,
        "pillars": pillars_payload,
        "issues": issue_line,
    }

    title = html.escape(str(product.get("title") or domain))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CatalogReady report · {title}</title>
<style>{_CSS}</style>
</head>
<body>
<main>
  <div class="brand">CatalogReady · product AI-readiness report</div>
  <h1>{title}</h1>
  <div class="sub">{html.escape(url)} · audited {html.escape(str(result.get("created_at", "")))}</div>
  <div class="badges">Offline · deterministic rules · no API key · no storefront writes</div>
  <div class="hero">
    {_dial(score)}
    <div class="pillars">{_pillar_rows(components)}</div>
  </div>
  {cap_html}
  <div class="actions">
    <button onclick="downloadCard()">Download score card (PNG)</button>
    <button onclick="copyText('jsonld', this)">Copy recommended JSON-LD</button>
  </div>
  <h2>Findings ({issue_line})</h2>
  {_findings_section(findings)}
  {questions_html}
  <h2>Recommended Product JSON-LD</h2>
  <p class="sub">Built only from evidence found on this page or supplied by the merchant.
  Paste it into the page head after review.</p>
  <pre id="jsonld">{html.escape(jsonld_text)}</pre>
  <footer>Generated by CatalogReady. A readiness score never guarantees ranking or citation
  by any AI system. Rule IDs are documented in the repository.</footer>
</main>
{_share_script(share_payload)}
</body>
</html>"""


def _generic_report(result: dict[str, Any]) -> str:
    operation = html.escape(str(result.get("operation", "audit")))
    findings = result.get("findings") or []
    score_rows: list[str] = []
    for name, section in (result.get("scores") or {}).items():
        label = html.escape(name.replace("_", " ").title())
        value = section.get("score")
        rendered = f"{value}/100" if value is not None else html.escape(str(section.get("status", "not_run")))
        score_rows.append(f"<tr><td>{label}</td><td>{rendered}</td></tr>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CatalogReady report · {operation}</title>
<style>{_CSS}</style>
</head>
<body>
<main>
  <div class="brand">CatalogReady · audit report</div>
  <h1>{operation}</h1>
  <h2>Scores</h2>
  <table>{''.join(score_rows)}</table>
  <h2>Findings</h2>
  {_findings_section(findings)}
  <footer>Generated by CatalogReady. A readiness score never guarantees ranking or citation
  by any AI system.</footer>
</main>
</body>
</html>"""


def render_html_report(result: dict[str, Any]) -> str:
    if result.get("operation") == "run_product_readiness_agent":
        return _agent_report(result)
    return _generic_report(result)


__all__ = ["render_html_report"]
