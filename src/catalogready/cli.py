"""Command-line adapter for CatalogReady."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from .reporting.html import PILLAR_LABELS, render_html_report
from .service import (
    audit_catalog,
    audit_discovery_bundle,
    audit_page_html,
    build_visibility_prompt_pack,
    describe_agent,
    dumps,
    optimize_product_csv,
    optimize_product_html,
    optimize_shopify_live,
    provider_status,
    render_markdown_report,
    run_product_agent_html,
    score_visibility_snapshots,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catalogready")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit",
        help="Audit one product page: score, findings, and an HTML report",
    )
    audit.add_argument("url", help="Product page URL")
    audit.add_argument(
        "html_file",
        nargs="?",
        help="Optional saved HTML file; when omitted, the page is fetched once",
    )
    audit.add_argument(
        "--report",
        default="catalogready-report.html",
        help="Where to write the HTML report (default: catalogready-report.html)",
    )
    audit.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON result instead of the score card",
    )

    catalog = subparsers.add_parser("catalog", help="Audit a CSV product catalog")
    catalog.add_argument("catalog_path")

    page = subparsers.add_parser("page", help="Audit supplied product-page HTML")
    page.add_argument("url")
    page.add_argument("html_file")

    discovery = subparsers.add_parser("discovery", help="Audit HTML, robots.txt, and sitemap XML")
    discovery.add_argument("url")
    discovery.add_argument("html_file")
    discovery.add_argument("--robots")
    discovery.add_argument("--sitemap")

    prompts = subparsers.add_parser("prompts", help="Build an AI-visibility prompt pack")
    prompts.add_argument("--domain", required=True)
    prompts.add_argument("--category", required=True)
    prompts.add_argument("--market", default="en-AU")

    visibility = subparsers.add_parser("visibility", help="Score recorded visibility observations")
    visibility.add_argument("snapshot_path")
    visibility.add_argument("--domain", required=True)

    report = subparsers.add_parser("report", help="Render an audit JSON file as Markdown")
    report.add_argument("audit_result_path")

    agent = subparsers.add_parser(
        "agent",
        help="Run the bounded product-readiness agent over supplied HTML",
    )
    agent.add_argument("url")
    agent.add_argument("html_file")
    agent.add_argument("--mode", choices=["audit", "draft"], default="audit")
    agent.add_argument(
        "--provider",
        choices=["deterministic", "openai", "gemini", "anthropic", "claude", "deepseek"],
        default="deterministic",
    )
    agent.add_argument("--model", default="")
    agent.add_argument(
        "--answers",
        help="Optional JSON object containing verified merchant answers",
    )
    agent.add_argument(
        "--resumed-from",
        default="",
        help="Optional prior agent run ID for traceability",
    )

    optimize_html = subparsers.add_parser(
        "optimize-html",
        help="Optimize a supplied product page with evidence-backed claims",
    )
    optimize_html.add_argument("url")
    optimize_html.add_argument("html_file")
    _add_provider_arguments(optimize_html)

    optimize_csv = subparsers.add_parser(
        "optimize-csv",
        help="Optimize one product row from a CSV file",
    )
    optimize_csv.add_argument("csv_file")
    optimize_csv.add_argument("--row", type=int, default=0)
    _add_provider_arguments(optimize_csv)

    optimize_shopify = subparsers.add_parser(
        "optimize-shopify",
        help="Read one Shopify product through Admin GraphQL and optimize it",
    )
    optimize_shopify.add_argument("shop_domain")
    optimize_shopify.add_argument("product_query")
    _add_provider_arguments(optimize_shopify)

    subparsers.add_parser("providers", help="Show configured BYO model providers")

    subparsers.add_parser("describe", help="Describe agent capabilities")
    return parser


def _add_provider_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["deterministic", "openai", "gemini", "anthropic", "claude", "deepseek"],
        default="deterministic",
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--market", default="en-AU")
    parser.add_argument(
        "--customer-type",
        action="append",
        dest="customer_types",
        help="Optional customer type ID; repeat up to three times",
    )


def _provider_options(args: argparse.Namespace) -> dict:
    return {
        "provider_name": args.provider,
        "model": args.model,
        "market": args.market,
        "target_customer_types": args.customer_types,
    }


def _read_optional(path: str | None) -> str:
    return Path(path).read_text(encoding="utf-8") if path else ""


_FETCH_LIMIT_BYTES = 2_000_000


def _fetch_page(url: str) -> str:
    """Fetch one product page. The CLI's only network call; the core stays offline."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CatalogReady/0.5 product-page audit (single request)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(_FETCH_LIMIT_BYTES).decode(charset, errors="replace")


def _score_card(result: dict, report_path: Path) -> str:
    readiness = (result.get("readiness") or {}).get("before") or {}
    product = (result.get("evidence_record") or {}).get("product") or {}
    findings = result.get("findings") or []
    counts = {
        severity: sum(1 for item in findings if item.get("severity") == severity)
        for severity in ("high", "medium", "low")
    }
    lines = [
        "",
        f"  {product.get('title') or (result.get('input') or {}).get('url', 'Product page')}",
        "",
        f"  CatalogReady Score: {readiness.get('score', 0)}/100 ({readiness.get('status', 'unknown')})",
        "",
    ]
    for key, section in (readiness.get("components") or {}).items():
        label = PILLAR_LABELS.get(key, key.replace("_", " ").title())
        lines.append(f"  {label:<20} {section.get('score', 0):>3}/{section.get('max_score', 0)}")
    for reason in readiness.get("cap_reasons") or []:
        lines.append(f"  ! Score capped at {readiness.get('safety_cap')}: {reason}")
    lines.extend(
        [
            "",
            f"  {counts['high']} critical · {counts['medium']} recommended · {counts['low']} minor findings",
            f"  Full report: {report_path}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0].startswith(("http://", "https://")):
        argv = ["audit", *argv]
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        else:
            print(f"Fetching {args.url} (single request) ...", file=sys.stderr)
            html = _fetch_page(args.url)
        result = run_product_agent_html(args.url, html, mode="audit")
        report_path = Path(args.report)
        report_path.write_text(render_html_report(result), encoding="utf-8")
        output = dumps(result) if args.json else _score_card(result, report_path)
    elif args.command == "catalog":
        output = dumps(audit_catalog(args.catalog_path))
    elif args.command == "page":
        html = Path(args.html_file).read_text(encoding="utf-8")
        output = dumps(audit_page_html(args.url, html))
    elif args.command == "discovery":
        output = dumps(
            audit_discovery_bundle(
                args.url,
                Path(args.html_file).read_text(encoding="utf-8"),
                _read_optional(args.robots),
                _read_optional(args.sitemap),
            )
        )
    elif args.command == "prompts":
        output = dumps(build_visibility_prompt_pack(args.domain, args.category, args.market))
    elif args.command == "visibility":
        output = dumps(score_visibility_snapshots(args.snapshot_path, args.domain))
    elif args.command == "report":
        audit_result = json.loads(Path(args.audit_result_path).read_text(encoding="utf-8"))
        output = render_markdown_report(audit_result)
    elif args.command == "agent":
        merchant_answers = None
        if args.answers:
            merchant_answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
            if not isinstance(merchant_answers, dict):
                raise ValueError("--answers must contain a JSON object")
        output = dumps(
            run_product_agent_html(
                args.url,
                Path(args.html_file).read_text(encoding="utf-8"),
                mode=args.mode,
                provider_name=args.provider,
                model=args.model,
                merchant_answers=merchant_answers,
                resumed_from=args.resumed_from,
            )
        )
    elif args.command == "optimize-html":
        output = dumps(
            optimize_product_html(
                args.url,
                Path(args.html_file).read_text(encoding="utf-8"),
                **_provider_options(args),
            )
        )
    elif args.command == "optimize-csv":
        output = dumps(
            optimize_product_csv(
                Path(args.csv_file).read_text(encoding="utf-8"),
                args.row,
                **_provider_options(args),
            )
        )
    elif args.command == "optimize-shopify":
        output = dumps(
            optimize_shopify_live(
                args.shop_domain,
                args.product_query,
                **_provider_options(args),
            )
        )
    elif args.command == "providers":
        output = dumps({"providers": provider_status()})
    else:
        output = dumps(describe_agent())
    print(output, end="" if output.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
