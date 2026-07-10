"""Terminal rendering for agent results: score cards, traces, findings."""

from __future__ import annotations

from typing import Any

from .html import PILLAR_LABELS

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"

_SEVERITY_COLORS = {"high": _RED, "medium": _YELLOW, "low": _DIM}


def _paint(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{_RESET}" if use_color else text


def _score_code(ratio: float) -> str:
    if ratio >= 0.8:
        return _GREEN
    if ratio >= 0.5:
        return _YELLOW
    return _RED


def severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        severity: sum(1 for item in findings if item.get("severity") == severity)
        for severity in ("high", "medium", "low")
    }


def render_score_card(
    result: dict[str, Any],
    report_path: Any = None,
    use_color: bool = False,
) -> str:
    readiness = (result.get("readiness") or {}).get("before") or {}
    product = (result.get("evidence_record") or {}).get("product") or {}
    findings = result.get("findings") or []
    counts = severity_counts(findings)
    score = readiness.get("score", 0)
    headline = f"CatalogReady Score: {score}/100 ({readiness.get('status', 'unknown')})"
    lines = [
        "",
        "  " + _paint(
            str(product.get("title") or (result.get("input") or {}).get("url", "Product page")),
            _BOLD,
            use_color,
        ),
        "",
        "  " + _paint(headline, _BOLD + _score_code(score / 100), use_color),
        "",
    ]
    for key, section in (readiness.get("components") or {}).items():
        label = PILLAR_LABELS.get(key, key.replace("_", " ").title())
        pillar_score = section.get("score", 0)
        maximum = section.get("max_score", 0) or 1
        value = _paint(
            f"{pillar_score:>3}/{maximum}",
            _score_code(pillar_score / maximum),
            use_color,
        )
        lines.append(f"  {label:<20} {value}")
    for reason in readiness.get("cap_reasons") or []:
        lines.append(
            "  " + _paint(f"! Score capped at {readiness.get('safety_cap')}: {reason}", _RED, use_color)
        )
    lines.extend(
        [
            "",
            f"  {counts['high']} critical · {counts['medium']} recommended · {counts['low']} minor findings",
        ]
    )
    if report_path:
        lines.append(f"  Full report: {report_path}")
    lines.append("")
    return "\n".join(lines)


def render_trace(result: dict[str, Any], use_color: bool = False) -> str:
    lines = []
    for event in result.get("trace") or []:
        marker = _paint("●", _GREEN if event.get("status") in {"completed", "validated"} else _YELLOW, use_color)
        lines.append(
            f"{marker} {event.get('tool', 'step')} "
            + _paint(f"— {event.get('summary', '')}", _DIM, use_color)
        )
    return "\n".join(lines)


def render_findings(findings: list[dict[str, Any]], use_color: bool = False) -> str:
    if not findings:
        return "No findings. Everything checked is machine-readable."
    lines = []
    for severity in ("high", "medium", "low"):
        for item in findings:
            if item.get("severity") != severity:
                continue
            tag = _paint(f"[{severity.upper()}]", _SEVERITY_COLORS[severity], use_color)
            lines.append(f"{tag} {item.get('title', 'Finding')} ({item.get('rule_id', '')})")
            lines.append(_paint(f"    {item.get('evidence', '')}", _DIM, use_color))
            lines.append(f"    → {item.get('recommendation', '')}")
    return "\n".join(lines)


def render_questions(questions: list[dict[str, Any]], use_color: bool = False) -> str:
    if not questions:
        return "No open merchant questions."
    lines = ["The agent needs these facts (it will not invent them):"]
    for item in questions:
        marker = "blocking" if item.get("blocking") else "advisory"
        tag = _paint(f"[{marker}]", _RED if item.get("blocking") else _DIM, use_color)
        lines.append(f"  {tag} {item.get('field', '')}: {item.get('question', '')}")
    lines.append('Answer with: /answers field=value [field=value ...]')
    return "\n".join(lines)


__all__ = [
    "render_findings",
    "render_questions",
    "render_score_card",
    "render_trace",
    "severity_counts",
]
