"""Helpers for merging/summarizing extraction results.

Kept separate from the engine so future phases can add reconciliation logic
(e.g. merging values across parser paths) without touching the extractor.
"""

from __future__ import annotations

from ..domain.models import ExtractionResult


def presence_map(result: ExtractionResult) -> dict[str, bool]:
    """Map each item_id to whether a non-null value was extracted."""
    return {v.item_id: (v.value is not None) for v in result.values}


def populated_count(result: ExtractionResult) -> int:
    """Number of items with a non-null extracted value."""
    return sum(1 for v in result.values if v.value is not None)
