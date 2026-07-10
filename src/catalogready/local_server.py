"""Dependency-free local HTTP adapter for the browser extension.

This is intentionally small and localhost-only. Production deployments should
use ``catalogready-api`` with FastAPI, authentication, and a reverse proxy.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .model_providers import ProviderError, provider_status
from .service import dispatch


MAX_BODY_BYTES = 8 * 1024 * 1024


class CatalogReadyHandler(BaseHTTPRequestHandler):
    server_version = "CatalogReadyLocal/0.4"

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin.startswith(("chrome-extension://", "moz-extension://")) or origin.startswith(
            ("http://127.0.0.1", "http://localhost")
        ):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if length <= 0:
            raise ValueError("A JSON request body is required")
        if length > MAX_BODY_BYTES:
            raise ValueError("Request body exceeds the 8 MB local limit")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object")
        return value

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "catalogready-local"})
        elif path == "/v1/providers":
            self._send_json(HTTPStatus.OK, {"providers": provider_status()})
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        routes = {
            "/v1/agent/html": "run_product_agent_html",
            "/v1/optimize/html": "optimize_product_html",
            "/v1/optimize/csv": "optimize_product_csv",
            "/v1/optimize/evidence": "optimize_product_evidence",
            "/v1/optimize/shopify-payload": "optimize_shopify_payload",
            "/v1/optimize/shopify": "optimize_shopify_live",
        }
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/v1/execute":
                operation = str(body.get("operation", ""))
                arguments = body.get("arguments") or {}
                if not isinstance(arguments, dict):
                    raise ValueError("arguments must be an object")
            elif path in routes:
                operation = routes[path]
                arguments = body
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
                return
            self._send_json(HTTPStatus.OK, dispatch(operation, arguments))
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": str(exc)})
        except ProviderError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"detail": str(exc)})
        except Exception as exc:  # pragma: no cover - final HTTP boundary
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"detail": f"Local server error: {type(exc).__name__}"},
            )

    def log_message(self, format: str, *args: Any) -> None:
        if os.environ.get("CATALOGREADY_QUIET") != "1":
            super().log_message(format, *args)


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), CatalogReadyHandler)
    print(f"CatalogReady local server listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
