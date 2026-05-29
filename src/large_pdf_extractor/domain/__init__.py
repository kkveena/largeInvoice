"""Domain layer: enums and Pydantic contracts."""

from .enums import (
    ArtifactType,
    ChunkType,
    ExpectedValueType,
    ParseStrategy,
)
from .models import (
    ArtifactRef,
    ComparisonReport,
    DocumentChunk,
    DocumentProfile,
    ExtractedValue,
    ExtractionDictionary,
    ExtractionDictionaryItem,
    ExtractionResult,
    ParsedDocument,
    ParsedPage,
    ParserPathResult,
    PipelineStepResult,
    RunConfig,
    RunState,
    SourceSpan,
)

__all__ = [
    "ArtifactType",
    "ChunkType",
    "ExpectedValueType",
    "ParseStrategy",
    "ArtifactRef",
    "ComparisonReport",
    "DocumentChunk",
    "DocumentProfile",
    "ExtractedValue",
    "ExtractionDictionary",
    "ExtractionDictionaryItem",
    "ExtractionResult",
    "ParsedDocument",
    "ParsedPage",
    "ParserPathResult",
    "PipelineStepResult",
    "RunConfig",
    "RunState",
    "SourceSpan",
]
