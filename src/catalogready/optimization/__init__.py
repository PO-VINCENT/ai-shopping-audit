"""Evidence-grounded product visibility optimization."""

from .claims import audit_listing_claims
from .evidence import evidence_from_csv, evidence_from_html, evidence_from_shopify
from .pipeline import optimize_evidence, optimize_product_csv, optimize_product_html
from .readiness import score_page_readiness

__all__ = [
    "audit_listing_claims",
    "evidence_from_csv",
    "evidence_from_html",
    "evidence_from_shopify",
    "optimize_evidence",
    "optimize_product_csv",
    "optimize_product_html",
    "score_page_readiness",
]
