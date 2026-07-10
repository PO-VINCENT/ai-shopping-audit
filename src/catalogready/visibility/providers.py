"""Provider boundary for live or recorded visibility observations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol


class VisibilityProvider(Protocol):
    name: str

    def observe(self, prompts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return timestamped responses for the supplied prompt records."""


class RecordedResponseProvider:
    """Deterministic provider used by examples, CI, and offline development."""

    name = "recorded"

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses

    def observe(self, prompts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed_ids = {str(prompt.get("id", "")) for prompt in prompts}
        return [response for response in self._responses if str(response.get("prompt_id", "")) in allowed_ids]

