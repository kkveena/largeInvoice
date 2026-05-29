"""Document profiler.

Summarizes a `ParsedDocument` into a `DocumentProfile` of structural signals
that downstream services (dictionary generation, chunking, comparison) consume.
All detection here is generic heuristics; no domain vocabulary is hard-coded.
"""

from __future__ import annotations

from ..domain.models import DocumentChunk, DocumentProfile, ParsedDocument
from ..utils.text import (
    detect_headings,
    non_empty_lines,
    repeated_line_candidates,
    table_like_ratio,
)

# A page with fewer characters than this is treated as empty/low-text.
LOW_TEXT_PAGE_THRESHOLD = 40
# A page whose lines are this table-like is counted as a "table page".
TABLE_PAGE_RATIO = 0.4


class DocumentProfiler:
    """Compute a representative profile of a parsed document.

    Designed to be an agent tool (`profile_document`).
    """

    def profile(self, parsed: ParsedDocument) -> DocumentProfile:
        page_lines: list[list[str]] = []
        total_chars = 0
        low_text_pages: list[int] = []
        detected_table_count = 0
        headings: list[str] = []

        for page in parsed.pages:
            text = page.text or ""
            total_chars += len(text)
            lines = non_empty_lines(text)
            page_lines.append(lines)

            if len(text.strip()) < LOW_TEXT_PAGE_THRESHOLD:
                low_text_pages.append(page.page_number)

            ratio = table_like_ratio(text)
            if ratio >= TABLE_PAGE_RATIO or page.tables:
                detected_table_count += 1

            for heading in detect_headings(text, limit=5):
                if heading not in headings:
                    headings.append(heading)

        header_candidates = repeated_line_candidates(page_lines, position="header")
        footer_candidates = repeated_line_candidates(page_lines, position="footer")

        representative_pages = self._representative_pages(parsed, low_text_pages)

        warnings = list(parsed.metadata.get("warnings", []))
        if parsed.metadata.get("skipped"):
            warnings.append(
                f"Parser '{parsed.strategy.value}' produced no pages (skipped)."
            )

        return DocumentProfile(
            document_id=parsed.document_id,
            strategy=parsed.strategy,
            page_count=parsed.page_count,
            total_char_count=total_chars,
            empty_or_low_text_pages=low_text_pages,
            detected_headings=headings[:25],
            detected_table_count=detected_table_count,
            repeated_header_candidates=header_candidates,
            repeated_footer_candidates=footer_candidates,
            representative_chunk_ids=[],  # filled in after chunking
            metadata={
                "representative_pages": representative_pages,
                "parse_runtime_seconds": parsed.metadata.get("parse_runtime_seconds"),
                "parser": parsed.metadata.get("parser"),
                "parser_version": parsed.metadata.get("parser_version"),
                "skipped": bool(parsed.metadata.get("skipped", False)),
                "warnings": warnings,
            },
        )

    def _representative_pages(
        self, parsed: ParsedDocument, low_text_pages: list[int]
    ) -> list[int]:
        """Pick a small, well-spread set of content-bearing page numbers.

        We always include the first page (document metadata typically lives
        there) plus an evenly spaced sample across the document.
        """
        content_pages = [
            p.page_number
            for p in parsed.pages
            if p.page_number not in set(low_text_pages)
        ]
        if not content_pages:
            content_pages = [p.page_number for p in parsed.pages]
        if not content_pages:
            return []

        wanted = min(5, len(content_pages))
        if wanted == 1:
            return content_pages[:1]

        step = max(1, (len(content_pages) - 1) // (wanted - 1))
        sampled: list[int] = []
        for i in range(0, len(content_pages), step):
            sampled.append(content_pages[i])
            if len(sampled) >= wanted:
                break
        if content_pages[0] not in sampled:
            sampled.insert(0, content_pages[0])
        return sorted(set(sampled))[:wanted]


def select_representative_chunks(
    profile: DocumentProfile, chunks: list[DocumentChunk], max_chunks: int = 6
) -> list[DocumentChunk]:
    """Select representative chunks from representative pages and update profile.

    Mutates ``profile.representative_chunk_ids`` so the profile artifact records
    which chunks fed dictionary generation. This is the bridge between the
    profiling and chunking steps.
    """
    rep_pages = set(profile.metadata.get("representative_pages", []))
    selected: list[DocumentChunk] = []
    seen: set[str] = set()

    # Prefer chunks overlapping representative pages.
    for chunk in chunks:
        if chunk.chunk_id in seen:
            continue
        pages = set(range(chunk.page_start, chunk.page_end + 1))
        if rep_pages & pages:
            selected.append(chunk)
            seen.add(chunk.chunk_id)
        if len(selected) >= max_chunks:
            break

    # Backfill with leading chunks if we are short.
    if len(selected) < max_chunks:
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                selected.append(chunk)
                seen.add(chunk.chunk_id)
            if len(selected) >= max_chunks:
                break

    profile.representative_chunk_ids = [c.chunk_id for c in selected]
    return selected
