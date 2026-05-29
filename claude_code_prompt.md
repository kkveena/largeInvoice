# Claude Code Prompt - Build Phase 1 Large PDF Extractor

You are building Phase 1 of a generic large-PDF extraction system.

## Files I am providing in the repo

I will include the following project guidance files at the repo root:

- `agent.md`
- `README.md`
- `architecture.md`

I will also include the reference input files under `data/input/`:

- `data/input/Metals_Option_Products.pdf`
- `data/input/metal_options_summary.rtf`

The CME files are reference examples only. Do not hard-code CME, metals, options, futures, or finance-specific assumptions into the core pipeline. The system must remain generic for large PDFs.

## Mission

Implement Phase 1 only.

Build a dictionary-first large-PDF extraction pipeline that:

1. Parses a large PDF without sending the whole document to an LLM in one prompt.
2. Builds or loads an extraction dictionary before final extraction.
3. Validates all contracts using Pydantic.
4. Chunks the document intelligently.
5. Extracts dictionary-driven values into JSON and Markdown.
6. Compares two parser/chunking approaches:
   - `PyMuPDFTextParser`
   - `DoclingParser`
7. Keeps both approaches available until later online/offline evaluation phases decide which is better.
8. Produces source traceability for extracted values.
9. Is designed so each major step can later become an agentic tool.

## Critical design rule: dictionary first

The pipeline sequence must be:

```text
PDF
  -> parse/profile
  -> propose or load extraction dictionary
  -> validate dictionary
  -> chunk/select candidate chunks
  -> extract values
  -> validate outputs
  -> render JSON and Markdown
```

Do not do broad open-ended extraction first and retrofit the result into a schema.

## Required parser/chunking comparison

Implement these strategies:

```bash
--strategy pymupdf
--strategy docling
--strategy compare
```

Compare mode must run both paths where possible and create:

```text
comparison_report.json
comparison_report.md
```

If Docling is unavailable, do not fail the whole run. Record a graceful skip/warning in the comparison report.

## Required notebook

Create this notebook:

```text
notebooks/01_phase1_cme_reference_demo.ipynb
```

The notebook must be fully executed before delivery. It must showcase Phase 1 using:

```text
data/input/Metals_Option_Products.pdf
data/input/metal_options_summary.rtf
```

The notebook must demonstrate:

1. Input file validation.
2. Document/profile inspection.
3. Dictionary proposal before extraction.
4. Pydantic dictionary validation.
5. PyMuPDF parse/chunk/extract path.
6. Docling parse/chunk/extract path or graceful skip.
7. Compare mode.
8. Generated JSON and Markdown artifacts.
9. Pydantic reload/validation of outputs.
10. Markdown preview.
11. Final pass/fail checklist.

The default notebook run must use `FakeLLMProvider`, so it works without paid API calls. Optional Gemini/OpenAI cells may be included only if they are skipped when API keys are not present.

## Implementation guidance

Use the architecture and model contracts in `agent.md` and `architecture.md` as the source of truth.

Build in this order:

1. Repo structure, `pyproject.toml`, `.gitignore`, `.env.example`, `Makefile`.
2. Pydantic domain models.
3. Artifact store and run-state models.
4. Parser interfaces.
5. `PyMuPDFTextParser`.
6. `DoclingParser` with graceful fallback.
7. Document profiler.
8. Dictionary loader/generator/validator.
9. Parser-aware chunker.
10. Candidate selector.
11. Fake LLM provider.
12. Extraction engine.
13. JSON and Markdown renderers.
14. Parser-path comparator.
15. Typer CLI.
16. Unit and integration tests.
17. Fully executed notebook.

## Acceptance criteria

Before finishing, run:

```bash
pytest
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/Metals_Option_Products.pdf \
  --output-dir data/output \
  --strategy pymupdf \
  --llm-provider fake \
  --max-chunks 12

python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/Metals_Option_Products.pdf \
  --output-dir data/output \
  --strategy compare \
  --llm-provider fake \
  --max-chunks 12

jupyter nbconvert \
  --to notebook \
  --execute notebooks/01_phase1_cme_reference_demo.ipynb \
  --output 01_phase1_cme_reference_demo.executed.ipynb
```

Deliver the working repo with generated example outputs under `data/output/` or a documented sample output folder. The notebook must show executed output cells.
