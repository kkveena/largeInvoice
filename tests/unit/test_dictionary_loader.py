"""Dictionary loading, validation, and generation tests."""

from __future__ import annotations

import json

import pytest

from large_pdf_extractor.dictionary.generator import DictionaryService
from large_pdf_extractor.dictionary.loader import (
    DictionaryLoader,
    DictionaryValidationError,
)
from large_pdf_extractor.domain.models import ExtractionDictionary
from large_pdf_extractor.profiling.document_profiler import (
    DocumentProfiler,
    select_representative_chunks,
)
from large_pdf_extractor.chunking.chunker import ChunkingService


def test_loader_rejects_invalid_dictionary(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "missing required fields"}), encoding="utf-8")
    with pytest.raises(DictionaryValidationError):
        DictionaryLoader().load(str(bad))


def test_loader_rejects_empty_items(tmp_path):
    data = {
        "dictionary_id": "d",
        "name": "n",
        "description": "desc",
        "items": [],
    }
    path = tmp_path / "empty.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DictionaryValidationError):
        DictionaryLoader().load(str(path))


def test_loader_accepts_valid_dictionary(tmp_path, sample_dictionary):
    path = tmp_path / "good.json"
    path.write_text(sample_dictionary.model_dump_json(), encoding="utf-8")
    loaded = DictionaryLoader().load(str(path))
    assert isinstance(loaded, ExtractionDictionary)
    assert loaded.dictionary_id == sample_dictionary.dictionary_id
    assert len(loaded.items) == len(sample_dictionary.items)


def test_generator_produces_valid_dictionary(sample_parsed_document):
    profile = DocumentProfiler().profile(sample_parsed_document)
    chunks = ChunkingService().chunk(sample_parsed_document, profile)
    rep = select_representative_chunks(profile, chunks)

    service = DictionaryService()  # defaults to FakeLLMProvider
    dictionary = service.generate_proposed_dictionary(profile, rep)

    assert isinstance(dictionary, ExtractionDictionary)
    assert dictionary.items
    assert dictionary.document_id == sample_parsed_document.document_id


def test_generator_is_deterministic(sample_parsed_document):
    profile = DocumentProfiler().profile(sample_parsed_document)
    chunks = ChunkingService().chunk(sample_parsed_document, profile)
    rep = select_representative_chunks(profile, chunks)
    service = DictionaryService()
    d1 = service.generate_proposed_dictionary(profile, rep)
    d2 = service.generate_proposed_dictionary(profile, rep)
    assert d1.model_dump() == d2.model_dump()
