"""Stable shopper-intent prompt packs."""

from __future__ import annotations

from typing import Any


def normalize_domain(domain: str) -> str:
    return domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/", 1)[0]


def build_visibility_prompt_pack(domain: str, category: str, market: str = "en-AU") -> dict[str, Any]:
    domain = normalize_domain(domain)
    category = " ".join(category.split())
    if not domain or not category:
        raise ValueError("domain and category are required")

    prompts = [
        ("discovery", f"What are the best {category} for a first-time buyer?"),
        ("comparison", f"Compare reliable {category} for everyday use."),
        ("value", f"Which {category} offer the best value without sacrificing quality?"),
        ("education", f"What should I check before buying {category}?"),
        ("trust", f"Which brands are trusted for {category}?"),
        ("limitations", f"What are common limitations of {category}?"),
        ("use_case", f"Which {category} are suitable for demanding use cases?"),
        ("comparison", f"How does {domain} compare with alternatives for {category}?"),
        ("evidence", f"Does {domain} publish enough evidence about its {category}?"),
        ("transaction", f"Where can I buy well-documented {category} with clear returns?"),
    ]
    return {
        "schema_version": "1.0",
        "operation": "build_visibility_prompt_pack",
        "domain": domain,
        "category": category,
        "market": market,
        "prompts": [
            {"id": f"VIS-{index:03d}", "intent": intent, "text": text}
            for index, (intent, text) in enumerate(prompts, start=1)
        ],
        "measurement_note": "Run repeated, timestamped observations. Eligibility does not guarantee citation.",
    }

