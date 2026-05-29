"""Parser interface and shared result types.

All parsers convert a PDF path into a `ParsedDocument`. Parsers should never
raise for environment reasons (e.g. an optional dependency missing); instead
they return a structured skip/empty document with warnings in metadata so the
pipeline can continue and the comparator can report the gap.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import ParsedDocument, ParseStrategy


@runtime_checkable
class PDFParser(Protocol):
    """Common parser contract. Designed to become an agent tool (`parse_pdf`)."""

    strategy: ParseStrategy

    def parse(self, pdf_path: str) -> ParsedDocument:  # pragma: no cover - protocol
        ...


class ParserUnavailableError(RuntimeError):
    """Raised internally when a parser dependency cannot be loaded.

    The pipeline catches this and converts it to a graceful skip; it is not
    propagated as a fatal error.
    """
