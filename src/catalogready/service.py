"""Stable application facade shared by CLI, MCP, HTTP, and A2A adapters."""

from __future__ import annotations

import json
from typing import Any

from .agent import run_product_agent_html
from .catalog.scoring import audit_catalog
from .discovery.scoring import audit_discovery_bundle, audit_page_html
from .model_providers import provider_status
from .optimization.pipeline import (
    optimize_evidence,
    optimize_product_csv,
    optimize_product_html,
    optimize_shopify_live,
    optimize_shopify_payload,
)
from .qa import answer_audit_question
from .reporting.html import render_html_report
from .reporting.render import render_markdown_report
from .visibility.metrics import score_visibility_snapshots
from .visibility.prompt_packs import build_visibility_prompt_pack


def describe_agent() -> dict[str, Any]:
    return {
        "name": "CatalogReady AI",
        "version": "0.7.0",
        "capabilities": [
            "run_product_readiness_agent",
            "audit_catalog",
            "audit_page_html",
            "audit_discovery_bundle",
            "build_visibility_prompt_pack",
            "score_visibility_snapshots",
            "render_markdown_report",
            "render_html_report",
            "answer_audit_question",
            "optimize_product_html",
            "optimize_product_csv",
            "optimize_shopify_payload",
            "optimize_shopify_live",
            "list_model_providers",
        ],
        "protocols": ["CLI", "MCP", "HTTP/OpenAPI", "A2A 0.3 JSON-RPC"],
        "constraints": [
            "No live crawling in the deterministic core",
            "No model-provider calls in the deterministic test path",
            "No ranking or citation guarantees",
            "Generated product claims require merchant approval",
            "Provider API keys remain server-side",
        ],
    }


def _optimization_options(arguments: dict[str, Any]) -> dict[str, Any]:
    target_types = arguments.get("target_customer_types")
    if target_types is not None and not isinstance(target_types, list):
        raise ValueError("target_customer_types must be an array")
    return {
        "provider_name": str(arguments.get("provider", "deterministic")),
        "model": str(arguments.get("model", "")),
        "evaluator_provider_name": str(arguments.get("evaluator_provider", "")),
        "evaluator_model": str(arguments.get("evaluator_model", "")),
        "market": str(arguments.get("market", "en-AU")),
        "target_customer_types": target_types,
    }


def _agent_options(arguments: dict[str, Any]) -> dict[str, Any]:
    merchant_answers = arguments.get("merchant_answers")
    if merchant_answers is not None and not isinstance(merchant_answers, dict):
        raise ValueError("merchant_answers must be an object")
    return {
        "mode": str(arguments.get("mode", "audit")),
        "provider_name": str(arguments.get("provider", "deterministic")),
        "model": str(arguments.get("model", "")),
        "merchant_answers": merchant_answers,
        "resumed_from": str(arguments.get("resumed_from", "")),
    }


def dispatch(operation: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    if operation == "describe":
        return describe_agent()
    if operation == "list_model_providers":
        return {"providers": provider_status()}
    if operation == "run_product_agent_html":
        return run_product_agent_html(
            str(arguments.get("url", "")),
            str(arguments.get("html", "")),
            **_agent_options(arguments),
        )
    if operation == "audit_catalog":
        return audit_catalog(str(arguments.get("catalog_path", "")))
    if operation == "audit_page_html":
        return audit_page_html(str(arguments.get("url", "")), str(arguments.get("html", "")))
    if operation == "audit_discovery_bundle":
        return audit_discovery_bundle(
            str(arguments.get("url", "")),
            str(arguments.get("html", "")),
            str(arguments.get("robots_txt", "")),
            str(arguments.get("sitemap_xml", "")),
        )
    if operation == "build_visibility_prompt_pack":
        return build_visibility_prompt_pack(
            str(arguments.get("domain", "")),
            str(arguments.get("category", "")),
            str(arguments.get("market", "en-AU")),
        )
    if operation == "score_visibility_snapshots":
        return score_visibility_snapshots(
            str(arguments.get("snapshot_path", "")),
            str(arguments.get("target_domain", "")),
        )
    if operation == "render_markdown_report":
        audit_result = arguments.get("audit_result")
        if not isinstance(audit_result, dict):
            raise ValueError("audit_result must be an object")
        return {
            "schema_version": "1.0",
            "operation": "render_markdown_report",
            "markdown": render_markdown_report(audit_result),
        }
    if operation == "render_html_report":
        audit_result = arguments.get("audit_result")
        if not isinstance(audit_result, dict):
            raise ValueError("audit_result must be an object")
        return {
            "schema_version": "1.0",
            "operation": "render_html_report",
            "html": render_html_report(audit_result),
        }
    if operation == "answer_audit_question":
        audit_result = arguments.get("audit_result")
        if not isinstance(audit_result, dict):
            raise ValueError("audit_result must be an object")
        return answer_audit_question(
            audit_result,
            str(arguments.get("question", "")),
            provider_name=str(arguments.get("provider", "deterministic")),
            model=str(arguments.get("model", "")),
        )
    if operation == "optimize_product_html":
        return optimize_product_html(
            str(arguments.get("url", "")),
            str(arguments.get("html", "")),
            **_optimization_options(arguments),
        )
    if operation == "optimize_product_csv":
        return optimize_product_csv(
            str(arguments.get("csv_text", "")),
            int(arguments.get("row_index", 0)),
            **_optimization_options(arguments),
        )
    if operation == "optimize_product_evidence":
        evidence_record = arguments.get("evidence_record")
        if not isinstance(evidence_record, dict):
            raise ValueError("evidence_record must be an object")
        return optimize_evidence(evidence_record, **_optimization_options(arguments))
    if operation == "optimize_shopify_payload":
        product_data = arguments.get("product_data")
        if not isinstance(product_data, dict):
            raise ValueError("product_data must be an object")
        return optimize_shopify_payload(
            product_data,
            str(arguments.get("shop_domain", "")),
            **_optimization_options(arguments),
        )
    if operation == "optimize_shopify_live":
        return optimize_shopify_live(
            str(arguments.get("shop_domain", "")),
            str(arguments.get("product_query", "")),
            **_optimization_options(arguments),
        )
    raise ValueError(f"Unsupported operation: {operation}")


def dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


__all__ = [
    "answer_audit_question",
    "audit_catalog",
    "audit_discovery_bundle",
    "audit_page_html",
    "build_visibility_prompt_pack",
    "describe_agent",
    "dispatch",
    "dumps",
    "optimize_evidence",
    "optimize_product_csv",
    "optimize_product_html",
    "optimize_shopify_live",
    "optimize_shopify_payload",
    "provider_status",
    "run_product_agent_html",
    "render_html_report",
    "render_markdown_report",
    "score_visibility_snapshots",
]
