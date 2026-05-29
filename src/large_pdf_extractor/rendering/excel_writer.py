"""Excel export for dictionaries and extraction results.

Produces shareable ``.xlsx`` workbooks for non-engineering stakeholders (e.g. a
product manager) without changing any core contract. Uses pandas + openpyxl.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..domain.models import ExtractionDictionary, ExtractionResult


class ExcelExporter:
    """Render Pydantic outputs into reviewer-friendly Excel workbooks."""

    def export_dictionary(self, dictionary: ExtractionDictionary, path: str) -> str:
        """Write the extraction dictionary to an Excel workbook.

        Sheet ``Dictionary`` lists one row per item; sheet ``Overview`` carries
        the dictionary-level metadata.
        """
        item_rows = [
            {
                "item_id": item.item_id,
                "document_section": item.document_section,
                "entity_name": item.entity_name,
                "description": item.description,
                "instruction_prompt": item.instruction_prompt,
                "expected_type": item.expected_type.value,
                "required": item.required,
                "examples": _join(item.examples),
                "normalization_hint": item.normalization_hint or "",
                "candidate_selection_hints": _join(item.candidate_selection_hints),
            }
            for item in dictionary.items
        ]
        items_df = pd.DataFrame(
            item_rows,
            columns=[
                "item_id",
                "document_section",
                "entity_name",
                "description",
                "instruction_prompt",
                "expected_type",
                "required",
                "examples",
                "normalization_hint",
                "candidate_selection_hints",
            ],
        )

        overview_df = pd.DataFrame(
            [
                {"field": "dictionary_id", "value": dictionary.dictionary_id},
                {"field": "name", "value": dictionary.name},
                {"field": "description", "value": dictionary.description},
                {"field": "document_id", "value": dictionary.document_id or ""},
                {
                    "field": "generated_from_strategy",
                    "value": dictionary.generated_from_strategy.value
                    if dictionary.generated_from_strategy
                    else "",
                },
                {"field": "item_count", "value": len(dictionary.items)},
            ],
            columns=["field", "value"],
        )

        return self._write_sheets(
            path, {"Overview": overview_df, "Dictionary": items_df}
        )

    def export_extraction_result(self, result: ExtractionResult, path: str) -> str:
        """Write extracted values to an Excel workbook (one row per value)."""
        rows = []
        for v in result.values:
            rows.append(
                {
                    "item_id": v.item_id,
                    "entity_name": v.entity_name,
                    "value": _stringify(v.value),
                    "raw_value": v.raw_value or "",
                    "normalized_value": _stringify(v.normalized_value),
                    "confidence": v.confidence,
                    "source_pages": _format_spans(v.source_spans),
                    "source_chunk": _first_chunk(v.source_spans),
                    "warnings": _join(v.warnings),
                    "extraction_notes": v.extraction_notes or "",
                }
            )
        values_df = pd.DataFrame(
            rows,
            columns=[
                "item_id",
                "entity_name",
                "value",
                "raw_value",
                "normalized_value",
                "confidence",
                "source_pages",
                "source_chunk",
                "warnings",
                "extraction_notes",
            ],
        )

        overview_df = pd.DataFrame(
            [
                {"field": "document_id", "value": result.document_id},
                {"field": "dictionary_id", "value": result.dictionary_id},
                {"field": "parse_strategy", "value": result.parse_strategy.value},
                {"field": "value_count", "value": len(result.values)},
                {
                    "field": "values_populated",
                    "value": sum(1 for v in result.values if v.value is not None),
                },
            ],
            columns=["field", "value"],
        )

        sheets = {"Overview": overview_df, "Extracted Values": values_df}
        if result.unmapped_observations:
            sheets["Unmapped"] = pd.DataFrame(
                {"observation": result.unmapped_observations}
            )
        return self._write_sheets(path, sheets)

    # -- internal ---------------------------------------------------------

    def _write_sheets(self, path: str, sheets: dict[str, pd.DataFrame]) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                _autosize(writer.sheets[sheet_name[:31]], df)
        return str(out)


def _join(values) -> str:
    return "; ".join(str(v) for v in (values or []))


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)


def _format_spans(spans) -> str:
    parts = []
    for span in spans or []:
        if span.page_start == span.page_end:
            parts.append(f"p{span.page_start}")
        else:
            parts.append(f"p{span.page_start}-{span.page_end}")
    return "; ".join(parts)


def _first_chunk(spans) -> str:
    for span in spans or []:
        if span.chunk_id:
            return span.chunk_id
    return ""


def _autosize(worksheet, df: pd.DataFrame, max_width: int = 60) -> None:
    """Set reasonable column widths so the workbook is readable on open."""
    from openpyxl.utils import get_column_letter

    for idx, column in enumerate(df.columns, start=1):
        header_len = len(str(column))
        cell_lens = [len(str(v)) for v in df[column].tolist()]
        width = min(max_width, max([header_len, *cell_lens], default=header_len) + 2)
        worksheet.column_dimensions[get_column_letter(idx)].width = max(10, width)
