"""Provider-neutral prompts and JSON schemas for product optimization."""

from __future__ import annotations

import json
from typing import Any


LISTING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "listing": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "short_title": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                "description": {"type": "string"},
                "best_for": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                "limitations": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                "faq": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                            "evidence_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["question", "answer", "evidence_ids"],
                    },
                },
                "alt_text": {"type": "string"},
                "image_briefs": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "purpose": {"type": "string"},
                            "prompt": {"type": "string"},
                            "fidelity_rules": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["purpose", "prompt", "fidelity_rules"],
                    },
                },
            },
            "required": [
                "title",
                "short_title",
                "bullets",
                "description",
                "best_for",
                "limitations",
                "faq",
                "alt_text",
                "image_briefs",
            ],
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["text", "evidence_ids", "risk"],
            },
        },
        "missing_information": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["listing", "claims", "missing_information"],
}


EVALUATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["supported", "partially_supported", "unsupported", "contradicted", "requires_human_review"],
                    },
                    "reason": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "status", "reason", "evidence_ids"],
            },
        },
        "overall_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["claims", "overall_notes"],
}


GENERATOR_SYSTEM = """You are an evidence-grounded retail product visibility optimizer.
Use only the supplied product evidence. Do not invent specifications, benefits,
compatibility, certifications, reviews, price, availability, warranty, shipping,
medical, safety, environmental, or comparative claims. Every factual claim must
cite one or more supplied evidence IDs. Missing information must remain missing.
Generated customer questions are hypotheses, not measured demand. Return JSON only.
The primary image must remain the real product image; image briefs are for optional
supporting or lifestyle images and must preserve product color, shape, logo,
proportions, included items, and documented capabilities."""


EVALUATOR_SYSTEM = """You are a strict retail claim evaluator. Compare each claim
only with the supplied evidence. Never use outside knowledge. Mark a claim
supported only when the cited evidence directly entails it. Comparative,
superlative, medical, safety, environmental, compatibility, warranty, price, and
availability claims require explicit evidence. Return JSON only."""


def generator_prompt(evidence: dict[str, Any], journey: dict[str, Any]) -> str:
    return """Create a decision-support listing for the product. Keep the existing
product identity. Put distinctive verified attributes early, explain documented
trade-offs, answer useful journey questions, and list important missing facts.
Do not claim generated questions are popular or frequently asked.

PRODUCT EVIDENCE:
{evidence}

CUSTOMER JOURNEY AND QUERY HYPOTHESES:
{journey}
""".format(
        evidence=json.dumps(evidence, ensure_ascii=False),
        journey=json.dumps(journey, ensure_ascii=False),
    )


def evaluator_prompt(evidence: dict[str, Any], draft: dict[str, Any]) -> str:
    return """Evaluate every supplied claim. Downgrade vague or overstated claims.
Do not upgrade a claim based on common knowledge.

PRODUCT EVIDENCE:
{evidence}

GENERATED DRAFT:
{draft}
""".format(
        evidence=json.dumps(evidence, ensure_ascii=False),
        draft=json.dumps(draft, ensure_ascii=False),
    )


__all__ = [
    "EVALUATION_SCHEMA",
    "EVALUATOR_SYSTEM",
    "GENERATOR_SYSTEM",
    "LISTING_SCHEMA",
    "evaluator_prompt",
    "generator_prompt",
]
