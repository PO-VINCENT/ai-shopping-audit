from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from catalogready.chat import ChatSession


LAMP_HTML = """
<html><head><title>Desk Lamp</title><script type="application/ld+json">
{"@type":"Product","name":"Desk Lamp",
"offers":{"price":"49","priceCurrency":"AUD"}}
</script></head><body>Compact desk lamp.</body></html>
"""


class ChatSessionTests(unittest.TestCase):
    def _audit(self, session: ChatSession) -> str:
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "lamp.html"
            page.write_text(LAMP_HTML, encoding="utf-8")
            return session.handle(f"/audit https://example.com/lamp {page}")

    def test_audit_command_runs_offline_and_shows_score(self) -> None:
        session = ChatSession()
        output = self._audit(session)
        self.assertIn("CatalogReady Score:", output)
        self.assertIn("inspect_product_page", output)
        # Missing sku and availability -> blocking questions surface immediately.
        self.assertIn("blocking", output)

    def test_answers_clear_blocking_questions_and_draft_validates_gain(self) -> None:
        session = ChatSession()
        self._audit(session)
        before = session.result["readiness"]["before"]["score"]
        output = session.handle("/answers sku=LAMP-1 availability=in_stock")
        self.assertIn("CatalogReady Score:", output)
        blocking = [
            item
            for item in session.result["merchant_questions"]
            if item.get("blocking")
        ]
        self.assertEqual(blocking, [])
        draft_output = session.handle("/draft")
        self.assertIn("reversible change", draft_output)
        validation = session.result["validation"]
        self.assertGreater(validation["after_score"], before)

    def test_free_text_pillar_question_is_answered_deterministically(self) -> None:
        session = ChatSession()
        self._audit(session)
        output = session.handle("why is structured data low?")
        self.assertIn("Structured data:", output)
        self.assertIn("✗", output)

    def test_fix_question_returns_prioritized_plan(self) -> None:
        session = ChatSession()
        self._audit(session)
        output = session.handle("what should I fix first?")
        self.assertIn("1.", output)

    def test_report_and_jsonld_exports(self) -> None:
        session = ChatSession()
        self._audit(session)
        self.assertIn('"@type": "Product"', session.handle("/jsonld"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.html"
            self.assertIn(str(path), session.handle(f"/report {path}"))
            self.assertIn("<!doctype html>", path.read_text(encoding="utf-8"))

    def test_unknown_command_and_empty_state_are_guided(self) -> None:
        session = ChatSession()
        self.assertIn("/audit", session.handle("/score"))
        self.assertIn("Unknown command", session.handle("/nonsense"))
        self.assertIn("/audit", session.handle("hello"))

    def test_quit_raises_eof(self) -> None:
        session = ChatSession()
        with self.assertRaises(EOFError):
            session.handle("/quit")


if __name__ == "__main__":
    unittest.main()
