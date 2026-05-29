"""CLI smoke tests using Typer's CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from large_pdf_extractor.cli.main import app

runner = CliRunner()


def test_cli_propose_dictionary(sample_pdf_path, tmp_path):
    result = runner.invoke(
        app,
        [
            "propose-dictionary",
            "--pdf",
            sample_pdf_path,
            "--output-dir",
            str(tmp_path),
            "--strategy",
            "pymupdf",
            "--llm-provider",
            "fake",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Proposed dictionary" in result.output


def test_cli_extract_pymupdf(sample_pdf_path, tmp_path):
    result = runner.invoke(
        app,
        [
            "extract",
            "--pdf",
            sample_pdf_path,
            "--output-dir",
            str(tmp_path),
            "--strategy",
            "pymupdf",
            "--llm-provider",
            "fake",
            "--max-chunks",
            "12",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Run complete" in result.output


def test_cli_compare(sample_pdf_path, tmp_path):
    result = runner.invoke(
        app,
        [
            "compare",
            "--pdf",
            sample_pdf_path,
            "--output-dir",
            str(tmp_path),
            "--llm-provider",
            "fake",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Compare run complete" in result.output


def test_cli_rejects_missing_pdf(tmp_path):
    result = runner.invoke(
        app,
        ["extract", "--pdf", str(tmp_path / "nope.pdf"), "--output-dir", str(tmp_path)],
    )
    assert result.exit_code != 0
