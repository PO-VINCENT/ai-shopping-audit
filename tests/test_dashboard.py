from __future__ import annotations

import unittest

from catalogready.local_server import _DASHBOARD_DIR, _STATIC_FILES, fetch_url_payload
from catalogready.service import dispatch


class DashboardTests(unittest.TestCase):
    def test_packaged_dashboard_assets_exist(self) -> None:
        for path, (filename, content_type) in _STATIC_FILES.items():
            with self.subTest(path=path):
                asset = _DASHBOARD_DIR / filename
                self.assertTrue(asset.is_file(), f"missing dashboard asset: {asset}")
                self.assertTrue(content_type.startswith("text/"))

    def test_dashboard_calls_no_external_origins(self) -> None:
        for filename in ("index.html", "app.js", "styles.css"):
            content = (_DASHBOARD_DIR / filename).read_text(encoding="utf-8")
            self.assertNotIn("https://cdn", content)
            self.assertNotIn("src=\"http", content)
            self.assertNotIn("@import", content)

    def test_fetch_route_rejects_non_http_schemes(self) -> None:
        for url in ("file:///etc/passwd", "ftp://example.com/x", "javascript:alert(1)", ""):
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch_url_payload(url)

    def test_report_route_operation_renders_html(self) -> None:
        agent_result = dispatch(
            "run_product_agent_html",
            {
                "url": "https://example.com/lamp",
                "html": "<html><head><title>Lamp</title></head><body>Lamp</body></html>",
            },
        )
        rendered = dispatch("render_html_report", {"audit_result": agent_result})
        self.assertEqual(rendered["operation"], "render_html_report")
        self.assertIn("<!doctype html>", rendered["html"])


if __name__ == "__main__":
    unittest.main()
