"""Audit a list of product URLs and write a benchmark table.

Launch-content generator: feeds real store pages through the same audit
the CLI runs and emits a Markdown table sorted by score. Network use is
one GET per URL with a polite delay — run it deliberately, never in CI.

Usage:
    uv run python scripts/benchmark.py urls.txt BENCHMARK.md
    # urls.txt: one product URL per line, '#' comments allowed
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from catalogready.fetch import fetch_page  # noqa: E402
from catalogready.service import run_product_agent_html  # noqa: E402

DELAY_SECONDS = 3.0

_BOT_WALL_MARKERS = (
    "pardon our interruption",
    "access denied",
    "are you a robot",
    "attention required",
    "just a moment",
    "verify you are human",
)


def audit_url(url: str) -> dict:
    html = fetch_page(url)
    lowered = html.lower()
    if any(marker in lowered for marker in _BOT_WALL_MARKERS):
        return {"url": url, "status": "bot_blocked"}
    result = run_product_agent_html(url, html, mode="audit")
    readiness = result["readiness"]["before"]
    findings = result["findings"]
    top = next((f for f in findings if f["severity"] == "high"), findings[0] if findings else None)
    return {
        "url": url,
        "status": "ok",
        "score": readiness["score"],
        "state": readiness["status"],
        "caps": "; ".join(readiness["cap_reasons"]),
        "high": sum(1 for f in findings if f["severity"] == "high"),
        "findings": len(findings),
        "top_finding": f"{top['rule_id']}: {top['title']}" if top else "—",
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    urls = [
        line.strip()
        for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    rows = []
    for index, url in enumerate(urls, 1):
        domain = urlparse(url).hostname or url
        print(f"[{index}/{len(urls)}] {domain} ...", flush=True)
        try:
            rows.append(audit_url(url))
        except Exception as error:  # noqa: BLE001 - keep the sweep going
            rows.append({"url": url, "status": f"error: {type(error).__name__}"})
        time.sleep(DELAY_SECONDS)

    audited = [row for row in rows if row["status"] == "ok"]
    audited.sort(key=lambda row: row["score"])
    skipped = [row for row in rows if row["status"] != "ok"]

    lines = [
        "# CatalogReady benchmark",
        "",
        f"{len(audited)} product pages audited; {len(skipped)} unreachable or bot-blocked.",
        "Methodology: one GET per page, deterministic rules only (no model),",
        "same audit as `catalogready <url>`. See docs/scoring-methodology.md.",
        "",
        "| Store | Score | Status | High | Findings | Top issue |",
        "|---|---|---|---|---|---|",
    ]
    for row in audited:
        domain = urlparse(row["url"]).hostname.removeprefix("www.")
        lines.append(
            f"| [{domain}]({row['url']}) | **{row['score']}** | {row['state']} "
            f"| {row['high']} | {row['findings']} | {row['top_finding']} |"
        )
    if skipped:
        lines.extend(["", "Skipped: " + ", ".join(
            f"{urlparse(row['url']).hostname} ({row['status']})" for row in skipped
        )])
    ready = sum(1 for row in audited if row["state"] == "ready")
    if audited:
        lines.extend([
            "",
            f"**{len(audited) - ready} of {len(audited)} pages "
            f"({round(100 * (len(audited) - ready) / len(audited))}%) are not ready "
            "for AI shopping agents.**",
        ])
    Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()
