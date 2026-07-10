"""Citation URL and domain extraction."""

from __future__ import annotations

import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s\]\[\)\(<>\"']+")


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_PATTERN.findall(text):
        url = match.rstrip(".,;:!?")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def citation_domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def citation_domains(urls: list[str]) -> list[str]:
    return [domain for domain in (citation_domain(url) for url in urls) if domain]


def domain_matches(candidate: str, target: str) -> bool:
    candidate = candidate.lower().removeprefix("www.")
    target = target.lower().removeprefix("www.")
    return candidate == target or candidate.endswith(f".{target}")

