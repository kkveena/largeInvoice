"""Fast baseline text parser using PyMuPDF (fitz).

This parser extracts per-page text and lightweight metadata. It is the default
for local smoke tests and never depends on heavyweight ML stacks.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..domain.models import ParsedDocument, ParsedPage, ParseStrategy
from ..utils.hashing import file_document_id


class PyMuPDFTextParser:
    """Baseline page-text parser."""

    strategy: ParseStrategy = ParseStrategy.PYMUPDF
    name = "pymupdf"

    def parse(self, pdf_path: str) -> ParsedDocument:
        import fitz  # PyMuPDF; imported lazily so the module stays optional.

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        document_id = file_document_id(pdf_path)
        start = time.perf_counter()

        pages: list[ParsedPage] = []
        with fitz.open(pdf_path) as doc:
            doc_metadata = dict(doc.metadata or {})
            for index in range(doc.page_count):
                page = doc.load_page(index)
                text = page.get_text("text") or ""
                pages.append(
                    ParsedPage(
                        page_number=index + 1,
                        text=text,
                        tables=[],
                        metadata={"char_count": len(text)},
                    )
                )
            page_count = doc.page_count

        runtime = time.perf_counter() - start
        return ParsedDocument(
            document_id=document_id,
            filename=path.name,
            page_count=page_count,
            strategy=self.strategy,
            pages=pages,
            metadata={
                "parser": self.name,
                "parser_version": _pymupdf_version(),
                "parse_runtime_seconds": round(runtime, 4),
                "pdf_metadata": doc_metadata,
                "warnings": [],
            },
        )


def _pymupdf_version() -> str:
    try:
        import fitz

        return getattr(fitz, "__version__", "unknown")
    except Exception:  # pragma: no cover - defensive
        return "unknown"
