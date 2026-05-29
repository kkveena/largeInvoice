"""Shared pytest fixtures.

A tiny PDF is generated on the fly with PyMuPDF so tests never depend on the
heavy reference document. The generated fixture intentionally contains the
structural patterns Phase 1 targets: a title, a date, repeated header/footer
lines, a heading, and a small numeric table.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from large_pdf_extractor.domain.models import (
    ChunkType,
    DocumentChunk,
    ExpectedValueType,
    ExtractionDictionary,
    ExtractionDictionaryItem,
    ParsedDocument,
    ParsedPage,
    ParseStrategy,
    SourceSpan,
)

_HEADER = "ACME OPERATIONS DAILY BULLETIN"
_FOOTER = "Confidential - subject to operational controls"

_PAGE_BODY = [
    (
        f"{_HEADER}\n"
        "Report Date: May 28, 2026\n"
        "MARKET OPERATIONS SUMMARY\n"
        "Product Code: ABC123\n"
        "Status: FINAL\n"
        "Volume     Open Interest     Settlement\n"
        "1,234      5,678             99.50\n"
        "2,345      6,789             98.25\n"
        "3,456      7,890             97.10\n"
        "4,567      8,901             96.05\n"
        "Total      6,912             ----\n"
        f"{_FOOTER}\n"
    ),
    (
        f"{_HEADER}\n"
        "POSITION DETAIL\n"
        "Account: DESK-01\n"
        "Quantity   Price    Delta\n"
        "100        12.5     0.45\n"
        "200        13.0     0.55\n"
        "Exception: unmatched trade pending\n"
        f"{_FOOTER}\n"
    ),
]


@pytest.fixture(scope="session")
def sample_pdf_path(tmp_path_factory) -> str:
    import fitz

    path = tmp_path_factory.mktemp("pdf") / "sample.pdf"
    doc = fitz.open()
    for body in _PAGE_BODY:
        page = doc.new_page()
        page.insert_text((50, 60), body, fontsize=9)
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def sample_parsed_document() -> ParsedDocument:
    pages = [
        ParsedPage(page_number=i + 1, text=body, metadata={"char_count": len(body)})
        for i, body in enumerate(_PAGE_BODY)
    ]
    return ParsedDocument(
        document_id="doc-test",
        filename="sample.pdf",
        page_count=len(pages),
        strategy=ParseStrategy.PYMUPDF,
        pages=pages,
        metadata={"parser": "pymupdf", "parse_runtime_seconds": 0.01, "warnings": []},
    )


@pytest.fixture
def sample_chunks(sample_parsed_document) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for page in sample_parsed_document.pages:
        cid = f"pymupdf-c{page.page_number:04d}-p{page.page_number}"
        chunks.append(
            DocumentChunk(
                chunk_id=cid,
                document_id=sample_parsed_document.document_id,
                parser_strategy=ParseStrategy.PYMUPDF,
                chunk_type=ChunkType.TABLE,
                page_start=page.page_number,
                page_end=page.page_number,
                text=page.text,
                token_estimate=len(page.text) // 4,
                heading="MARKET OPERATIONS SUMMARY" if page.page_number == 1 else None,
                table_like=True,
                source_spans=[
                    SourceSpan(
                        document_id=sample_parsed_document.document_id,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        chunk_id=cid,
                    )
                ],
            )
        )
    return chunks


@pytest.fixture
def sample_dictionary() -> ExtractionDictionary:
    return ExtractionDictionary(
        dictionary_id="dict-test",
        document_id="doc-test",
        name="Test dictionary",
        description="A minimal dictionary for tests.",
        generated_from_strategy=ParseStrategy.PYMUPDF,
        items=[
            ExtractionDictionaryItem(
                item_id="report_date",
                document_section="document metadata",
                entity_name="report_date",
                description="The report date.",
                instruction_prompt="Extract the report date.",
                expected_type=ExpectedValueType.DATE,
                required=True,
                candidate_selection_hints=["date", "report"],
            ),
            ExtractionDictionaryItem(
                item_id="status",
                document_section="operational status",
                entity_name="status",
                description="Operational status.",
                instruction_prompt="Extract the operational status.",
                expected_type=ExpectedValueType.STRING,
                candidate_selection_hints=["status", "final"],
            ),
        ],
    )
