"""Comparator tests, including graceful Docling skip."""

from __future__ import annotations

from large_pdf_extractor.chunking.chunker import ChunkingService
from large_pdf_extractor.comparison.comparator import ParserPathComparator
from large_pdf_extractor.domain.models import (
    ComparisonReport,
    ParsedDocument,
    ParserPathResult,
    ParseStrategy,
)
from large_pdf_extractor.extraction.extractor import ExtractionEngine
from large_pdf_extractor.llm.fake_provider import FakeLLMProvider
from large_pdf_extractor.profiling.document_profiler import DocumentProfiler


def _pymupdf_path(parsed, dictionary) -> ParserPathResult:
    profile = DocumentProfiler().profile(parsed)
    chunks = ChunkingService().chunk(parsed, profile)
    result = ExtractionEngine(FakeLLMProvider()).extract(
        dictionary, chunks, ParseStrategy.PYMUPDF
    )
    return ParserPathResult(
        strategy=ParseStrategy.PYMUPDF,
        parsed_document=parsed,
        document_profile=profile,
        chunks=chunks,
        extraction_result=result,
    )


def _docling_skip_path(document_id) -> ParserPathResult:
    skipped = ParsedDocument(
        document_id=document_id,
        filename="sample.pdf",
        page_count=0,
        strategy=ParseStrategy.DOCLING,
        pages=[],
        metadata={"skipped": True, "warnings": ["Docling not installed"]},
    )
    profile = DocumentProfiler().profile(skipped)
    return ParserPathResult(
        strategy=ParseStrategy.DOCLING,
        parsed_document=skipped,
        document_profile=profile,
        chunks=[],
        warnings=["Docling not installed"],
    )


def test_comparator_handles_docling_skip(sample_parsed_document, sample_dictionary):
    py_path = _pymupdf_path(sample_parsed_document, sample_dictionary)
    dl_path = _docling_skip_path(sample_parsed_document.document_id)

    report = ParserPathComparator().compare(
        sample_parsed_document.document_id, sample_dictionary, [py_path, dl_path]
    )
    assert isinstance(report, ComparisonReport)
    assert ParseStrategy.PYMUPDF in report.compared_strategies
    assert ParseStrategy.DOCLING in report.compared_strategies

    py_metrics = report.parser_metrics["pymupdf"]
    dl_metrics = report.parser_metrics["docling"]
    assert py_metrics["page_count"] == 2
    assert dl_metrics["skipped"] is True
    assert dl_metrics["page_count"] == 0

    # Coverage and presence keyed by dictionary items.
    assert set(report.dictionary_item_coverage) == {
        i.item_id for i in sample_dictionary.items
    }
    assert any("graceful skip" in n for n in report.recommendation_notes)


def test_comparator_presence_reflects_extraction(
    sample_parsed_document, sample_dictionary
):
    py_path = _pymupdf_path(sample_parsed_document, sample_dictionary)
    dl_path = _docling_skip_path(sample_parsed_document.document_id)
    report = ParserPathComparator().compare(
        sample_parsed_document.document_id, sample_dictionary, [py_path, dl_path]
    )
    presence = report.extraction_presence_diff["report_date"]
    assert presence["pymupdf"] is True
    assert presence["docling"] is False
