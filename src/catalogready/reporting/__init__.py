"""Human-readable and machine-readable report rendering."""

from .html import render_html_report
from .render import render_markdown_report

__all__ = ["render_html_report", "render_markdown_report"]

