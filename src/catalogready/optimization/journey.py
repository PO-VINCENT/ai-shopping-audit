"""Deterministic customer types, journey stages, and query hypotheses."""

from __future__ import annotations

from typing import Any


CUSTOMER_TYPES = {
    "problem_solver": {
        "label": "Problem solver",
        "focus": "Whether the product solves a specific need or use case",
    },
    "category_beginner": {
        "label": "Category beginner",
        "focus": "Understanding choices, terminology, and buying criteria",
    },
    "specification_buyer": {
        "label": "Specification buyer",
        "focus": "Technical requirements, dimensions, materials, and performance",
    },
    "comparison_shopper": {
        "label": "Comparison shopper",
        "focus": "Differences, trade-offs, and fit versus alternatives",
    },
    "value_shopper": {
        "label": "Value shopper",
        "focus": "Budget, durability, inclusions, and total value",
    },
    "risk_conscious": {
        "label": "Risk-conscious shopper",
        "focus": "Reliability, reviews, limitations, warranty, and returns",
    },
    "compatibility_buyer": {
        "label": "Compatibility buyer",
        "focus": "Whether the product works with an existing product or environment",
    },
}


def _suggested_types(category: str) -> list[str]:
    text = category.lower()
    if any(word in text for word in ("apparel", "clothing", "shoe", "fashion")):
        return ["problem_solver", "comparison_shopper", "risk_conscious"]
    if any(word in text for word in ("electronic", "computer", "phone", "camera", "appliance")):
        return ["specification_buyer", "compatibility_buyer", "comparison_shopper"]
    if any(word in text for word in ("beauty", "skin", "hair", "cosmetic")):
        return ["problem_solver", "risk_conscious", "value_shopper"]
    if any(word in text for word in ("home", "furniture", "garden", "kitchen")):
        return ["problem_solver", "specification_buyer", "compatibility_buyer"]
    return ["problem_solver", "category_beginner", "comparison_shopper"]


def build_journey(
    product: dict[str, Any],
    *,
    market: str = "en-AU",
    target_customer_types: list[str] | None = None,
) -> dict[str, Any]:
    title = str(product.get("title") or "this product")
    category = str(product.get("category") or "this product category")
    selected = target_customer_types or _suggested_types(category)
    selected = [item for item in selected if item in CUSTOMER_TYPES][:3]
    if not selected:
        selected = _suggested_types(category)

    customer_types = [
        {
            "id": item,
            **CUSTOMER_TYPES[item],
            "status": "merchant_confirmation_required",
        }
        for item in selected
    ]

    stages = [
        {
            "id": "need_recognition",
            "name": "Need recognition",
            "intent": "Solve a problem or satisfy a goal",
            "questions": [
                f"What problems can {category} help solve?",
                f"Who is {title} best suited to based on its documented features?",
                f"When would someone choose {category}?",
            ],
            "content_needed": ["documented use cases", "audience fit", "limitations"],
        },
        {
            "id": "exploration",
            "name": "Exploration",
            "intent": "Understand the category and buying criteria",
            "questions": [
                f"What should I look for when buying {category}?",
                f"Which specifications matter most for {category}?",
                f"What types of {category} are available?",
            ],
            "content_needed": ["category terminology", "key specifications", "variant choices"],
        },
        {
            "id": "evaluation",
            "name": "Evaluation",
            "intent": "Compare fit, features, and trade-offs",
            "questions": [
                f"How does {title} differ from similar {category}?",
                f"What are the main advantages and limitations of {title}?",
                f"Is {title} suitable for my requirements?",
                f"Which variant of {title} should I choose?",
            ],
            "content_needed": ["comparison facts", "best-for guidance", "limitations", "variant table"],
        },
        {
            "id": "validation",
            "name": "Validation",
            "intent": "Reduce purchase risk",
            "questions": [
                f"What evidence supports the claims about {title}?",
                f"What do verified customers say about {title}?",
                f"What warranty, compatibility, or return limitations apply?",
            ],
            "content_needed": ["reviews", "source evidence", "compatibility", "warranty and returns"],
        },
        {
            "id": "purchase",
            "name": "Purchase",
            "intent": "Confirm price, availability, and delivery",
            "questions": [
                f"What is the current price of {title}?",
                f"Is {title} currently available?",
                f"What is included and what are the shipping and return terms?",
            ],
            "content_needed": ["current price", "availability", "inclusions", "shipping and returns"],
        },
        {
            "id": "post_purchase",
            "name": "Post-purchase",
            "intent": "Use, maintain, or troubleshoot the product",
            "questions": [
                f"How should I set up or use {title}?",
                f"How should I clean or maintain {title}?",
                f"Where can I find support for {title}?",
            ],
            "content_needed": ["instructions", "care", "troubleshooting", "support"],
        },
    ]

    queries: list[dict[str, Any]] = []
    for stage in stages:
        for question in stage["questions"]:
            queries.append(
                {
                    "id": f"Q-{len(queries) + 1:02d}",
                    "query": question,
                    "journey_stage": stage["id"],
                    "intent": stage["intent"],
                    "source": "generated_hypothesis",
                    "frequency": None,
                    "confidence": 0.5,
                }
            )

    return {
        "market": market,
        "category": category,
        "customer_types": customer_types,
        "stages": stages,
        "queries": queries[:20],
        "notice": "Generated questions are hypotheses until supported by search, review, support, or sales evidence.",
    }


__all__ = ["CUSTOMER_TYPES", "build_journey"]
