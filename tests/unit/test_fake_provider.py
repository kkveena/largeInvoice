"""FakeLLMProvider determinism and grounding tests."""

from __future__ import annotations

from large_pdf_extractor.llm import embed_payload
from large_pdf_extractor.llm.fake_provider import FakeLLMProvider


def _extract_prompt(item, candidates):
    payload = {
        "task": "extract",
        "document_id": "doc-test",
        "items": [item],
        "candidates": candidates,
    }
    return embed_payload("extract", payload)


def test_fake_provider_deterministic():
    provider = FakeLLMProvider()
    item = {
        "item_id": "report_date",
        "entity_name": "report_date",
        "expected_type": "date",
        "candidate_selection_hints": ["date", "report"],
        "examples": [],
    }
    candidates = [
        {"chunk_id": "c1", "page_start": 1, "page_end": 1, "text": "Report Date: May 28, 2026"}
    ]
    prompt = _extract_prompt(item, candidates)
    out1 = provider.generate_json("sys", prompt)
    out2 = provider.generate_json("sys", prompt)
    assert out1 == out2


def test_fake_provider_grounds_date_value():
    provider = FakeLLMProvider()
    item = {
        "item_id": "report_date",
        "entity_name": "report_date",
        "expected_type": "date",
        "candidate_selection_hints": ["date"],
        "examples": [],
    }
    candidates = [
        {"chunk_id": "c1", "page_start": 3, "page_end": 3, "text": "Report Date: May 28, 2026"}
    ]
    out = provider.generate_json("sys", _extract_prompt(item, candidates))
    value = out["values"][0]
    assert value["raw_value"] == "May 28, 2026"
    assert value["source_spans"][0]["chunk_id"] == "c1"
    assert value["source_spans"][0]["page_start"] == 3


def test_fake_provider_reports_missing_value():
    provider = FakeLLMProvider()
    item = {
        "item_id": "report_date",
        "entity_name": "report_date",
        "expected_type": "date",
        "candidate_selection_hints": ["date"],
        "examples": [],
    }
    candidates = [
        {"chunk_id": "c1", "page_start": 1, "page_end": 1, "text": "no date here at all"}
    ]
    out = provider.generate_json("sys", _extract_prompt(item, candidates))
    value = out["values"][0]
    assert value["value"] is None
    assert "value_not_found_in_candidates" in value["warnings"]


def test_fake_provider_unknown_task_returns_empty():
    provider = FakeLLMProvider()
    assert provider.generate_json("sys", "no payload here") == {}
