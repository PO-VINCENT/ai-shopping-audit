"""HTTP, OpenAPI, and A2A adapters over the shared CatalogReady service."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .model_providers import ProviderError, provider_status
from .service import describe_agent, dispatch


app = FastAPI(
    title="CatalogReady AI",
    version="0.4.0",
    description="Evidence-grounded retail product visibility optimization agent.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension|moz-extension)://.*$|^http://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def _public_url() -> str:
    return os.environ.get("CATALOGREADY_PUBLIC_URL", "http://127.0.0.1:8080").rstrip("/")


def agent_card() -> dict[str, Any]:
    return {
        "protocolVersion": "0.3",
        "name": "CatalogReady AI",
        "description": "Builds evidence-grounded product listings, shopping journeys, claim audits, and AI-visibility measurements.",
        "url": f"{_public_url()}/a2a",
        "version": "0.4.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "product-readiness-agent",
                "name": "Run product readiness agent",
                "description": "Inspects supplied product HTML, plans fixes, asks for missing evidence, and validates reversible changes in memory.",
                "tags": ["retail", "agent", "product-data", "evidence"],
            },
            {
                "id": "audit-catalog",
                "name": "Audit product catalog",
                "description": "Checks required retail feed fields and missing values in a CSV catalog.",
                "tags": ["retail", "ecommerce", "catalog", "seo"],
            },
            {
                "id": "audit-page-html",
                "name": "Audit product page evidence",
                "description": "Checks supplied HTML for indexability, canonical identity, structured data, and textual evidence.",
                "tags": ["seo", "geo", "structured-data"],
            },
            {
                "id": "visibility-prompt-pack",
                "name": "Build AI visibility prompt pack",
                "description": "Creates stable retail prompts for citation and answer-coverage measurement.",
                "tags": ["geo", "ai-visibility", "evaluation"],
            },
            {
                "id": "score-visibility-snapshots",
                "name": "Score recorded AI visibility",
                "description": "Measures citation rate, product mentions, answer support, and competitor share of voice.",
                "tags": ["geo", "citations", "benchmarking"],
            },
            {
                "id": "optimize-product-visibility",
                "name": "Optimize product visibility",
                "description": "Builds a customer journey, evidence-backed listing draft, claim audit, and readiness score.",
                "tags": ["retail", "product", "ai-visibility", "evidence"],
            },
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "catalogready"}


@app.get("/.well-known/agent-card.json")
def get_agent_card() -> dict[str, Any]:
    return agent_card()


@app.get("/v1/capabilities")
def capabilities() -> dict[str, Any]:
    return describe_agent()


@app.get("/v1/providers")
def providers() -> dict[str, Any]:
    return {"providers": provider_status()}


@app.post("/v1/agent/html")
def run_product_agent(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("run_product_agent_html", body)


@app.post("/v1/execute")
def execute(body: dict[str, Any]) -> dict[str, Any]:
    try:
        return dispatch(str(body.get("operation", "")), body.get("arguments") or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _run_operation(operation: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return dispatch(operation, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/optimize/html")
def optimize_html(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("optimize_product_html", body)


@app.post("/v1/optimize/csv")
def optimize_csv(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("optimize_product_csv", body)


@app.post("/v1/optimize/evidence")
def optimize_canonical_evidence(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("optimize_product_evidence", body)


@app.post("/v1/optimize/shopify-payload")
def optimize_shopify_json(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("optimize_shopify_payload", body)


@app.post("/v1/optimize/shopify")
def optimize_shopify_api(body: dict[str, Any]) -> dict[str, Any]:
    return _run_operation("optimize_shopify_live", body)


def _text_from_message(message: dict[str, Any]) -> str:
    parts = message.get("parts") or []
    return "\n".join(
        str(part.get("text", ""))
        for part in parts
        if isinstance(part, dict) and part.get("kind") == "text"
    ).strip()


@app.post("/a2a")
async def a2a(request: Request) -> dict[str, Any]:
    body = await request.json()
    request_id = body.get("id")
    if body.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}
    if body.get("method") != "message/send":
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

    params = body.get("params") or {}
    message = params.get("message") or {}
    metadata = params.get("metadata") or {}
    operation = str(metadata.get("operation", "describe"))
    arguments = metadata.get("arguments") or {}
    if operation == "describe":
        text = _text_from_message(message).lower()
        if "prompt" in text and metadata.get("domain") and metadata.get("category"):
            operation = "build_visibility_prompt_pack"
            arguments = {
                "domain": metadata["domain"],
                "category": metadata["category"],
                "market": metadata.get("market", "en-AU"),
            }
    try:
        result = dispatch(operation, arguments)
    except (ValueError, ProviderError) as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}

    context_id = message.get("contextId") or str(uuid4())
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "messageId": str(uuid4()),
            "contextId": context_id,
            "role": "agent",
            "parts": [
                {
                    "kind": "text",
                    "text": f"CatalogReady completed `{operation}`. Structured evidence is attached in metadata.",
                }
            ],
            "kind": "message",
            "metadata": {"catalogready": result},
        },
    }


def main() -> None:
    uvicorn.run(
        "catalogready.api_server:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
