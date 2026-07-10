"""Recorded visibility snapshot loading and normalization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .citations import citation_domains, extract_urls


def load_snapshots(snapshot_path: str) -> list[dict[str, Any]]:
    path = Path(snapshot_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Snapshot file does not exist: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        parsed = parsed.get("observations", [])
    if not isinstance(parsed, list):
        raise ValueError("Snapshot JSON must be a list or contain an observations list.")
    return [item for item in parsed if isinstance(item, dict)]


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    response_text = str(snapshot.get("response", snapshot.get("answer", "")))
    citations = snapshot.get("citations")
    if not isinstance(citations, list):
        citations = extract_urls(response_text)
    citations = [str(url) for url in citations]
    return {
        "prompt_id": str(snapshot.get("prompt_id", "")),
        "provider": str(snapshot.get("provider", "unknown")),
        "checked_at": snapshot.get("checked_at"),
        "response": response_text,
        "citations": citations,
        "citation_domains": citation_domains(citations),
        "product_mentioned": bool(snapshot.get("product_mentioned", False)),
        "answer_supported": snapshot.get("answer_supported"),
    }

