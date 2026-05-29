"""Chunking and profiling tests."""

from __future__ import annotations

from large_pdf_extractor.chunking.chunker import ChunkingService
from large_pdf_extractor.profiling.document_profiler import (
    DocumentProfiler,
    select_representative_chunks,
)


def test_chunker_preserves_page_spans(sample_parsed_document):
    profile = DocumentProfiler().profile(sample_parsed_document)
    chunks = ChunkingService().chunk(sample_parsed_document, profile)
    assert chunks
    pages_seen = set()
    for chunk in chunks:
        assert chunk.page_start <= chunk.page_end
        assert chunk.page_start >= 1
        assert chunk.page_end <= sample_parsed_document.page_count
        assert chunk.source_spans
        assert chunk.source_spans[0].chunk_id == chunk.chunk_id
        pages_seen.add(chunk.page_start)
    # Every page with content produced at least one chunk.
    assert pages_seen == {1, 2}


def test_chunker_strips_repeated_headers(sample_parsed_document):
    profile = DocumentProfiler().profile(sample_parsed_document)
    # Header/footer should have been detected as repeated across the 2 pages.
    assert profile.repeated_header_candidates
    chunks = ChunkingService().chunk(sample_parsed_document, profile)
    joined = "\n".join(c.text for c in chunks)
    # The repeated header line should be stripped from chunk text.
    assert "ACME OPERATIONS DAILY BULLETIN" not in joined


def test_chunker_token_budget_splits_large_page(sample_parsed_document):
    # Force a tiny budget so the page must split into multiple pieces.
    chunker = ChunkingService(max_chunk_tokens=10, chunk_overlap_tokens=0)
    profile = DocumentProfiler().profile(sample_parsed_document)
    chunks = chunker.chunk(sample_parsed_document, profile)
    page1_chunks = [c for c in chunks if c.page_start == 1]
    assert len(page1_chunks) >= 2


def test_profiler_detects_tables_and_representatives(sample_parsed_document):
    profile = DocumentProfiler().profile(sample_parsed_document)
    assert profile.page_count == 2
    assert profile.total_char_count > 0
    assert profile.detected_table_count >= 1
    chunks = ChunkingService().chunk(sample_parsed_document, profile)
    rep = select_representative_chunks(profile, chunks)
    assert rep
    assert profile.representative_chunk_ids
    assert all(c.chunk_id in profile.representative_chunk_ids for c in rep)
