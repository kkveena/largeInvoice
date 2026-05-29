"""Typer CLI for the Phase 1 large-PDF extractor.

Commands:
    propose-dictionary  Build/propose a dictionary (dictionary-first), no extraction.
    extract             Run the full pipeline for one strategy or compare mode.
    compare             Run compare mode (PyMuPDF vs Docling).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..app.config import build_run_config
from ..app.pipeline import Phase1Pipeline
from ..domain.models import ArtifactType, ParseStrategy
from ..parsing import get_parser
from ..profiling.document_profiler import DocumentProfiler, select_representative_chunks
from ..chunking.chunker import ChunkingService
from ..dictionary.generator import DictionaryService
from ..llm import get_provider
from ..storage.artifact_store import ArtifactStore
from ..utils.hashing import file_document_id
from ..app.run_state import new_run_id

app = typer.Typer(
    add_completion=False,
    help="Phase 1 generic large-PDF extraction system (dictionary-first).",
)
console = Console()


def _parse_strategy(value: str) -> ParseStrategy:
    try:
        return ParseStrategy(value)
    except ValueError as exc:
        raise typer.BadParameter(
            f"Unknown strategy '{value}'. Use pymupdf | docling | compare."
        ) from exc


def _summarize_run(state) -> None:
    table = Table(title=f"Run {state.run_id} — artifacts")
    table.add_column("Artifact type")
    table.add_column("Strategy")
    table.add_column("Path")
    for ref in state.artifacts:
        table.add_row(
            ref.artifact_type.value,
            ref.strategy.value if ref.strategy else "-",
            ref.path,
        )
    console.print(table)


@app.command("propose-dictionary")
def propose_dictionary(
    pdf: str = typer.Option(..., help="Path to the input PDF."),
    output_dir: str = typer.Option("data/output", help="Output directory."),
    strategy: str = typer.Option("pymupdf", help="Parser strategy: pymupdf | docling."),
    llm_provider: str = typer.Option("fake", help="LLM provider: fake | gemini | openai."),
) -> None:
    """Propose and save an extraction dictionary (no extraction performed)."""
    strat = _parse_strategy(strategy)
    if strat == ParseStrategy.COMPARE:
        raise typer.BadParameter("propose-dictionary requires a single strategy.")
    if not Path(pdf).exists():
        raise typer.BadParameter(f"PDF not found: {pdf}")

    document_id = file_document_id(pdf)
    run_id = new_run_id()
    store = ArtifactStore(output_dir, document_id, run_id)
    provider = get_provider(llm_provider)

    parser = get_parser(strat)
    parsed = parser.parse(pdf)
    profiler = DocumentProfiler()
    profile = profiler.profile(parsed)
    chunker = ChunkingService()
    chunks = chunker.chunk(parsed, profile)
    representative = select_representative_chunks(profile, chunks)

    service = DictionaryService(provider=provider)
    dictionary = service.generate_proposed_dictionary(profile, representative)

    proposed_ref = store.write_model(
        dictionary,
        "extraction_dictionary.proposed.json",
        ArtifactType.EXTRACTION_DICTIONARY,
    )
    used_ref = store.write_model(
        dictionary,
        "extraction_dictionary.used.json",
        ArtifactType.EXTRACTION_DICTIONARY,
    )
    excel_ref = store.write_dictionary_excel(
        dictionary, "extraction_dictionary.used.xlsx"
    )

    console.print(
        f"[green]Proposed dictionary with {len(dictionary.items)} items.[/green]"
    )
    console.print(f"  proposed: {proposed_ref.path}")
    console.print(f"  used:     {used_ref.path}")
    console.print(f"  excel:    {excel_ref.path}")


@app.command("extract")
def extract(
    pdf: str = typer.Option(..., help="Path to the input PDF."),
    output_dir: str = typer.Option("data/output", help="Output directory."),
    strategy: str = typer.Option("pymupdf", help="pymupdf | docling | compare."),
    dictionary: str | None = typer.Option(None, help="Path to a curated dictionary JSON."),
    llm_provider: str = typer.Option("fake", help="LLM provider: fake | gemini | openai."),
    max_chunks: int | None = typer.Option(None, help="Max chunks to process for extraction."),
) -> None:
    """Run the dictionary-first extraction pipeline."""
    strat = _parse_strategy(strategy)
    if not Path(pdf).exists():
        raise typer.BadParameter(f"PDF not found: {pdf}")

    config = build_run_config(
        pdf_path=pdf,
        output_dir=output_dir,
        strategy=strat,
        dictionary_path=dictionary,
        llm_provider=llm_provider,
        max_chunks=max_chunks,
    )
    pipeline = Phase1Pipeline(config)
    state = pipeline.run()

    console.print(
        f"[green]Run complete:[/green] {state.run_id} "
        f"({len(state.artifacts)} artifacts, strategy={strat.value})"
    )
    _summarize_run(state)


@app.command("compare")
def compare(
    pdf: str = typer.Option(..., help="Path to the input PDF."),
    output_dir: str = typer.Option("data/output", help="Output directory."),
    dictionary: str | None = typer.Option(None, help="Path to a curated dictionary JSON."),
    llm_provider: str = typer.Option("fake", help="LLM provider: fake | gemini | openai."),
    max_chunks: int | None = typer.Option(None, help="Max chunks to process for extraction."),
) -> None:
    """Compare PyMuPDF and Docling parser/chunking paths."""
    if not Path(pdf).exists():
        raise typer.BadParameter(f"PDF not found: {pdf}")

    config = build_run_config(
        pdf_path=pdf,
        output_dir=output_dir,
        strategy=ParseStrategy.COMPARE,
        dictionary_path=dictionary,
        llm_provider=llm_provider,
        max_chunks=max_chunks,
    )
    pipeline = Phase1Pipeline(config)
    state = pipeline.run()

    console.print(f"[green]Compare run complete:[/green] {state.run_id}")
    _summarize_run(state)


@app.command("export-excel")
def export_excel(
    dictionary: str | None = typer.Option(
        None, help="Path to a dictionary JSON to export to Excel."
    ),
    extraction: str | None = typer.Option(
        None, help="Path to an extraction_result JSON to export to Excel."
    ),
    output: str | None = typer.Option(
        None, help="Output .xlsx path (defaults next to the input JSON)."
    ),
) -> None:
    """Export an existing dictionary or extraction-result JSON to Excel (.xlsx).

    Handy for sharing the extraction dictionary or results with non-engineering
    stakeholders without re-running the pipeline.
    """
    from ..domain.models import ExtractionDictionary, ExtractionResult
    from ..rendering.excel_writer import ExcelExporter

    if not dictionary and not extraction:
        raise typer.BadParameter("Provide --dictionary and/or --extraction.")

    exporter = ExcelExporter()

    if dictionary:
        src = Path(dictionary)
        if not src.exists():
            raise typer.BadParameter(f"Dictionary JSON not found: {dictionary}")
        model = ExtractionDictionary.model_validate_json(src.read_text())
        out = output if (output and extraction is None) else str(src.with_suffix(".xlsx"))
        path = exporter.export_dictionary(model, out)
        console.print(f"[green]Dictionary Excel written:[/green] {path}")

    if extraction:
        src = Path(extraction)
        if not src.exists():
            raise typer.BadParameter(f"Extraction JSON not found: {extraction}")
        model = ExtractionResult.model_validate_json(src.read_text())
        out = output if (output and dictionary is None) else str(src.with_suffix(".xlsx"))
        path = exporter.export_extraction_result(model, out)
        console.print(f"[green]Extraction Excel written:[/green] {path}")


if __name__ == "__main__":
    app()
