"""JSON diff summary helpers for comparing extraction results."""

from __future__ import annotations

from ..domain.models import ExtractionResult


def value_diff_summary(
    results_by_strategy: dict[str, ExtractionResult],
) -> dict[str, dict[str, object]]:
    """Summarize per-item value agreement across strategies.

    Returns a mapping item_id -> {strategy: raw_value, "agree": bool}.
    """
    summary: dict[str, dict[str, object]] = {}
    all_item_ids: list[str] = []
    for result in results_by_strategy.values():
        for v in result.values:
            if v.item_id not in all_item_ids:
                all_item_ids.append(v.item_id)

    for item_id in all_item_ids:
        per_strategy: dict[str, object] = {}
        raw_values: list[str | None] = []
        for strat, result in results_by_strategy.items():
            match = next((v for v in result.values if v.item_id == item_id), None)
            raw = match.raw_value if match else None
            per_strategy[strat] = raw
            raw_values.append(raw)
        non_null = [r for r in raw_values if r is not None]
        agree = len(set(non_null)) <= 1 and len(non_null) == len(raw_values)
        per_strategy["agree"] = agree
        summary[item_id] = per_strategy
    return summary
