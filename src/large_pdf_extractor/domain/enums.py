"""Enumerations used across the extraction pipeline.

These are document-type agnostic. No finance/CME-specific values live here.
"""

from __future__ import annotations

from enum import Enum


class ParseStrategy(str, Enum):
    """Parser/chunking strategy selector."""

    PYMUPDF = "pymupdf"
    DOCLING = "docling"
    COMPARE = "compare"


class ChunkType(str, Enum):
    """Coarse classification of a chunk's structure."""

    PAGE = "page"
    SECTION = "section"
    TABLE = "table"
    MIXED = "mixed"


class ExpectedValueType(str, Enum):
    """Expected type of an extracted dictionary value."""

    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"
    TABLE = "table"
    OBJECT = "object"


class ArtifactType(str, Enum):
    """Types of artifacts written to the artifact store."""

    PARSED_DOCUMENT = "parsed_document"
    DOCUMENT_PROFILE = "document_profile"
    EXTRACTION_DICTIONARY = "extraction_dictionary"
    CHUNKS = "chunks"
    EXTRACTION_RESULT = "extraction_result"
    MARKDOWN_RESULT = "markdown_result"
    COMPARISON_REPORT = "comparison_report"
    RUN_METADATA = "run_metadata"
