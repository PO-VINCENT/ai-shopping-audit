"""Competitor citation share calculations."""

from __future__ import annotations

from collections import Counter


def citation_share_of_voice(domain_lists: list[list[str]]) -> dict[str, float]:
    counts: Counter[str] = Counter()
    for domains in domain_lists:
        counts.update(set(domains))
    total = sum(counts.values())
    if not total:
        return {}
    return {
        domain: round(100 * count / total, 2)
        for domain, count in counts.most_common()
    }


def top_competitors(share: dict[str, float], target_domain: str, limit: int = 5) -> list[dict[str, float | str]]:
    target = target_domain.lower().removeprefix("www.")
    return [
        {"domain": domain, "share": value}
        for domain, value in share.items()
        if domain != target
    ][:limit]

