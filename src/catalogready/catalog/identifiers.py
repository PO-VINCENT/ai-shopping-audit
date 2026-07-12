"""Product identifier validation (GS1 GTIN)."""

from __future__ import annotations

GTIN_LENGTHS = {8, 12, 13, 14}


def is_valid_gtin(value: str) -> bool:
    """Validate a GTIN-8/12/13/14 per GS1: length and mod-10 check digit.

    An *invalid* GTIN is worse than a missing one — Google documents an
    incorrect GTIN as a disapproval cause.
    """

    digits = str(value or "").strip()
    if not digits.isdigit() or len(digits) not in GTIN_LENGTHS:
        return False
    total = 0
    for position, char in enumerate(reversed(digits[:-1])):
        weight = 3 if position % 2 == 0 else 1
        total += int(char) * weight
    return (10 - total % 10) % 10 == int(digits[-1])


__all__ = ["GTIN_LENGTHS", "is_valid_gtin"]
