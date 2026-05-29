"""Markdown rendering for extraction results and comparison reports.

Markdown output is human-readable and includes extracted values, warnings, and
source traceability (page/chunk references).
"""

from __future__ import annotations

from ..domain.models import ComparisonReport, ExtractionResult


class MarkdownRenderer:
    """Render extraction results and comparison reports to Markdown."""

    def render_extraction_result(self, result: ExtractionResult) -> str:
        lines: list[str] = []
        lines.append(f"# Extraction Result — `{result.parse_strategy.value}`")
        lines.append("")
        lines.append(f"- **Document ID:** `{result.document_id}`")
        lines.append(f"- **Dictionary ID:** `{result.dictionary_id}`")
        lines.append(f"- **Parser strategy:** `{result.parse_strategy.value}`")
        populated = sum(1 for v in result.values if v.value is not None)
        lines.append(f"- **Values populated:** {populated} / {len(result.values)}")
        lines.append("")

        lines.append("## Extracted Values")
        lines.append("")
        lines.append("| Item | Entity | Value | Confidence | Source (pages / chunk) | Warnings |")
        lines.append("|------|--------|-------|------------|------------------------|----------|")
        for v in result.values:
            source = self._format_spans(v.source_spans)
            value = self._format_cell(v.value)
            conf = "" if v.confidence is None else f"{v.confidence:.2f}"
            warns = ", ".join(v.warnings) if v.warnings else ""
            lines.append(
                f"| `{v.item_id}` | {v.entity_name} | {value} | {conf} | {source} | {warns} |"
            )
        lines.append("")

        if result.unmapped_observations:
            lines.append("## Unmapped Observations")
            lines.append("")
            for obs in result.unmapped_observations:
                lines.append(f"- {self._escape(str(obs))}")
            lines.append("")

        return "\n".join(lines)

    def render_comparison_report(self, report: ComparisonReport) -> str:
        lines: list[str] = []
        lines.append("# Parser Path Comparison Report")
        lines.append("")
        lines.append(f"- **Document ID:** `{report.document_id}`")
        lines.append(f"- **Dictionary ID:** `{report.dictionary_id}`")
        strategies = [s.value for s in report.compared_strategies]
        lines.append(f"- **Compared strategies:** {', '.join(strategies)}")
        lines.append("")
        lines.append(
            "> This is a deterministic engineering comparison, not a formal "
            "accuracy evaluation."
        )
        lines.append("")

        # Metrics table.
        metric_keys = self._collect_metric_keys(report)
        lines.append("## Parser Metrics")
        lines.append("")
        header = "| Metric | " + " | ".join(strategies) + " |"
        sep = "|--------|" + "|".join(["------"] * len(strategies)) + "|"
        lines.append(header)
        lines.append(sep)
        for key in metric_keys:
            row = [key]
            for strat in strategies:
                row.append(str(report.parser_metrics.get(strat, {}).get(key, "")))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

        # Dictionary item coverage.
        if report.dictionary_item_coverage:
            lines.append("## Dictionary Item Coverage (candidate chunks)")
            lines.append("")
            lines.append("| Item | " + " | ".join(strategies) + " |")
            lines.append("|------|" + "|".join(["------"] * len(strategies)) + "|")
            for item_id, per_strat in report.dictionary_item_coverage.items():
                row = [f"`{item_id}`"]
                for strat in strategies:
                    row.append(str(per_strat.get(strat, "")))
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        # Extraction presence.
        if report.extraction_presence_diff:
            lines.append("## Extracted Field Presence")
            lines.append("")
            lines.append("| Item | " + " | ".join(strategies) + " |")
            lines.append("|------|" + "|".join(["------"] * len(strategies)) + "|")
            for item_id, per_strat in report.extraction_presence_diff.items():
                row = [f"`{item_id}`"]
                for strat in strategies:
                    present = per_strat.get(strat)
                    row.append("✓" if present else "—")
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

        if report.recommendation_notes:
            lines.append("## Recommendation Notes")
            lines.append("")
            for note in report.recommendation_notes:
                lines.append(f"- {self._escape(note)}")
            lines.append("")

        if report.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warn in report.warnings:
                lines.append(f"- {self._escape(warn)}")
            lines.append("")

        return "\n".join(lines)

    # -- helpers ----------------------------------------------------------

    def _collect_metric_keys(self, report: ComparisonReport) -> list[str]:
        keys: list[str] = []
        for metrics in report.parser_metrics.values():
            for key in metrics.keys():
                if key not in keys:
                    keys.append(key)
        return keys

    def _format_spans(self, spans) -> str:
        if not spans:
            return ""
        parts = []
        for span in spans:
            if span.page_start == span.page_end:
                pages = f"p{span.page_start}"
            else:
                pages = f"p{span.page_start}-{span.page_end}"
            chunk = f" ({span.chunk_id})" if span.chunk_id else ""
            parts.append(f"{pages}{chunk}")
        return "; ".join(parts)

    def _format_cell(self, value) -> str:
        if value is None:
            return "_null_"
        return self._escape(str(value))

    def _escape(self, text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ").strip()
