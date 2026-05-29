"""Layout/table-aware parser using Docling.

Docling is an optional, heavy dependency. This parser must never crash the
pipeline if Docling is unavailable or fails: in that case it returns a
`ParsedDocument` with zero pages and a structured warning in metadata, plus
`metadata["skipped"] = True`. The comparator reports the skip explicitly.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from ..domain.models import ParsedDocument, ParsedPage, ParseStrategy
from ..utils.hashing import file_document_id


class DoclingParser:
    """Docling-backed parser with graceful fallback."""

    strategy: ParseStrategy = ParseStrategy.DOCLING
    name = "docling"

    def is_available(self) -> bool:
        """Return True if the Docling dependency can be imported."""
        _configure_torch_for_mps()
        try:
            import docling  # noqa: F401

            return True
        except Exception:
            return False

    def parse(self, pdf_path: str) -> ParsedDocument:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        document_id = file_document_id(pdf_path)

        if not self.is_available():
            return self._skipped_document(
                document_id,
                path.name,
                "Docling is not installed; Docling parser path was skipped.",
            )

        try:
            return self._parse_with_docling(pdf_path, document_id, path.name)
        except Exception as exc:  # pragma: no cover - depends on docling internals
            return self._skipped_document(
                document_id,
                path.name,
                f"Docling parsing failed and was skipped: {exc!r}",
            )

    # -- internal helpers -------------------------------------------------

    def _parse_with_docling(
        self, pdf_path: str, document_id: str, filename: str
    ) -> ParsedDocument:
        _configure_torch_for_mps()
        from docling.document_converter import DocumentConverter

        start = time.perf_counter()
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        doc = result.document

        pages = self._extract_pages(doc)
        table_count = self._count_tables(doc)
        runtime = time.perf_counter() - start

        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            page_count=len(pages),
            strategy=self.strategy,
            pages=pages,
            metadata={
                "parser": self.name,
                "parser_version": _docling_version(),
                "parse_runtime_seconds": round(runtime, 4),
                "docling_table_count": table_count,
                "skipped": False,
                "warnings": [],
            },
        )

    def _extract_pages(self, doc) -> list[ParsedPage]:
        """Build per-page text from a Docling document, robust to API variants."""
        # Group text items by their page number using export metadata.
        page_texts: dict[int, list[str]] = {}
        page_tables: dict[int, list[dict]] = {}

        # Tables (if present) carry a page number via provenance.
        for table in getattr(doc, "tables", []) or []:
            page_no = _provenance_page(table)
            try:
                md = table.export_to_markdown()
            except Exception:
                md = str(table)
            page_tables.setdefault(page_no, []).append({"markdown": md})
            page_texts.setdefault(page_no, []).append(md)

        for item in getattr(doc, "texts", []) or []:
            page_no = _provenance_page(item)
            text = getattr(item, "text", "") or ""
            if text:
                page_texts.setdefault(page_no, []).append(text)

        # Determine page range.
        num_pages = 0
        pages_attr = getattr(doc, "pages", None)
        if isinstance(pages_attr, dict) and pages_attr:
            num_pages = max(int(k) for k in pages_attr.keys())
        if page_texts:
            num_pages = max(num_pages, max(page_texts.keys()))

        if num_pages <= 0:
            # Fallback: dump whole document markdown into a single page.
            try:
                full_md = doc.export_to_markdown()
            except Exception:
                full_md = ""
            return [ParsedPage(page_number=1, text=full_md, metadata={"char_count": len(full_md)})]

        pages: list[ParsedPage] = []
        for page_no in range(1, num_pages + 1):
            text = "\n".join(page_texts.get(page_no, []))
            pages.append(
                ParsedPage(
                    page_number=page_no,
                    text=text,
                    tables=page_tables.get(page_no, []),
                    metadata={"char_count": len(text)},
                )
            )
        return pages

    def _count_tables(self, doc) -> int:
        return len(getattr(doc, "tables", []) or [])

    def _skipped_document(
        self, document_id: str, filename: str, warning: str
    ) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            page_count=0,
            strategy=self.strategy,
            pages=[],
            metadata={
                "parser": self.name,
                "parser_version": _docling_version(),
                "skipped": True,
                "warnings": [warning],
            },
        )


def _configure_torch_for_mps() -> None:
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    try:
        import torch

        try:
            torch.set_default_dtype(torch.float32)
        except Exception:
            pass
    except ImportError:
        pass


def _provenance_page(item) -> int:
    """Best-effort extraction of a 1-based page number from a Docling item."""
    prov = getattr(item, "prov", None)
    if prov:
        try:
            page_no = getattr(prov[0], "page_no", None)
            if page_no is not None:
                return int(page_no)
        except Exception:
            pass
    return 1


def _docling_version() -> str:
    try:
        import docling

        return getattr(docling, "__version__", "unknown")
    except Exception:
        return "unavailable"
