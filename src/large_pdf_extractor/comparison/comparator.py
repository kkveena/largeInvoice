"""Parser path comparator.

Produces a deterministic engineering comparison (NOT formal accuracy
evaluation) of two or more parser/chunking paths over a shared dictionary.
"""

from __future__ import annotations

from typing import Any

from ..chunking.candidate_selector import CandidateSelector
from ..domain.models import (
    ComparisonReport,
    DocumentChunk,
    ExtractionDictionary,
    ParserPathResult,
    ParseStrategy,
)
from .diff import value_diff_summary


class ParserPathComparator:
    """Compare parser paths. Designed to be an agent tool (`compare_parser_paths`)."""

    def __init__(self, selector: CandidateSelector | None = None):
        self.selector = selector or CandidateSelector()

    def compare(
        self,
        document_id: str,
        dictionary: ExtractionDictionary | None,
        results: list[ParserPathResult],
    ) -> ComparisonReport:
        compared = [r.strategy for r in results]
        parser_metrics: dict[str, dict[str, Any]] = {}
        warnings: list[str] = []

        for result in results:
            strat = result.strategy.value
            parser_metrics[strat] = self._metrics_for(result)
            warnings.extend(f"[{strat}] {w}" for w in result.warnings)
            warnings.extend(f"[{strat}] ERROR: {e}" for e in result.errors)

        coverage = self._coverage(dictionary, results)
        presence = self._presence(dictionary, results)
        notes = self._recommendation_notes(results, dictionary)

        # JSON diff summary across extraction results (stored in metrics).
        results_by_strategy = {
            r.strategy.value: r.extraction_result
            for r in results
            if r.extraction_result is not None
        }
        if len(results_by_strategy) >= 2:
            diff = value_diff_summary(results_by_strategy)
            agree_count = sum(1 for d in diff.values() if d.get("agree"))
            notes.append(
                f"Raw-value agreement on {agree_count}/{len(diff)} dictionary items "
                "across parser paths."
            )

        return ComparisonReport(
            document_id=document_id,
            dictionary_id=dictionary.dictionary_id if dictionary else None,
            compared_strategies=compared,
            parser_metrics=parser_metrics,
            dictionary_item_coverage=coverage,
            extraction_presence_diff=presence,
            warnings=warnings,
            recommendation_notes=notes,
        )

    # -- metrics ----------------------------------------------------------

    def _metrics_for(self, result: ParserPathResult) -> dict[str, Any]:
        parsed = result.parsed_document
        profile = result.document_profile
        chunks = result.chunks

        token_estimates = [c.token_estimate for c in chunks]
        avg_tokens = (
            round(sum(token_estimates) / len(token_estimates), 2)
            if token_estimates
            else 0
        )
        max_tokens = max(token_estimates) if token_estimates else 0
        table_like_chunks = sum(1 for c in chunks if c.table_like)

        metrics: dict[str, Any] = {
            "parser_name": result.strategy.value,
            "skipped": bool(parsed.metadata.get("skipped")) if parsed else True,
            "parse_runtime_seconds": (
                parsed.metadata.get("parse_runtime_seconds") if parsed else None
            ),
            "page_count": parsed.page_count if parsed else 0,
            "extracted_char_count": profile.total_char_count if profile else 0,
            "low_text_page_count": (
                len(profile.empty_or_low_text_pages) if profile else 0
            ),
            "detected_table_count": profile.detected_table_count if profile else 0,
            "detected_heading_count": (
                len(profile.detected_headings) if profile else 0
            ),
            "chunk_count": len(chunks),
            "avg_chunk_token_estimate": avg_tokens,
            "max_chunk_token_estimate": max_tokens,
            "table_like_chunk_count": table_like_chunks,
            "repeated_header_candidate_count": (
                len(profile.repeated_header_candidates) if profile else 0
            ),
            "repeated_footer_candidate_count": (
                len(profile.repeated_footer_candidates) if profile else 0
            ),
            "warning_count": len(result.warnings),
            "error_count": len(result.errors),
        }
        # Merge any pipeline-supplied metrics.
        metrics.update(result.metrics or {})
        return metrics

    def _coverage(
        self,
        dictionary: ExtractionDictionary | None,
        results: list[ParserPathResult],
    ) -> dict[str, dict[str, Any]]:
        if not dictionary:
            return {}
        coverage: dict[str, dict[str, Any]] = {}
        for item in dictionary.items:
            per_strategy: dict[str, Any] = {}
            for result in results:
                candidates = (
                    self.selector.select(item, result.chunks) if result.chunks else []
                )
                per_strategy[result.strategy.value] = len(candidates)
            coverage[item.item_id] = per_strategy
        return coverage

    def _presence(
        self,
        dictionary: ExtractionDictionary | None,
        results: list[ParserPathResult],
    ) -> dict[str, dict[str, Any]]:
        presence: dict[str, dict[str, Any]] = {}
        item_ids = (
            [i.item_id for i in dictionary.items] if dictionary else []
        )
        if not item_ids:
            for result in results:
                if result.extraction_result:
                    for v in result.extraction_result.values:
                        if v.item_id not in item_ids:
                            item_ids.append(v.item_id)

        for item_id in item_ids:
            per_strategy: dict[str, Any] = {}
            for result in results:
                present = False
                if result.extraction_result:
                    match = next(
                        (
                            v
                            for v in result.extraction_result.values
                            if v.item_id == item_id
                        ),
                        None,
                    )
                    present = bool(match and match.value is not None)
                per_strategy[result.strategy.value] = present
            presence[item_id] = per_strategy
        return presence

    def _recommendation_notes(
        self,
        results: list[ParserPathResult],
        dictionary: ExtractionDictionary | None,
    ) -> list[str]:
        notes: list[str] = []
        active = [r for r in results if r.parsed_document and r.parsed_document.pages]
        skipped = [
            r
            for r in results
            if not r.parsed_document or not r.parsed_document.pages
        ]

        for r in skipped:
            notes.append(
                f"Parser path '{r.strategy.value}' produced no pages and was "
                "treated as a graceful skip."
            )

        if len(active) >= 2:
            # Compare text coverage.
            by_chars = sorted(
                active,
                key=lambda r: r.document_profile.total_char_count
                if r.document_profile
                else 0,
                reverse=True,
            )
            top = by_chars[0]
            notes.append(
                f"'{top.strategy.value}' produced the most extracted text "
                f"({top.document_profile.total_char_count if top.document_profile else 0} chars)."
            )
            # Compare table structure.
            by_tables = sorted(
                active,
                key=lambda r: r.document_profile.detected_table_count
                if r.document_profile
                else 0,
                reverse=True,
            )
            top_tables = by_tables[0]
            notes.append(
                f"'{top_tables.strategy.value}' detected the most table-like "
                f"structure ({top_tables.document_profile.detected_table_count if top_tables.document_profile else 0} table pages)."
            )
        elif len(active) == 1:
            notes.append(
                f"Only '{active[0].strategy.value}' ran successfully; comparison "
                "is single-sided."
            )

        return notes
