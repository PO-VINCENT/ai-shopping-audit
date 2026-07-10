"""Vendor-neutral JSON generation over provider REST APIs.

API keys are read from server-side environment variables. They are never
accepted in agent tool arguments or browser-extension requests.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """A safe provider error that does not expose credentials."""


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class JsonModelProvider(Protocol):
    name: str
    model: str

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


def _http_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed provider URLs
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise ProviderError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc


def _json_from_text(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("Provider did not return a JSON object")
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ProviderError("Provider returned malformed JSON") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("Provider JSON output must be an object")
    return parsed


@dataclass
class _BaseProvider:
    model: str
    api_key: str
    transport: Transport = _http_json
    timeout: float = 90.0

    def _require(self) -> None:
        if not self.model.strip():
            raise ProviderError("A model ID is required for live model providers")
        if not self.api_key.strip():
            raise ProviderError(f"Missing API key for {self.name}")


class OpenAIProvider(_BaseProvider):
    name = "openai"

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require()
        text_format: dict[str, Any] = {"type": "text"}
        if schema:
            text_format = {
                "type": "json_schema",
                "name": "catalogready_product_optimization",
                "strict": True,
                "schema": schema,
            }
        response = self.transport(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "instructions": system,
                "input": user,
                "text": {"format": text_format},
                "store": False,
            },
            self.timeout,
        )
        chunks: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    chunks.append(str(content.get("text", "")))
        return _json_from_text("\n".join(chunks))


class GeminiProvider(_BaseProvider):
    name = "gemini"

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require()
        generation_config: dict[str, Any] = {"responseMimeType": "application/json"}
        if schema:
            generation_config["responseJsonSchema"] = schema
        response = self.transport(
            f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent",
            {"x-goog-api-key": self.api_key},
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": generation_config,
            },
            self.timeout,
        )
        candidates = response.get("candidates") or []
        if not candidates:
            raise ProviderError("Gemini returned no candidates")
        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        return _json_from_text("\n".join(str(part.get("text", "")) for part in parts))


class AnthropicProvider(_BaseProvider):
    name = "anthropic"

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require()
        schema_instruction = ""
        if schema:
            schema_instruction = f"\nReturn JSON matching this JSON Schema:\n{json.dumps(schema)}"
        response = self.transport(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            {
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": [
                    {"role": "user", "content": user + schema_instruction}
                ],
            },
            self.timeout,
        )
        chunks = [
            str(block.get("text", ""))
            for block in response.get("content") or []
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return _json_from_text("\n".join(chunks))


class DeepSeekProvider(_BaseProvider):
    name = "deepseek"

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require()
        schema_instruction = ""
        if schema:
            schema_instruction = f"\nReturn JSON matching this JSON Schema:\n{json.dumps(schema)}"
        response = self.transport(
            "https://api.deepseek.com/chat/completions",
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user + schema_instruction},
                ],
                "response_format": {"type": "json_object"},
                "stream": False,
            },
            self.timeout,
        )
        choices = response.get("choices") or []
        if not choices:
            raise ProviderError("DeepSeek returned no choices")
        return _json_from_text(str((choices[0].get("message") or {}).get("content", "")))


_PROVIDER_ENV = {
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"),
}


def provider_status() -> list[dict[str, Any]]:
    status = [
        {
            "provider": "deterministic",
            "configured": True,
            "api_key_configured": False,
            "default_model_configured": True,
            "model": "offline",
            "api_key_env": None,
            "model_env": None,
        }
    ]
    for provider, (key_env, model_env) in _PROVIDER_ENV.items():
        status.append(
            {
                "provider": provider,
                "configured": bool(os.environ.get(key_env)),
                "api_key_configured": bool(os.environ.get(key_env)),
                "default_model_configured": bool(os.environ.get(model_env)),
                "model": os.environ.get(model_env, ""),
                "api_key_env": key_env,
                "model_env": model_env,
            }
        )
    return status


def create_provider(
    name: str,
    model: str = "",
    *,
    transport: Transport = _http_json,
) -> JsonModelProvider | None:
    normalized = name.strip().lower() or "deterministic"
    if normalized == "deterministic":
        return None
    if normalized == "claude":
        normalized = "anthropic"
    if normalized not in _PROVIDER_ENV:
        raise ProviderError(f"Unsupported provider: {name}")
    key_env, model_env = _PROVIDER_ENV[normalized]
    resolved_model = model.strip() or os.environ.get(model_env, "").strip()
    api_key = os.environ.get(key_env, "")
    provider_type = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "deepseek": DeepSeekProvider,
    }[normalized]
    provider = provider_type(model=resolved_model, api_key=api_key, transport=transport)
    provider._require()
    return provider


__all__ = [
    "AnthropicProvider",
    "DeepSeekProvider",
    "GeminiProvider",
    "JsonModelProvider",
    "OpenAIProvider",
    "ProviderError",
    "create_provider",
    "provider_status",
]
