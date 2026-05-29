"""Integration test: full single-strategy pipeline with FakeLLMProvider."""

from __future__ import annotations

import json
from pathlib import Path

from large_pdf_extractor.app.config import build_run_config
from large_pdf_extractor.app.pipeline import Phase1Pipeline
from large_pdf_extractor.domain.models import (
    ExtractionResult,
    ParseStrategy,
    RunState,
)


def test_pymupdf_pipeline_produces_all_artifacts(sample_pdf_path, tmp_path):
    config = build_run_config(
        pdf_path=sample_pdf_path,
        output_dir=str(tmp_path),
        strategy=ParseStrategy.PYMUPDF,
        llm_provider="fake",
        max_chunks=12,
    )
    state = Phase1Pipeline(config).run()
    assert isinstance(state, RunState)

    run_dir = Path(tmp_path) / state.document_id / state.run_id
    expected = [
        "parsed_document.pymupdf.json",
        "document_profile.pymupdf.json",
        "chunks.pymupdf.jsonl",
        "extraction_dictionary.proposed.json",
        "extraction_dictionary.used.json",
        "extraction_result.pymupdf.json",
        "extraction_result.pymupdf.md",
        "run_metadata.json",
    ]
    for name in expected:
        assert (run_dir / name).exists(), f"missing artifact: {name}"

    # Outputs validate back through Pydantic.
    result = ExtractionResult.model_validate_json(
        (run_dir / "extraction_result.pymupdf.json").read_text()
    )
    assert result.parse_strategy is ParseStrategy.PYMUPDF
    assert result.values

    # Dictionary-first: dictionary artifact exists and has items.
    used = json.loads((run_dir / "extraction_dictionary.used.json").read_text())
    assert used["items"]


def test_pipeline_with_provided_dictionary(
    sample_pdf_path, tmp_path, sample_dictionary
):
    dict_path = tmp_path / "curated.json"
    dict_path.write_text(sample_dictionary.model_dump_json(), encoding="utf-8")

    config = build_run_config(
        pdf_path=sample_pdf_path,
        output_dir=str(tmp_path / "out"),
        strategy=ParseStrategy.PYMUPDF,
        dictionary_path=str(dict_path),
        llm_provider="fake",
    )
    state = Phase1Pipeline(config).run()
    run_dir = Path(tmp_path / "out") / state.document_id / state.run_id

    # No proposed dictionary when a curated one is supplied.
    assert not (run_dir / "extraction_dictionary.proposed.json").exists()
    assert (run_dir / "extraction_dictionary.used.json").exists()

    result = ExtractionResult.model_validate_json(
        (run_dir / "extraction_result.pymupdf.json").read_text()
    )
    assert result.dictionary_id == sample_dictionary.dictionary_id
