# agent.md - Claude Code Build Instructions

## Project Mission

Build Phase 1 of a generic large-PDF extraction system. The system must accept a large PDF, parse it safely, **build or load an extraction dictionary first**, chunk the document intelligently, extract structured values using LLMs, and produce validated JSON and Markdown outputs for UI consumption.

This project must be generic. The provided CME Metals Options Products bulletin is only a reference example of a difficult large PDF: repeated headers/footers, dense tabular data, many pages, recurring table schemas, option/futures product sections, expiration schedules, price/volume/open-interest columns, and repeated disclaimers. Do not hard-code CME, metals, options, or finance-specific assumptions into the core pipeline.

## Non-Negotiable Phase 1 Requirement: Dictionary First

## Domain Orientation: Finance Market Operations Technology

Most expected documents for this project are from Finance / Markets / Operations Technology. The system should therefore be friendly to dense financial and operational documents such as market operations reports, trade lifecycle documents, futures/options bulletins, settlement and delivery reports, reconciliations, exception reports, margin/collateral reports, position or open-interest reports, regulatory/control documents, payment reports, clearing documents, and confirmation documents.

This domain orientation should improve dictionary proposal hints and sample dictionaries, but the **core pipeline must remain generic**. Do not hard-code CME, metals, options, futures, settlement, clearing, or any single financial document type into the parser, chunker, extractor, renderer, or core Pydantic models.

Finance Market Ops documents often contain:

- dense tables and table-like text;
- repeated headers, footers, disclaimers, and control notes;
- product, contract, account, book, desk, legal entity, counterparty, and trade identifiers;
- dates such as business date, report date, trade date, settlement date, maturity date, and expiration date;
- numeric fields such as quantity, price, rate, notional, settlement amount, margin, collateral, exposure, variance, open interest, volume, delta, and P&L;
- operational statuses such as NEW, UNCH, amended, cancelled, failed, pending, settled, matched, unmatched, exception, rejected, or out-of-floor;
- caveats about data quality, operational controls, and legal disclaimers.

Phase 1 should preserve raw values and source page/chunk references. Normalized financial values should only be produced when unambiguous. Any finance-specific behavior must live in configurable hints, dictionary templates, examples, or prompts — not hidden inside core services.

Dictionary proposal for Finance Market Ops documents may include generic categories such as document metadata, business/report date, product or business section, entity identifiers, key table metrics, operational status, exception/risk indicators, totals and summary values, disclaimers/caveats, and source table references. These categories must remain configurable and replaceable.


The dictionary is the control contract for extraction. The system must not perform open-ended extraction first and then infer a schema afterward.

Phase 1 must follow this order:

```text
PDF
  -> parse with one or more parser strategies
  -> create representative profile of the document
  -> build or load extraction dictionary
  -> validate dictionary with Pydantic
  -> chunk document using parser-aware chunking
  -> select candidate chunks for each dictionary item
  -> extract values using the dictionary instructions
  -> validate JSON and render Markdown
```

Dictionary-first means:

1. If the user supplies a dictionary, validate it before extraction.
2. If the user does not supply a dictionary, generate a proposed dictionary from representative document samples before extraction.
3. Save the proposed dictionary as a first-class artifact.
4. Use the dictionary to drive candidate chunk selection, prompts, extraction result shape, and Markdown rendering.
5. Never let the LLM invent final output fields outside the validated dictionary, except in a clearly separated `unmapped_observations` section.

## Phase 1 Scope

Implement only Phase 1:

1. Load and inspect a PDF.
2. Extract text, layout, and tables through at least two parser strategies:
   - `PyMuPDFTextParser`: fast baseline text parser.
   - `DoclingParser`: layout/table-aware parser.
3. Generate a document profile from parser output.
4. Build a proposed extraction dictionary, or load a curated dictionary.
5. Validate the dictionary using Pydantic.
6. Chunk the document using parser-aware chunking.
7. Run dictionary-driven extraction.
8. Compare parser/chunking paths without making final accuracy claims.
9. Validate all outputs with Pydantic models.
10. Write final outputs as JSON and Markdown.
11. Save traceability metadata linking each extracted value to source pages/chunks.

Do not implement Phase 2 reliability scoring, DSPy optimization, chatbot, or full agentic orchestration yet. However, design every major step as a future agent/tool boundary.

## Required Parser and Chunking Comparison

Phase 1 must continue with both approaches until evaluation is introduced later:

1. `PyMuPDFTextParser` path.
2. `DoclingParser` path.

These are parser strategies, but each parser will influence chunking. Therefore implement a parser-aware comparison pipeline:

```text
PDF
  -> PyMuPDFTextParser
      -> ParsedDocument
      -> ChunkSet[pymupdf]
      -> Dictionary-driven extraction result[pymupdf]

PDF
  -> DoclingParser
      -> ParsedDocument
      -> ChunkSet[docling]
      -> Dictionary-driven extraction result[docling]

Both results
  -> ComparisonReport
```

The comparison is not Phase 2 evaluation. It is a deterministic engineering comparison to decide what each path preserves or loses.

Comparison must include:

- parser name and version if available
- parse runtime
- page count
- extracted character count
- empty/low-text page count
- detected table count
- detected heading/section count
- chunk count
- average and max chunk token estimate
- number of table-like chunks
- repeated header/footer candidates
- dictionary item coverage by candidate chunks
- extraction result field presence by dictionary item
- warnings and parser errors
- JSON diff summary between methods
- Markdown comparison summary

Save:

```text
comparison_report.json
comparison_report.md
```

The system should allow three run modes:

```text
--strategy pymupdf
--strategy docling
--strategy compare
```

Default local smoke tests should work with `--strategy pymupdf` and `FakeLLMProvider`. The `compare` mode should skip Docling gracefully if Docling is unavailable, but it must report that the Docling path was not run.

## Future Agentic Design Requirement

Even though Phase 1 is not a full agentic system, design it as if each step can later become a tool in an agentic workflow.

Every major operation should be callable independently:

- `parse_pdf`
- `profile_document`
- `generate_dictionary`
- `load_dictionary`
- `chunk_document`
- `select_candidate_chunks`
- `extract_values`
- `compare_parser_paths`
- `render_json`
- `render_markdown`

Avoid a monolithic script. The `Phase1Pipeline` should orchestrate these services, but each service must be testable and reusable. Later phases should be able to wrap these services as agent tools without rewriting core logic.

Use clear run-state models so a future agent can reason over intermediate artifacts:

- `RunConfig`
- `RunState`
- `PipelineStepResult`
- `ArtifactRef`
- `ComparisonReport`

## Non-Negotiable Design Principles

- Use Pydantic for every external and internal data contract.
- Build or load the extraction dictionary before final extraction.
- Never rely on one giant prompt over the whole PDF.
- Never assume a PDF has clean text extraction.
- Preserve page numbers and source references for every extracted value.
- Support large PDFs by chunking and incremental processing.
- Keep extraction schema generic and document-type agnostic.
- Separate parsing, profiling, dictionary generation, chunking, extraction, rendering, comparison, and storage.
- Make the system testable without paid LLM calls by supporting deterministic fake/stub LLM providers.
- Prefer simple, readable Python over complex frameworks in Phase 1.
- Design public services as future agent tools.

## Reference Document Pattern

The sample PDF demonstrates the following complexity classes that the generic system should handle:

- Multi-page financial bulletin.
- Repeated document headers.
- Product/contract sections.
- Expiration date grid near the beginning.
- Dense tables where column names span multiple lines.
- Mixed numeric formats, symbols, bid/ask suffixes, and placeholders like `----`, `UNCH`, `NEW`.
- Repeated legal disclaimer/footer text.
- Multiple product groups, option types, expiration months, strike rows, and summary totals.

The system should not attempt to perfectly normalize all domain values in Phase 1. It should preserve raw extracted values plus optional normalized values where confidence is high.

## Target Repository Structure

Create this structure:

```text
large-pdf-extractor/
  README.md
  architecture.md
  agent.md
  pyproject.toml
  .env.example
  .gitignore
  Makefile
  data/
    input/.gitkeep
    output/.gitkeep
    samples/.gitkeep
  notebooks/
    01_phase1_smoke_test.ipynb
    02_parser_comparison.ipynb
  src/
    large_pdf_extractor/
      __init__.py
      app/
        __init__.py
        pipeline.py
        config.py
        run_state.py
      cli/
        __init__.py
        main.py
      domain/
        __init__.py
        models.py
        enums.py
      parsing/
        __init__.py
        base.py
        pymupdf_text_parser.py
        docling_parser.py
      profiling/
        __init__.py
        document_profiler.py
      chunking/
        __init__.py
        chunker.py
        strategies.py
        candidate_selector.py
      dictionary/
        __init__.py
        generator.py
        loader.py
        prompts.py
      extraction/
        __init__.py
        prompts.py
        extractor.py
        merger.py
      comparison/
        __init__.py
        comparator.py
        diff.py
      llm/
        __init__.py
        base.py
        gemini_provider.py
        openai_provider.py
        fake_provider.py
      rendering/
        __init__.py
        markdown_renderer.py
        json_writer.py
      observability/
        __init__.py
        logging.py
      storage/
        __init__.py
        artifact_store.py
      utils/
        __init__.py
        hashing.py
        text.py
        tokens.py
  tests/
    unit/
      test_models.py
      test_chunking.py
      test_dictionary_loader.py
      test_candidate_selector.py
      test_comparator.py
      test_markdown_renderer.py
    integration/
      test_phase1_pipeline_fake_llm.py
      test_compare_mode_fake_llm.py
```



## Required Phase 1 Demo Notebook

Claude Code must create and execute a notebook that demonstrates the Phase 1 system end to end using the reference files that the user will place in the repository.

Expected input files:

```text
data/input/Metals_Option_Products.pdf
data/input/metal_options_summary.rtf
```

The notebook must be committed as:

```text
notebooks/01_phase1_cme_reference_demo.ipynb
```

The notebook must be fully executed before delivery. Do not leave unexecuted cells, placeholder outputs, or TODO-only cells. The notebook should run with `FakeLLMProvider` by default so it can be demonstrated without paid LLM calls. Optional Gemini/OpenAI cells may be included but must be clearly marked and skipped unless API keys are present.

The notebook must demonstrate:

1. Repository and environment setup checks.
2. Verification that the CME PDF and summary files exist in `data/input/`.
3. PDF inspection: page count, text sample, repeated header/footer candidates, table-like text indicators.
4. Dictionary-first flow:
   - generate a proposed dictionary from representative document profile/chunks;
   - validate the dictionary with Pydantic;
   - save `extraction_dictionary.proposed.json`;
   - reload the dictionary as `extraction_dictionary.used.json`.
5. PyMuPDF path:
   - parse;
   - profile;
   - chunk;
   - select candidate chunks;
   - extract with fake LLM;
   - write JSON and Markdown.
6. Docling path:
   - run if Docling is installed;
   - otherwise show a graceful skip record, not a notebook failure.
7. Compare mode:
   - compare PyMuPDF and Docling if both are available;
   - otherwise compare PyMuPDF against a structured skip result for Docling;
   - write `comparison_report.json` and `comparison_report.md`.
8. Output validation:
   - assert that core artifacts exist;
   - load JSON outputs back into Pydantic models;
   - display a small artifact summary table.
9. Markdown preview:
   - show the first portion of the extraction Markdown and comparison Markdown.
10. Final acceptance checklist cell showing pass/fail status.

The notebook is part of the Definition of Done. Phase 1 is not complete unless this notebook can run from top to bottom on the checked-in reference files.


## Recommended Python Stack

Use Python 3.11 or newer.

Core dependencies:

```toml
[project]
dependencies = [
  "pydantic>=2.7",
  "pydantic-settings>=2.2",
  "typer>=0.12",
  "rich>=13.7",
  "python-dotenv>=1.0",
  "pypdf>=4.2",
  "pymupdf>=1.24",
  "pandas>=2.2",
  "tabulate>=0.9",
  "docling>=2.0",
  "tenacity>=8.2",
]
```

Optional provider dependencies can be extras:

```toml
[project.optional-dependencies]
gemini = ["google-generativeai>=0.7"]
openai = ["openai>=1.40"]
dev = ["pytest>=8.2", "pytest-cov>=5.0", "ruff>=0.5", "mypy>=1.10"]
notebook = ["jupyterlab>=4.2", "ipywidgets>=8.1"]
```

If Docling installation is heavy or environment-specific, keep `DoclingParser` behind a clean interface and allow the smoke test to run with `PyMuPDFTextParser` and `FakeLLMProvider`.

## Core Pydantic Models

Implement the following model set in `domain/models.py`. Add fields as needed, but do not remove the core contracts.

```python
from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class ParseStrategy(str, Enum):
    PYMUPDF = "pymupdf"
    DOCLING = "docling"
    COMPARE = "compare"


class ChunkType(str, Enum):
    PAGE = "page"
    SECTION = "section"
    TABLE = "table"
    MIXED = "mixed"


class ExpectedValueType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"
    TABLE = "table"
    OBJECT = "object"


class ArtifactType(str, Enum):
    PARSED_DOCUMENT = "parsed_document"
    DOCUMENT_PROFILE = "document_profile"
    EXTRACTION_DICTIONARY = "extraction_dictionary"
    CHUNKS = "chunks"
    EXTRACTION_RESULT = "extraction_result"
    MARKDOWN_RESULT = "markdown_result"
    COMPARISON_REPORT = "comparison_report"
    RUN_METADATA = "run_metadata"


class SourceSpan(BaseModel):
    document_id: str
    page_start: int
    page_end: int
    chunk_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    bbox: list[float] | None = None


class ParsedPage(BaseModel):
    page_number: int
    text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    document_id: str
    filename: str
    page_count: int
    strategy: ParseStrategy
    pages: list[ParsedPage]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentProfile(BaseModel):
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
    dictionary_id: str
    document_id: str | None = None
    name: str
    description: str
    items: list[ExtractionDictionaryItem]
    generated_from_strategy: ParseStrategy | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedValue(BaseModel):
    item_id: str
    entity_name: str
    value: Any | None
    raw_value: str | None = None
    normalized_value: Any | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_spans: list[SourceSpan] = Field(default_factory=list)
    extraction_notes: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    document_id: str
    dictionary_id: str
    parse_strategy: ParseStrategy
    values: list[ExtractedValue]
    unmapped_observations: list[str] = Field(default_factory=list)
    markdown_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParserPathResult(BaseModel):
    strategy: ParseStrategy
    parsed_document: ParsedDocument | None = None
    document_profile: DocumentProfile | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    extraction_result: ExtractionResult | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ComparisonReport(BaseModel):
    document_id: str
    dictionary_id: str | None = None
    compared_strategies: list[ParseStrategy]
    parser_metrics: dict[str, dict[str, Any]]
    dictionary_item_coverage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    extraction_presence_diff: dict[str, dict[str, Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    recommendation_notes: list[str] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    artifact_type: ArtifactType
    path: str
    strategy: ParseStrategy | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunConfig(BaseModel):
    pdf_path: str
    output_dir: str
    strategy: ParseStrategy = ParseStrategy.PYMUPDF
    dictionary_path: str | None = None
    llm_provider: str = "fake"
    max_chunk_tokens: int = 4000
    chunk_overlap_tokens: int = 300
    max_chunks: int | None = None


class PipelineStepResult(BaseModel):
    step_name: str
    success: bool
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunState(BaseModel):
    run_id: str
    document_id: str
    config: RunConfig
    steps: list[PipelineStepResult] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## Required Services and Contracts

### Parser Interface

```python
class PDFParser(Protocol):
    strategy: ParseStrategy

    def parse(self, pdf_path: str) -> ParsedDocument:
        ...
```

### Dictionary Service

```python
class DictionaryService:
    def generate_proposed_dictionary(
        self,
        profile: DocumentProfile,
        representative_chunks: list[DocumentChunk],
    ) -> ExtractionDictionary:
        ...

    def load_dictionary(self, path: str) -> ExtractionDictionary:
        ...
```

### Chunking Service

```python
class ChunkingService:
    def chunk(self, parsed: ParsedDocument, profile: DocumentProfile) -> list[DocumentChunk]:
        ...
```

### Candidate Selector

```python
class CandidateSelector:
    def select(
        self,
        dictionary_item: ExtractionDictionaryItem,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        ...
```

### Comparator

```python
class ParserPathComparator:
    def compare(
        self,
        document_id: str,
        dictionary: ExtractionDictionary | None,
        results: list[ParserPathResult],
    ) -> ComparisonReport:
        ...
```

## Pipeline Behavior

### Single Strategy Mode

```text
parse -> profile -> dictionary -> chunk -> extract -> render
```

### Compare Mode

```text
for strategy in [pymupdf, docling]:
    parse -> profile -> chunk

build/load one dictionary:
    - if dictionary is provided, use it for both paths
    - if dictionary is not provided, generate a proposed dictionary from a combined representative profile

for strategy result:
    select chunks -> extract -> render strategy-specific result

compare both paths -> comparison_report.json/md
```

The dictionary must be shared across both parser paths in compare mode so that differences are caused by parser/chunking behavior, not by different extraction schemas.

## Prompt Requirements

### Dictionary Generation Prompt

The prompt must ask for a dictionary only. It must not ask for final extracted values.

It should instruct the LLM to return strict JSON with:

- `dictionary_id`
- `name`
- `description`
- `items`
- `document_section`
- `entity_name`
- `description`
- `instruction_prompt`
- `expected_type`
- `required`
- `examples`
- `normalization_hint`
- `candidate_selection_hints`

### Extraction Prompt

The extraction prompt must include:

- One dictionary item or a small group of related dictionary items.
- Candidate chunks only.
- Page/chunk IDs.
- Instruction to preserve raw values.
- Instruction to return strict JSON.
- Instruction to avoid fields outside the dictionary item IDs.

## CLI Requirements

Implement these commands:

```bash
large-pdf-extractor extract --pdf data/input/sample.pdf --output-dir data/output --strategy pymupdf
large-pdf-extractor extract --pdf data/input/sample.pdf --output-dir data/output --strategy docling
large-pdf-extractor extract --pdf data/input/sample.pdf --output-dir data/output --strategy compare
large-pdf-extractor propose-dictionary --pdf data/input/sample.pdf --output-dir data/output --strategy pymupdf
large-pdf-extractor compare --pdf data/input/sample.pdf --output-dir data/output --dictionary data/samples/extraction_dictionary.json
```

## Output Requirements

For a single parser strategy:

```text
data/output/<document_id>/<run_id>/
  parsed_document.<strategy>.json
  document_profile.<strategy>.json
  chunks.<strategy>.jsonl
  extraction_dictionary.proposed.json     # if generated
  extraction_dictionary.used.json
  extraction_result.<strategy>.json
  extraction_result.<strategy>.md
  run_metadata.json
```

For compare mode:

```text
data/output/<document_id>/<run_id>/
  parsed_document.pymupdf.json
  document_profile.pymupdf.json
  chunks.pymupdf.jsonl
  extraction_result.pymupdf.json
  extraction_result.pymupdf.md
  parsed_document.docling.json
  document_profile.docling.json
  chunks.docling.jsonl
  extraction_result.docling.json
  extraction_result.docling.md
  extraction_dictionary.used.json
  comparison_report.json
  comparison_report.md
  run_metadata.json
```

## Testing Requirements

Minimum tests:

1. Pydantic model validation.
2. Dictionary loader rejects invalid dictionary.
3. Dictionary generator output validates with fake LLM.
4. PyMuPDF parser returns a `ParsedDocument`.
5. Chunker preserves page spans.
6. Candidate selector returns relevant chunks for dictionary items.
7. Fake LLM extraction produces deterministic `ExtractionResult`.
8. Compare mode produces `ComparisonReport` even if Docling is unavailable.
9. Markdown renderer includes values and source spans.
10. No pipeline step requires vendor SDK unless that provider is selected.

## Definition of Done for Phase 1

Phase 1 is complete when Claude Code has produced:

- Working repository structure.
- Pydantic models.
- PyMuPDF parser.
- Docling parser behind a clean interface.
- Document profiler.
- Dictionary-first generation/loading path.
- Parser-aware chunking.
- Candidate chunk selection.
- Dictionary-driven extractor.
- Fake LLM provider.
- Optional Gemini/OpenAI providers behind interfaces.
- JSON and Markdown writers.
- Compare mode for PyMuPDF vs Docling parser/chunking paths.
- Comparison report artifacts.
- CLI commands.
- Smoke-test notebook.
- Parser comparison notebook.
- Unit and integration tests.
