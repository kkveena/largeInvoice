"""Core Pydantic contracts for the Phase 1 large-PDF extraction pipeline.

Every external and internal contract is a Pydantic model. These models are
document-type agnostic: they carry generic concepts (pages, chunks, dictionary
items, extracted values, source spans) and never hard-code finance/CME logic.
Domain-specific behavior lives in configurable hints, templates, and prompts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .enums import (
    ArtifactType,
    ChunkType,
    ExpectedValueType,
    ParseStrategy,
)


class SourceSpan(BaseModel):
    """Pointer back to the source location of a piece of content."""

    document_id: str
    page_start: int
    page_end: int
    chunk_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    bbox: list[float] | None = None


class ParsedPage(BaseModel):
    """A single parsed page of a document."""

    page_number: int
    text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """A fully parsed document produced by a parser strategy."""

    document_id: str
    filename: str
    page_count: int
    strategy: ParseStrategy
    pages: list[ParsedPage]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentProfile(BaseModel):
    """Representative summary of a parsed document used downstream."""

    document_id: str
    strategy: ParseStrategy
    page_count: int
    total_char_count: int
    empty_or_low_text_pages: list[int] = Field(default_factory=list)
    detected_headings: list[str] = Field(default_factory=list)
    detected_table_count: int = 0
    repeated_header_candidates: list[str] = Field(default_factory=list)
    repeated_footer_candidates: list[str] = Field(default_factory=list)
    representative_chunk_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A parser-aware chunk that fits an LLM context window."""

    chunk_id: str
    document_id: str
    parser_strategy: ParseStrategy
    chunk_type: ChunkType
    page_start: int
    page_end: int
    text: str
    token_estimate: int
    heading: str | None = None
    table_like: bool = False
    source_spans: list[SourceSpan] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionDictionaryItem(BaseModel):
    """A single extraction-contract field."""

    item_id: str
    document_section: str
    entity_name: str
    description: str
    instruction_prompt: str
    expected_type: ExpectedValueType
    required: bool = False
    examples: list[str] = Field(default_factory=list)
    normalization_hint: str | None = None
    candidate_selection_hints: list[str] = Field(default_factory=list)


class ExtractionDictionary(BaseModel):
    """The extraction contract: what to extract and how to find/instruct it."""

    dictionary_id: str
    document_id: str | None = None
    name: str
    description: str
    items: list[ExtractionDictionaryItem]
    generated_from_strategy: ParseStrategy | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedValue(BaseModel):
    """A single extracted value, source-grounded and raw-preserving."""

    item_id: str
    entity_name: str
    value: Any | None = None
    raw_value: str | None = None
    normalized_value: Any | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_spans: list[SourceSpan] = Field(default_factory=list)
    extraction_notes: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """The set of extracted values for one parser strategy + dictionary."""

    document_id: str
    dictionary_id: str
    parse_strategy: ParseStrategy
    values: list[ExtractedValue]
    unmapped_observations: list[str] = Field(default_factory=list)
    markdown_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParserPathResult(BaseModel):
    """Everything produced by running one parser path end-to-end."""

    strategy: ParseStrategy
    parsed_document: ParsedDocument | None = None
    document_profile: DocumentProfile | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    extraction_result: ExtractionResult | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ComparisonReport(BaseModel):
    """Deterministic engineering comparison of parser paths (not eval)."""

    document_id: str
    dictionary_id: str | None = None
    compared_strategies: list[ParseStrategy]
    parser_metrics: dict[str, dict[str, Any]]
    dictionary_item_coverage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    extraction_presence_diff: dict[str, dict[str, Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    recommendation_notes: list[str] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    """A reference to a written artifact on disk."""

    artifact_type: ArtifactType
    path: str
    strategy: ParseStrategy | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunConfig(BaseModel):
    """Configuration for a single pipeline run."""

    pdf_path: str
    output_dir: str
    strategy: ParseStrategy = ParseStrategy.PYMUPDF
    dictionary_path: str | None = None
    llm_provider: str = "fake"
    max_chunk_tokens: int = 4000
    chunk_overlap_tokens: int = 300
    max_chunks: int | None = None


class PipelineStepResult(BaseModel):
    """Result of a single named pipeline step."""

    step_name: str
    success: bool
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunState(BaseModel):
    """Serializable state of a run; future agents can reason over this."""

    run_id: str
    document_id: str
    config: RunConfig
    steps: list[PipelineStepResult] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "SourceSpan",
    "ParsedPage",
    "ParsedDocument",
    "DocumentProfile",
    "DocumentChunk",
    "ExtractionDictionaryItem",
    "ExtractionDictionary",
    "ExtractedValue",
    "ExtractionResult",
    "ParserPathResult",
    "ComparisonReport",
    "ArtifactRef",
    "RunConfig",
    "PipelineStepResult",
    "RunState",
    "ParseStrategy",
    "ChunkType",
    "ExpectedValueType",
    "ArtifactType",
]
