from __future__ import annotations

import json
import unittest
from pathlib import Path

_EXTENSION_DIR = Path(__file__).resolve().parents[1] / "browser-extension"


class ExtensionTests(unittest.TestCase):
    def test_manifest_is_mv3_with_minimal_permissions(self) -> None:
        manifest = json.loads((_EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(set(manifest["permissions"]), {"activeTab", "scripting", "storage"})
        # Host permissions must stay local-only: the page HTML never leaves the machine.
        for host in manifest["host_permissions"]:
            self.assertTrue(
                host.startswith(("http://127.0.0.1", "http://localhost")),
                f"non-local host permission: {host}",
            )

    def test_popup_calls_no_external_origins(self) -> None:
        for filename in ("popup.html", "popup.js", "popup.css"):
            content = (_EXTENSION_DIR / filename).read_text(encoding="utf-8")
            self.assertNotIn("https://cdn", content)
            self.assertNotIn('src="http', content)
            self.assertNotIn("@import", content)

    def test_popup_never_handles_api_keys(self) -> None:
        content = (_EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")
        lowered = content.lower()
        self.assertNotIn("api_key", lowered)
        self.assertNotIn("apikey", lowered)
        # Stored settings are limited to server URL, provider name, and model ID.
        self.assertIn('chrome.storage.local.set', content)
        self.assertNotIn("key:", lowered)


if __name__ == "__main__":
    unittest.main()
