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
        for filename in ("index.html", "app.js", "i18n.js", "styles.css"):
            content = (_DASHBOARD_DIR / filename).read_text(encoding="utf-8")
            self.assertNotIn("https://cdn", content)
            self.assertNotIn("src=\"http", content)
            self.assertNotIn("@import", content)

    def test_i18n_languages_cover_the_same_keys(self) -> None:
        import re

        content = (_DASHBOARD_DIR / "i18n.js").read_text(encoding="utf-8")
        html = (_DASHBOARD_DIR / "index.html").read_text(encoding="utf-8")
        # Every static key referenced in the HTML must exist in the dictionary.
        for key in set(re.findall(r'data-i18n(?:-placeholder|-title)?="([a-zA-Z]+)"', html)):
            self.assertIn(f"{key}:", content, f"missing i18n key: {key}")
        # Both languages must define the pillar tables.
        self.assertEqual(content.count("pillars: {"), 2)
        self.assertEqual(content.count("pillarExplain: {"), 2)
        self.assertEqual(content.count("checks: {"), 2)

    def test_health_payload_reports_version_and_staleness(self) -> None:
        from catalogready.local_server import health_payload

        payload = health_payload()
        self.assertEqual(payload["status"], "ok")
        self.assertRegex(payload["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("started_at", payload)
        # Source files were written after this test process imported the
        # module only in dev flows; the flag must at least be a boolean.
        self.assertIsInstance(payload["stale"], bool)

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
