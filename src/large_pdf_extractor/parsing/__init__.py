"""Parsing layer: parser interface and concrete parser strategies."""

from ..domain.models import ParseStrategy
from .base import PDFParser, ParserUnavailableError
from .docling_parser import DoclingParser
from .pymupdf_text_parser import PyMuPDFTextParser


def get_parser(strategy: ParseStrategy | str) -> PDFParser:
    """Return a parser instance for a single (non-compare) strategy."""
    value = strategy.value if isinstance(strategy, ParseStrategy) else str(strategy)
    if value == ParseStrategy.PYMUPDF.value:
        return PyMuPDFTextParser()
    if value == ParseStrategy.DOCLING.value:
        return DoclingParser()
    raise ValueError(f"No single parser for strategy: {value!r}")


__all__ = [
    "PDFParser",
    "ParserUnavailableError",
    "PyMuPDFTextParser",
    "DoclingParser",
    "get_parser",
]
