"""Extraction engine tests."""

from __future__ import annotations

from large_pdf_extractor.domain.models import (
    ExtractionResult,
    ParseStrategy,
)
from large_pdf_extractor.extraction.extractor import ExtractionEngine
from large_pdf_extractor.llm.fake_provider import FakeLLMProvider


def test_extractor_produces_grounded_result(sample_chunks, sample_dictionary):
    engine = ExtractionEngine(FakeLLMProvider())
    result = engine.extract(sample_dictionary, sample_chunks, ParseStrategy.PYMUPDF)

    assert isinstance(result, ExtractionResult)
    assert result.dictionary_id == sample_dictionary.dictionary_id
    # Only dictionary item_ids appear in values.
    item_ids = {i.item_id for i in sample_dictionary.items}
    assert {v.item_id for v in result.values} == item_ids

    date_value = next(v for v in result.values if v.item_id == "report_date")
    assert date_value.raw_value == "May 28, 2026"
    assert date_value.source_spans
    assert date_value.source_spans[0].chunk_id is not None


def test_extractor_is_deterministic(sample_chunks, sample_dictionary):
    engine = ExtractionEngine(FakeLLMProvider())
    r1 = engine.extract(sample_dictionary, sample_chunks, ParseStrategy.PYMUPDF)
    r2 = engine.extract(sample_dictionary, sample_chunks, ParseStrategy.PYMUPDF)
    assert r1.model_dump() == r2.model_dump()


def test_extractor_handles_no_chunks(sample_dictionary):
    engine = ExtractionEngine(FakeLLMProvider())
    result = engine.extract(sample_dictionary, [], ParseStrategy.PYMUPDF)
    assert all(v.value is None for v in result.values)
