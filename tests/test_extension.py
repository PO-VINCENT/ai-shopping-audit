from __future__ import annotations

import json
import unittest
from pathlib import Path

_EXTENSION_DIR = Path(__file__).resolve().parents[1] / "browser-extension"


class ExtensionTests(unittest.TestCase):
    def test_manifest_is_mv3_with_minimal_permissions(self) -> None:
        manifest = json.loads((_EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["version"], "0.8.1")
        self.assertLessEqual(len(manifest["description"]), 132)
        self.assertEqual(set(manifest["permissions"]), {"activeTab", "scripting", "storage"})
        # Host permissions must stay local-only: the page HTML never leaves the machine.
        for host in manifest["host_permissions"]:
            self.assertTrue(
                host.startswith(("http://127.0.0.1", "http://localhost")),
                f"non-local host permission: {host}",
            )

    def test_popup_calls_no_external_origins(self) -> None:
        for filename in ("popup.html", "popup.js", "popup.css", "i18n.js"):
            content = (_EXTENSION_DIR / filename).read_text(encoding="utf-8")
            self.assertNotIn("https://cdn", content)
            self.assertNotIn('src="http', content)
            self.assertNotIn("@import", content)

    def test_i18n_covers_every_static_key(self) -> None:
        import re

        content = (_EXTENSION_DIR / "i18n.js").read_text(encoding="utf-8")
        html = (_EXTENSION_DIR / "popup.html").read_text(encoding="utf-8")
        for key in set(re.findall(r'data-i18n(?:-placeholder)?="([a-zA-Z]+)"', html)):
            self.assertIn(f"{key}:", content, f"missing i18n key: {key}")
        self.assertEqual(content.count("pillars: {"), 2)
        self.assertEqual(content.count("checks: {"), 2)

    def test_popup_never_handles_api_keys(self) -> None:
        content = (_EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")
        lowered = content.lower()
        self.assertNotIn("api_key", lowered)
        self.assertNotIn("apikey", lowered)
        # Stored settings are limited to server URL, provider name, and model ID.
        self.assertIn('chrome.storage.local.set', content)
        self.assertNotIn("key:", lowered)

    def test_popup_renders_latest_platform_and_deduction_contract(self) -> None:
        script = (_EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")
        css = (_EXTENSION_DIR / "popup.css").read_text(encoding="utf-8")
        html = (_EXTENSION_DIR / "popup.html").read_text(encoding="utf-8")
        self.assertIn('id="score-breakdown"', html)
        self.assertIn('id="platform-scores"', html)
        self.assertIn("deduction_items", script)
        self.assertIn("platform_scores", script)
        for platform in ("comprehensive", "openai", "google", "microsoft", "anthropic", "perplexity"):
            self.assertIn(f'"{platform}"', script)
        self.assertIn('data-platform="${platform}"', script)
        self.assertIn("state.scorePlatform", script)
        self.assertIn(".platform-card.is-active", css)
        self.assertIn("#jsonld-wrap { min-width: 0; max-width: 100%; }", css)


if __name__ == "__main__":
    unittest.main()
