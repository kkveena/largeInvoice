"""Extraction prompts.

The extraction prompt is dictionary-driven and chunk-scoped: it includes only a
small group of related dictionary items and only the candidate chunks, never the
whole document. It instructs the model to preserve raw values, return strict
JSON, and never invent fields outside the provided item IDs.
"""

from __future__ import annotations

EXTRACTION_SYSTEM_PROMPT = (
    "You are a precise extraction engine. Extract ONLY the dictionary items "
    "given to you, using ONLY the provided candidate chunks. Preserve raw "
    "values exactly as they appear. Attach source spans (chunk_id, page range). "
    "Never return fields whose item_id is not in the provided list. Return "
    "strict JSON. If a value is not present in the candidate chunks, return it "
    "with value=null and a warning rather than guessing."
)

EXTRACTION_USER_INSTRUCTIONS = (
    "Extract the requested dictionary items from the candidate chunks. Return "
    "strict JSON with keys: document_id, values, unmapped_observations. Each "
    "value must include: item_id, entity_name, value, raw_value, "
    "normalized_value, confidence, source_spans, extraction_notes, warnings. "
    "Only include item_ids from the provided items list."
)
