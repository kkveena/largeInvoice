# Parser Path Comparison Report

- **Document ID:** `Metals_Option_Products-89ddba8c4b`
- **Dictionary ID:** `dict-Metals_Option_Products-89ddba8c4b`
- **Compared strategies:** pymupdf, docling

> This is a deterministic engineering comparison, not a formal accuracy evaluation.

## Parser Metrics

| Metric | pymupdf | docling |
|--------|------|------|
| parser_name | pymupdf | docling |
| skipped | False | True |
| parse_runtime_seconds | 0.3712 | None |
| page_count | 60 | 0 |
| extracted_char_count | 766344 | 0 |
| low_text_page_count | 0 | 0 |
| detected_table_count | 60 | 0 |
| detected_heading_count | 25 | 0 |
| chunk_count | 60 | 0 |
| avg_chunk_token_estimate | 2582.9 | 0 |
| max_chunk_token_estimate | 2942 | 0 |
| table_like_chunk_count | 60 | 0 |
| repeated_header_candidate_count | 3 | 0 |
| repeated_footer_candidate_count | 3 | 0 |
| warning_count | 0 | 2 |
| error_count | 0 | 0 |

## Dictionary Item Coverage (candidate chunks)

| Item | pymupdf | docling |
|------|------|------|
| `document_title` | 4 | 0 |
| `report_or_business_date` | 3 | 0 |
| `product_or_business_section` | 4 | 0 |
| `entity_identifiers` | 4 | 0 |
| `key_table_metrics` | 4 | 0 |
| `operational_status` | 4 | 0 |
| `exception_or_risk_indicators` | 4 | 0 |
| `totals_and_summary_values` | 4 | 0 |
| `disclaimers_or_caveats` | 1 | 0 |
| `source_table_references` | 4 | 0 |

## Extracted Field Presence

| Item | pymupdf | docling |
|------|------|------|
| `document_title` | ✓ | — |
| `report_or_business_date` | ✓ | — |
| `product_or_business_section` | ✓ | — |
| `entity_identifiers` | — | — |
| `key_table_metrics` | ✓ | — |
| `operational_status` | ✓ | — |
| `exception_or_risk_indicators` | ✓ | — |
| `totals_and_summary_values` | ✓ | — |
| `disclaimers_or_caveats` | — | — |
| `source_table_references` | — | — |

## Recommendation Notes

- Parser path 'docling' produced no pages and was treated as a graceful skip.
- Only 'pymupdf' ran successfully; comparison is single-sided.
- Raw-value agreement on 0/10 dictionary items across parser paths.

## Warnings

- [docling] Docling is not installed; Docling parser path was skipped.
- [docling] No chunks available for 'docling'; extraction skipped.
