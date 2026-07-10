from __future__ import annotations

import unittest

from catalogready.model_providers.base import (
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    OpenAIProvider,
)


class ModelProviderTests(unittest.TestCase):
    def test_openai_responses_adapter(self) -> None:
        seen = {}

        def transport(url, headers, payload, timeout):
            seen.update(url=url, headers=headers, payload=payload, timeout=timeout)
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"ok": true}'}],
                    }
                ]
            }

        result = OpenAIProvider("model-id", "secret", transport).generate_json(
            "system",
            "user",
            {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(seen["url"], "https://api.openai.com/v1/responses")
        self.assertFalse(seen["payload"]["store"])
        self.assertEqual(seen["payload"]["text"]["format"]["type"], "json_schema")

    def test_gemini_generate_content_adapter(self) -> None:
        def transport(url, headers, payload, timeout):
            self.assertIn(":generateContent", url)
            self.assertEqual(headers["x-goog-api-key"], "secret")
            self.assertEqual(payload["generationConfig"]["responseJsonSchema"], {"type": "object"})
            return {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}

        result = GeminiProvider("model-id", "secret", transport).generate_json(
            "system",
            "user",
            {"type": "object"},
        )
        self.assertEqual(result, {"ok": True})

    def test_anthropic_messages_adapter(self) -> None:
        def transport(url, headers, payload, timeout):
            self.assertEqual(url, "https://api.anthropic.com/v1/messages")
            self.assertEqual(payload["messages"][0]["role"], "user")
            return {"content": [{"type": "text", "text": "```json\n{\"ok\": true}\n```"}]}

        result = AnthropicProvider("model-id", "secret", transport).generate_json("system", "user")
        self.assertEqual(result, {"ok": True})

    def test_deepseek_chat_completions_adapter(self) -> None:
        def transport(url, headers, payload, timeout):
            self.assertEqual(url, "https://api.deepseek.com/chat/completions")
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        result = DeepSeekProvider("model-id", "secret", transport).generate_json("system", "user")
        self.assertEqual(result, {"ok": True})


if __name__ == "__main__":
    unittest.main()
