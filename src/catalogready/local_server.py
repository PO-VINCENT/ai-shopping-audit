"""Dependency-free local HTTP adapter and dashboard host.

Serves the packaged interactive dashboard at ``/`` and the JSON API under
``/v1``. This is intentionally small and localhost-only. Production
deployments should use ``catalogready-api`` with FastAPI, authentication,
and a reverse proxy.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .model_providers import ProviderError, provider_status
from .service import dispatch
from .env import load_local_env


MAX_BODY_BYTES = 8 * 1024 * 1024

_DASHBOARD_DIR = Path(__file__).parent / "dashboard"
_STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


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

    def _send_static(self, filename: str, content_type: str) -> None:
        file_path = _DASHBOARD_DIR / filename
        if not file_path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Dashboard asset missing"})
            return
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        path = urlparse(self.path).path
        if path in _STATIC_FILES:
            filename, content_type = _STATIC_FILES[path]
            self._send_static(filename, content_type)
        elif path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "catalogready-local"})
        elif path == "/v1/providers":
            self._send_json(HTTPStatus.OK, {"providers": provider_status()})
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        routes = {
            "/v1/agent/html": "run_product_agent_html",
            "/v1/report/html": "render_html_report",
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


def main(open_browser: bool = False) -> None:
    load_local_env()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), CatalogReadyHandler)
    address = f"http://{host}:{port}"
    print(f"CatalogReady dashboard and local API listening on {address}", flush=True)
    if open_browser:
        import threading
        import webbrowser

        threading.Timer(0.4, webbrowser.open, args=(address,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
