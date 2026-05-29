"""Candidate selector tests."""

from __future__ import annotations

from large_pdf_extractor.chunking.candidate_selector import CandidateSelector


def test_selector_returns_relevant_chunks(sample_chunks, sample_dictionary):
    selector = CandidateSelector()
    date_item = sample_dictionary.items[0]  # report_date, hints date/report
    selected = selector.select(date_item, sample_chunks)
    assert selected
    # Page 1 holds the report date and should be selected.
    assert any(c.page_start == 1 for c in selected)


def test_selector_always_returns_at_least_one(sample_chunks, sample_dictionary):
    selector = CandidateSelector()
    for item in sample_dictionary.items:
        assert selector.select(item, sample_chunks)


def test_selector_handles_empty_chunks(sample_dictionary):
    selector = CandidateSelector()
    assert selector.select(sample_dictionary.items[0], []) == []


def test_selector_respects_max_candidates(sample_chunks, sample_dictionary):
    selector = CandidateSelector(max_candidates=1)
    selected = selector.select(sample_dictionary.items[0], sample_chunks)
    assert len(selected) <= 1
