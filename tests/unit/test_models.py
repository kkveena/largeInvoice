"""Pydantic model validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from large_pdf_extractor.domain.models import (
    ExtractedValue,
    ExtractionResult,
    ParseStrategy,
    SourceSpan,
)


def test_source_span_roundtrip():
    span = SourceSpan(document_id="d", page_start=1, page_end=2, chunk_id="c1")
    data = span.model_dump()
    assert SourceSpan.model_validate(data) == span


def test_extracted_value_confidence_bounds():
    with pytest.raises(ValidationError):
        ExtractedValue(item_id="x", entity_name="x", confidence=1.5)
    with pytest.raises(ValidationError):
        ExtractedValue(item_id="x", entity_name="x", confidence=-0.1)
    ok = ExtractedValue(item_id="x", entity_name="x", confidence=0.5)
    assert ok.confidence == 0.5


def test_extraction_result_requires_strategy_enum():
    result = ExtractionResult(
        document_id="d",
        dictionary_id="dict",
        parse_strategy=ParseStrategy.PYMUPDF,
        values=[],
    )
    assert result.parse_strategy is ParseStrategy.PYMUPDF
    # JSON serialization is stable for UI consumption.
    reload = ExtractionResult.model_validate_json(result.model_dump_json())
    assert reload == result


def test_extracted_value_allows_null_value():
    v = ExtractedValue(item_id="x", entity_name="x", value=None)
    assert v.value is None
    assert v.warnings == []
