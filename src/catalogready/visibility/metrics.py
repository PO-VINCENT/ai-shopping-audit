"""Observed citation and answer-support metrics."""

from __future__ import annotations

from typing import Any

from catalogready.catalog.schemas import result, scores

from .citations import domain_matches
from .competitors import citation_share_of_voice, top_competitors
from .prompt_packs import normalize_domain
from .snapshots import load_snapshots, normalize_snapshot


def calculate_visibility_metrics(observations: list[dict[str, Any]], target_domain: str) -> dict[str, Any]:
    target = normalize_domain(target_domain)
    normalized = [normalize_snapshot(observation) for observation in observations]
    total = len(normalized)
    cited = [
        observation
        for observation in normalized
        if any(domain_matches(domain, target) for domain in observation["citation_domains"])
    ]
    mentioned = sum(bool(observation["product_mentioned"]) for observation in normalized)
    support_values = [observation["answer_supported"] for observation in normalized if isinstance(observation["answer_supported"], bool)]
    share = citation_share_of_voice([observation["citation_domains"] for observation in normalized])
    citation_rate = round(100 * len(cited) / total) if total else 0
    mention_rate = round(100 * mentioned / total) if total else 0
    support_rate = round(100 * sum(support_values) / len(support_values)) if support_values else None
    return {
        "target_domain": target,
        "observations": total,
        "citation_rate": citation_rate,
        "product_mention_rate": mention_rate,
        "answer_support_rate": support_rate,
        "citation_share_of_voice": share.get(target, 0.0),
        "top_competitors": top_competitors(share, target),
        "providers": sorted({observation["provider"] for observation in normalized}),
    }


def score_visibility_snapshots(snapshot_path: str, target_domain: str) -> dict[str, Any]:
    observations = load_snapshots(snapshot_path)
    metrics = calculate_visibility_metrics(observations, target_domain)
    visibility_score = metrics["citation_rate"]
    return result(
        "score_visibility_snapshots",
        {"snapshot_path": str(snapshot_path), "target_domain": normalize_domain(target_domain)},
        scores(visibility=visibility_score),
        {**metrics, "findings": 0},
        [],
    )

