"""Extract indexable evidence from supplied HTML."""

from __future__ import annotations

from html.parser import HTMLParser


class PageSignals(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.ignored_depth = 0
        self.json_ld_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._json_ld_parts: list[str] = []
        self.canonical: str | None = None
        self.robots: str = ""
        self.description: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        lowered = tag.lower()
        if lowered == "title":
            self.in_title = True
        elif lowered in {"style", "noscript"}:
            self.ignored_depth += 1
        elif lowered == "script":
            if values.get("type", "").lower() == "application/ld+json":
                self.json_ld_depth += 1
                self._json_ld_parts = []
            else:
                self.ignored_depth += 1
        elif lowered == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href") or None
        elif lowered == "meta" and values.get("name", "").lower() == "robots":
            self.robots = values.get("content", "").lower()
        elif lowered == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self.in_title = False
        elif lowered in {"style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif lowered == "script":
            if self.json_ld_depth:
                block = "".join(self._json_ld_parts).strip()
                if block:
                    self.json_ld_blocks.append(block)
                self.json_ld_depth -= 1
                self._json_ld_parts = []
            elif self.ignored_depth:
                self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.json_ld_depth:
            self._json_ld_parts.append(data)
            return
        if self.ignored_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self.in_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def visible_text(self) -> str:
        return " ".join(self.text_parts)

    @property
    def visible_words(self) -> int:
        return len(self.visible_text.split())


def extract_page_signals(html: str) -> PageSignals:
    parser = PageSignals()
    parser.feed(html)
    return parser


def evidence_coverage(signals: PageSignals) -> dict[str, bool]:
    text = signals.visible_text.lower()
    return {
        "specifications": any(term in text for term in ("specification", "material", "dimensions", "size")),
        "limitations": any(term in text for term in ("limitation", "not suitable", "avoid", "warning")),
        "shipping": any(term in text for term in ("shipping", "delivery", "dispatch")),
        "returns": any(term in text for term in ("return", "refund", "exchange")),
    }

