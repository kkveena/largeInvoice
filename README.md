# Large PDF Extractor - Phase 1

A generic large-PDF extraction framework that converts long, difficult PDFs into validated JSON and Markdown outputs using structured parsing, dictionary-first extraction, parser-aware chunking, and Pydantic models.

This Phase 1 project is designed for PDFs that are too large or too error-prone to pass directly into an LLM in one prompt. It supports both a fast PyMuPDF text path and a richer Docling path. The system compares both paths and continues to keep both available until later evaluation phases determine which approach is more reliable for a document family.

## Why This Exists

Large PDFs often fail with plain LLM extraction because:

- The document may exceed context limits.
- Dense tables lose structure.
- Repeated headers and footers confuse extraction.
- The model may mix unrelated sections.
- One-shot extraction is hard to validate.
- Source traceability is often missing.
- The extraction schema is often unclear or created too late.

The reference example for this project is a CME metals options daily bulletin. It contains repeated headers, many pages of tabular option data, product and expiration sections, volume, open interest, settlement price, delta, exercise count, and recurring disclaimers. The system should handle that pattern, but the implementation must remain generic for any large PDF.

## Core Design Decision: Dictionary First

## Domain Context: Finance Market Operations Technology

The first target document family is Finance / Markets / Operations Technology. Example documents may include market operations reports, trade lifecycle documents, futures/options bulletins, settlement or delivery reports, reconciliations, exception reports, margin/collateral reports, position/open-interest reports, regulatory/control documents, payment, settlement, clearing, and confirmation documents.

This context should help the system propose useful extraction dictionaries and candidate-selection hints. However, the implementation must remain generic. Finance-specific behavior should be represented through configurable dictionary templates, prompts, examples, and candidate-selection hints rather than hard-coded parser or extractor logic.

The system should be careful with raw financial and operational values. Preserve raw values and source page/chunk references. Only normalize values when the value type and meaning are unambiguous.


Phase 1 must build or load the extraction dictionary before final extraction.

The dictionary defines what the system is allowed to extract. It acts as the contract between the PDF, the extraction prompts, the JSON result, and the Markdown output.

The dictionary includes:

- `document_section`
- `entity_name`
- `description`
- `instruction_prompt`
- `expected_type`
- `required`
- `examples`
- `normalization_hint`
- `candidate_selection_hints`

The pipeline must not perform broad open-ended extraction and then retrofit the result into a schema. If the user does not provide a dictionary, the system proposes one first, validates it, saves it, and then uses it for extraction.

## Phase 1 Capabilities

Phase 1 implements:

- PDF loading and page-level parsing.
- `PyMuPDFTextParser` path.
- `DoclingParser` path.
- Document profiling.
- Dictionary-first proposed dictionary generation.
- User-supplied extraction dictionary support.
- Parser-aware chunking strategy.
- Candidate chunk selection per dictionary item.
- Dictionary-driven LLM extraction.
- Pydantic validation.
- JSON output.
- Markdown output.
- Source page and chunk traceability.
- Deterministic comparison of PyMuPDF vs Docling parser/chunking paths.
- Fake LLM provider for deterministic tests.

Future phases will add reliability scoring, offline evaluation, DSPy prompt optimization, chatbot/RAG, and full agentic workflows. Those are intentionally out of scope for Phase 1, but Phase 1 services are designed as future agent tools.

## High-Level Flow

```text
PDF
  -> Parser(s)
      -> ParsedDocument
          -> DocumentProfile
              -> Dictionary Generator or Dictionary Loader
                  -> ExtractionDictionary
                      -> Chunker
                          -> DocumentChunk[]
                              -> Candidate Selector
                                  -> Extraction Engine
                                      -> Pydantic ExtractionResult
                                          -> JSON Writer
                                          -> Markdown Renderer
```

In compare mode:

```text
PDF
  -> PyMuPDFTextParser -> profile -> chunks -> extraction result
  -> DoclingParser     -> profile -> chunks -> extraction result

Shared dictionary
  -> comparison_report.json
  -> comparison_report.md
```

## Parser and Chunking Comparison

Phase 1 compares two approaches:

1. `PyMuPDFTextParser`
   - Fast baseline.
   - Good for simple text extraction.
   - Useful for smoke tests and deterministic local development.

2. `DoclingParser`
   - Richer structure and table extraction.
   - Useful for layout-heavy documents.
   - May be heavier to install or run.

Both approaches must feed the same downstream contracts:

- `ParsedDocument`
- `DocumentProfile`
- `DocumentChunk[]`
- `ExtractionResult`

Comparison is not the same as Phase 2 online/offline evaluation. Phase 1 comparison is an engineering comparison that helps understand what each parser/chunking path preserves.

Comparison report fields include:

- parse runtime
- page count
- extracted character count
- low-text page count
- detected table count
- detected heading count
- chunk count
- average/max token estimate
- table-like chunk count
- repeated header/footer candidates
- candidate chunk coverage by dictionary item
- extracted field presence by dictionary item
- parser warnings/errors
- JSON diff summary between paths

## Installation

```bash
git clone <repo-url>
cd large-pdf-extractor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebook]"
```

Optional provider installs:

```bash
pip install -e ".[gemini]"
pip install -e ".[openai]"
```

Docling may have environment-specific dependencies. If Docling installation is not available, the PyMuPDF parser and fake LLM smoke tests must still work. Compare mode should report that Docling was skipped instead of failing the whole run.

## Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Example:

```env
LLM_PROVIDER=fake
GEMINI_API_KEY=
OPENAI_API_KEY=
MAX_CHUNK_TOKENS=4000
CHUNK_OVERLAP_TOKENS=300
DEFAULT_PARSE_STRATEGY=pymupdf
```



## Reference Files to Check Into the Repo

For the Phase 1 reference demonstration, place these files in the repository:

```text
data/input/Metals_Option_Products.pdf
data/input/metal_options_summary.rtf
```

These files are reference inputs only. The system must remain generic and must not hard-code CME, metals, options, futures, or finance-specific assumptions into the core pipeline.

## Required Fully Executed Demo Notebook

The repo must include a fully executed notebook:

```text
notebooks/01_phase1_cme_reference_demo.ipynb
```

This notebook is the showcase for Phase 1. It must run from top to bottom and prove that the pipeline works against the reference CME PDF using the dictionary-first approach.

The notebook must show:

- setup and input file validation;
- proposed dictionary generation before extraction;
- Pydantic validation of the dictionary;
- PyMuPDF parser/chunking path;
- Docling parser/chunking path when Docling is available;
- graceful Docling skip when Docling is unavailable;
- compare mode between `PyMuPDFTextParser` and `DoclingParser`;
- generated JSON and Markdown outputs;
- generated comparison reports;
- artifact existence checks;
- markdown preview cells;
- final pass/fail checklist.

The notebook should default to `FakeLLMProvider` so it can be executed without paid API calls. Gemini/OpenAI usage can be added as optional cells, but those cells must not be required for the default demo.

Example notebook run:

```bash
jupyter lab notebooks/01_phase1_cme_reference_demo.ipynb
```

Or execute it headlessly:

```bash
jupyter nbconvert \
  --to notebook \
  --execute notebooks/01_phase1_cme_reference_demo.ipynb \
  --output 01_phase1_cme_reference_demo.executed.ipynb
```

Phase 1 is not considered complete until the notebook has been executed successfully and the output cells demonstrate the generated artifacts.


## Command Line Usage

Run with PyMuPDF text parsing:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy pymupdf
```

Run with Docling parsing:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy docling
```

Run both parser/chunking paths and compare:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy compare
```

Generate only the proposed dictionary:

```bash
python -m large_pdf_extractor.cli.main propose-dictionary \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy pymupdf
```

Run with a provided extraction dictionary:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy compare \
  --dictionary data/samples/extraction_dictionary.json
```

Limit chunks during development:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/sample.pdf \
  --output-dir data/output \
  --strategy pymupdf \
  --max-chunks 5
```

## Output Layout

Each run writes to a document-specific folder:

```text
data/output/<document_id>/<run_id>/
  parsed_document.pymupdf.json
  document_profile.pymupdf.json
  chunks.pymupdf.jsonl
  extraction_dictionary.proposed.json
  extraction_dictionary.used.json
  extraction_result.pymupdf.json
  extraction_result.pymupdf.md
  comparison_report.json                 # compare mode only
  comparison_report.md                   # compare mode only
  run_metadata.json
```

If Docling is available and compare mode is used, the output also includes:

```text
  parsed_document.docling.json
  document_profile.docling.json
  chunks.docling.jsonl
  extraction_result.docling.json
  extraction_result.docling.md
```

## Extraction Dictionary

The extraction dictionary tells the system what to extract and how.

Example:

```json
{
  "dictionary_id": "sample_dictionary_v1",
  "document_id": null,
  "name": "Generic Market Bulletin Dictionary",
  "description": "Example fields for a tabular market bulletin. This is not hard-coded into the system.",
  "items": [
    {
      "item_id": "document_title",
      "document_section": "Document header",
      "entity_name": "Document Title",
      "description": "The official title of the document.",
      "instruction_prompt": "Extract the official document title exactly as shown in the header.",
      "expected_type": "string",
      "required": true,
      "examples": ["METALS OPTIONS PRODUCTS"],
      "normalization_hint": null,
      "candidate_selection_hints": ["header", "title", "first page"]
    },
    {
      "item_id": "table_metrics",
      "document_section": "Main data tables",
      "entity_name": "Table Metrics",
      "description": "Rows of table-level metrics such as volume, open interest, settlement price, and delta where present.",
      "instruction_prompt": "Extract visible table rows with their labels and raw numeric values. Preserve raw formatting when uncertain.",
      "expected_type": "table",
      "required": false,
      "examples": ["OPEN INTEREST", "SETT.PRICE", "DELTA", "GLOBEX VOLUME"],
      "normalization_hint": "Keep raw value and optionally parse numeric value when unambiguous.",
      "candidate_selection_hints": ["table", "open interest", "sett.price", "volume", "delta"]
    }
  ],
  "metadata": {}
}
```

The actual system should be able to propose a dictionary automatically from representative chunks and also accept a curated dictionary from the user.

## JSON Result Shape

`extraction_result.json` follows the `ExtractionResult` Pydantic model:

```json
{
  "document_id": "...",
  "dictionary_id": "...",
  "parse_strategy": "pymupdf",
  "values": [
    {
      "item_id": "document_title",
      "entity_name": "Document Title",
      "value": "METALS OPTIONS PRODUCTS",
      "raw_value": "METALS OPTIONS PRODUCTS",
      "normalized_value": null,
      "confidence": 0.95,
      "source_spans": [
        {
          "document_id": "...",
          "page_start": 1,
          "page_end": 1,
          "chunk_id": "chunk_0001",
          "char_start": null,
          "char_end": null,
          "bbox": null
        }
      ],
      "extraction_notes": null,
      "warnings": []
    }
  ],
  "unmapped_observations": [],
  "markdown_summary": "...",
  "metadata": {}
}
```

## Comparison Report Shape

`comparison_report.json` follows the `ComparisonReport` Pydantic model:

```json
{
  "document_id": "...",
  "dictionary_id": "...",
  "compared_strategies": ["pymupdf", "docling"],
  "parser_metrics": {
    "pymupdf": {
      "page_count": 60,
      "chunk_count": 120,
      "detected_table_count": 0,
      "table_like_chunk_count": 75,
      "warnings": []
    },
    "docling": {
      "page_count": 60,
      "chunk_count": 96,
      "detected_table_count": 42,
      "table_like_chunk_count": 42,
      "warnings": []
    }
  },
  "dictionary_item_coverage": {
    "document_title": {
      "pymupdf_candidate_chunks": 2,
      "docling_candidate_chunks": 2
    }
  },
  "extraction_presence_diff": {},
  "warnings": [],
  "recommendation_notes": []
}
```

## Future Agentic Compatibility

Phase 1 must be written so later phases can expose each operation as an agent tool.

Future tools may include:

- parse PDF
- profile document
- propose dictionary
- validate dictionary
- chunk document
- select candidate chunks
- extract dictionary item
- compare parser outputs
- ask document question
- score extraction reliability
- improve prompts using DSPy

For that reason, avoid hidden global state and monolithic scripts. Persist intermediate artifacts and use Pydantic models for run state.

## Development Workflow

Recommended order:

1. Create repository structure and Pydantic models.
2. Build `PyMuPDFTextParser`.
3. Build document profiler.
4. Build dictionary loader and sample dictionary.
5. Build fake dictionary generator.
6. Build chunking service.
7. Build candidate selector.
8. Build fake LLM extraction.
9. Build JSON and Markdown rendering.
10. Add Docling parser behind interface.
11. Add compare mode.
12. Add notebooks and tests.

## Definition of Done

Phase 1 is done when:

- A large PDF can run through PyMuPDF path.
- A large PDF can run through Docling path if Docling is installed.
- A proposed dictionary is generated before extraction when no dictionary is supplied.
- A supplied dictionary can be validated and used.
- Extraction results are Pydantic-validated.
- JSON and Markdown artifacts are produced.
- Compare mode produces `comparison_report.json` and `comparison_report.md`.
- Fake LLM tests run without paid API calls.
- Code structure can later be wrapped into an agentic workflow without rewriting the core services.
