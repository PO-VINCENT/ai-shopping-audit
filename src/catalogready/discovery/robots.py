"""Small robots.txt parser for discovery eligibility checks."""

from __future__ import annotations

from urllib.parse import urlsplit

from catalogready.catalog.schemas import Finding, finding


def _rules_for(robots_txt: str, user_agent: str) -> list[tuple[str, str]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    current_agents: list[str] = []
    current_rules: list[tuple[str, str]] = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        lowered = key.lower()
        if lowered == "user-agent":
            if current_rules:
                groups.append((current_agents, current_rules))
                current_agents, current_rules = [], []
            current_agents.append(value.lower())
        elif lowered in {"allow", "disallow"} and current_agents:
            current_rules.append((lowered, value))
    if current_agents:
        groups.append((current_agents, current_rules))

    target = user_agent.lower()
    exact = [rules for agents, rules in groups if target in agents]
    wildcard = [rules for agents, rules in groups if "*" in agents]
    selected = exact if exact else wildcard
    return [rule for rules in selected for rule in rules]


def is_allowed(robots_txt: str, user_agent: str, url: str) -> bool:
    path = urlsplit(url).path or "/"
    matches = [rule for rule in _rules_for(robots_txt, user_agent) if rule[1] and path.startswith(rule[1])]
    if not matches:
        return True
    directive, _ = max(matches, key=lambda rule: len(rule[1]))
    return directive == "allow"


def audit_robots(robots_txt: str, url: str) -> tuple[dict[str, bool], list[Finding]]:
    access = {
        "googlebot": is_allowed(robots_txt, "googlebot", url),
        "oai_searchbot": is_allowed(robots_txt, "oai-searchbot", url),
        "bingbot": is_allowed(robots_txt, "bingbot", url),
    }
    findings: list[Finding] = []
    for agent, allowed in access.items():
        if not allowed:
            findings.append(
                finding(
                    f"SEO-ROBOTS-{agent.upper()}",
                    "high",
                    f"Crawler is blocked: {agent}",
                    f"robots.txt disallows the audited path for {agent}.",
                    "Change crawler access only if public discovery is intended.",
                )
            )
    return access, findings

