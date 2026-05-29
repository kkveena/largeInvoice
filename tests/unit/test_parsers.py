"""Parser tests: PyMuPDF baseline and Docling graceful fallback."""

from __future__ import annotations

from large_pdf_extractor.domain.models import ParsedDocument, ParseStrategy
from large_pdf_extractor.parsing.docling_parser import DoclingParser
from large_pdf_extractor.parsing.pymupdf_text_parser import PyMuPDFTextParser


def test_pymupdf_parser_returns_parsed_document(sample_pdf_path):
    parser = PyMuPDFTextParser()
    parsed = parser.parse(sample_pdf_path)
    assert isinstance(parsed, ParsedDocument)
    assert parsed.strategy is ParseStrategy.PYMUPDF
    assert parsed.page_count == 2
    assert len(parsed.pages) == 2
    assert any("OPERATIONS" in p.text for p in parsed.pages)
    assert parsed.metadata.get("parse_runtime_seconds") is not None


def test_docling_parser_graceful_fallback(sample_pdf_path):
    parser = DoclingParser()
    parsed = parser.parse(sample_pdf_path)
    # Whether or not Docling is installed, parse must return a ParsedDocument.
    assert isinstance(parsed, ParsedDocument)
    assert parsed.strategy is ParseStrategy.DOCLING
    if not parser.is_available():
        # Graceful skip: no pages, structured warning, skipped flag.
        assert parsed.page_count == 0
        assert parsed.metadata.get("skipped") is True
        assert parsed.metadata.get("warnings")
    else:  # pragma: no cover - depends on environment
        assert parsed.page_count >= 1
