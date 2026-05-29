# Example Compare Run

This folder holds a committed example of a real pipeline run in `compare` mode
on the reference document `data/input/Metals_Option_Products.pdf`, produced with
the deterministic `FakeLLMProvider`.

It was generated with:

```bash
python -m large_pdf_extractor.cli.main extract \
  --pdf data/input/Metals_Option_Products.pdf \
  --output-dir data/output \
  --strategy compare \
  --llm-provider fake \
  --max-chunks 12
```

The large, fully reproducible full-text artifacts
(`parsed_document.pymupdf.json`, `chunks.*.jsonl`) are intentionally omitted to
keep the repository lean; re-run the command above to regenerate the complete
artifact set under `data/output/<document_id>/<run_id>/`.

Highlights to look at:

- `extraction_dictionary.used.json` — the dictionary built **before** extraction.
- `extraction_dictionary.used.xlsx` — the same dictionary as a shareable Excel
  workbook (for product managers / non-engineering reviewers).
- `extraction_result.pymupdf.md` / `.xlsx` — human-readable extracted values with
  page/chunk traceability.
- `comparison_report.md` — engineering comparison of the PyMuPDF vs Docling paths
  (Docling is gracefully skipped when the optional dependency is not installed).

Notes:

- Docling runs PyTorch models. On Apple Silicon (macOS/MPS) it can crash
  mid-inference, so `DoclingParser` defaults to the **CPU** accelerator. Override
  with `LPE_DOCLING_DEVICE=cpu|mps|cuda|auto`. A failure is always reported as a
  structured warning (never a blank result).
- Every run also emits `.xlsx` workbooks for the dictionary and the extraction
  results. You can also export any existing JSON with:
  `python -m large_pdf_extractor.cli.main export-excel --dictionary <path.json> --output <out.xlsx>`
