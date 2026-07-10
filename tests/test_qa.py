from __future__ import annotations

import unittest

from catalogready.qa import answer_audit_question, deterministic_answer
from catalogready.service import dispatch


def _audit_result() -> dict:
    return dispatch(
        "run_product_agent_html",
        {
            "url": "https://example.com/lamp",
            "html": "<html><head><title>Desk Lamp</title></head><body>Desk lamp</body></html>",
        },
    )


class AuditQATests(unittest.TestCase):
    def test_pillar_question_lists_checks(self) -> None:
        answer = deterministic_answer(_audit_result(), "why is structured data low?")
        self.assertIn("Structured data:", answer)
        self.assertIn("✗", answer)

    def test_fix_question_returns_prioritized_plan(self) -> None:
        answer = deterministic_answer(_audit_result(), "what should I fix first?")
        self.assertIn("Highest-priority actions", answer)
        self.assertIn("1.", answer)

    def test_score_question_includes_caps(self) -> None:
        answer = deterministic_answer(_audit_result(), "why is the score low?")
        self.assertIn("CatalogReady Score:", answer)
        self.assertIn("capped", answer)

    def test_dispatch_operation_stays_deterministic_offline(self) -> None:
        result = dispatch(
            "answer_audit_question",
            {"audit_result": _audit_result(), "question": "list the findings"},
        )
        self.assertEqual(result["operation"], "answer_audit_question")
        self.assertEqual(result["mode"], "deterministic")
        self.assertIn("AGENT-", result["answer"])

    def test_empty_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            answer_audit_question({}, "why?")
        with self.assertRaises(ValueError):
            answer_audit_question(_audit_result(), "")


if __name__ == "__main__":
    unittest.main()
