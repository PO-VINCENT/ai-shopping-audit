from __future__ import annotations

import unittest
from pathlib import Path

from catalogready.visibility.citations import extract_urls
from catalogready.visibility.metrics import score_visibility_snapshots


class VisibilityMetricTests(unittest.TestCase):
    def test_recorded_visibility_metrics(self) -> None:
        snapshot = Path(__file__).resolve().parents[1] / "examples" / "recorded-responses" / "sample.json"
        result = score_visibility_snapshots(str(snapshot), "example.com")
        self.assertEqual(result["scores"]["observed_ai_visibility"]["score"], 50)
        self.assertEqual(result["summary"]["product_mention_rate"], 50)
        self.assertEqual(result["summary"]["answer_support_rate"], 75)
        self.assertEqual(result["summary"]["observations"], 4)

    def test_extracts_unique_urls(self) -> None:
        urls = extract_urls("See https://example.com/a and https://example.com/a.")
        self.assertEqual(urls, ["https://example.com/a"])

