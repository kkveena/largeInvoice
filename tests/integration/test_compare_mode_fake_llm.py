"""Integration test: compare mode produces a ComparisonReport even if Docling
is unavailable."""

from __future__ import annotations

from pathlib import Path

from large_pdf_extractor.app.config import build_run_config
from large_pdf_extractor.app.pipeline import Phase1Pipeline
from large_pdf_extractor.domain.models import ComparisonReport, ParseStrategy


def test_compare_mode_creates_comparison_report(sample_pdf_path, tmp_path):
    config = build_run_config(
        pdf_path=sample_pdf_path,
        output_dir=str(tmp_path),
        strategy=ParseStrategy.COMPARE,
        llm_provider="fake",
        max_chunks=12,
    )
    state = Phase1Pipeline(config).run()
    run_dir = Path(tmp_path) / state.document_id / state.run_id

    assert (run_dir / "comparison_report.json").exists()
    assert (run_dir / "comparison_report.md").exists()
    # Shared dictionary used across both paths.
    assert (run_dir / "extraction_dictionary.used.json").exists()
    # PyMuPDF artifacts present.
    assert (run_dir / "extraction_result.pymupdf.json").exists()
    # Docling artifacts present (skipped path still writes a result + parsed doc).
    assert (run_dir / "parsed_document.docling.json").exists()
    assert (run_dir / "extraction_result.docling.json").exists()

    report = ComparisonReport.model_validate_json(
        (run_dir / "comparison_report.json").read_text()
    )
    assert ParseStrategy.PYMUPDF in report.compared_strategies
    assert ParseStrategy.DOCLING in report.compared_strategies
    assert "pymupdf" in report.parser_metrics
    assert "docling" in report.parser_metrics


def test_compare_mode_shares_single_dictionary(sample_pdf_path, tmp_path):
    config = build_run_config(
        pdf_path=sample_pdf_path,
        output_dir=str(tmp_path),
        strategy=ParseStrategy.COMPARE,
        llm_provider="fake",
    )
    state = Phase1Pipeline(config).run()
    run_dir = Path(tmp_path) / state.document_id / state.run_id

    import json

    py = json.loads((run_dir / "extraction_result.pymupdf.json").read_text())
    dl = json.loads((run_dir / "extraction_result.docling.json").read_text())
    # Both paths reference the same dictionary id.
    assert py["dictionary_id"] == dl["dictionary_id"]
