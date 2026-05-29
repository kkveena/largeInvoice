"""Markdown renderer tests."""

from __future__ import annotations

from large_pdf_extractor.domain.models import ParseStrategy
from large_pdf_extractor.extraction.extractor import ExtractionEngine
from large_pdf_extractor.llm.fake_provider import FakeLLMProvider
from large_pdf_extractor.rendering.markdown_renderer import MarkdownRenderer


def test_markdown_includes_values_and_source_spans(sample_chunks, sample_dictionary):
    result = ExtractionEngine(FakeLLMProvider()).extract(
        sample_dictionary, sample_chunks, ParseStrategy.PYMUPDF
    )
    md = MarkdownRenderer().render_extraction_result(result)
    assert "# Extraction Result" in md
    assert "report_date" in md
    assert "May 28, 2026" in md
    # Source traceability (page reference) is present.
    assert "p1" in md


def test_markdown_handles_null_values(sample_dictionary):
    result = ExtractionEngine(FakeLLMProvider()).extract(
        sample_dictionary, [], ParseStrategy.PYMUPDF
    )
    md = MarkdownRenderer().render_extraction_result(result)
    assert "_null_" in md
