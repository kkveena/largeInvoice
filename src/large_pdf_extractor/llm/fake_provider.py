"""Deterministic fake LLM provider.

Produces grounded, reproducible JSON for both dictionary proposal and
extraction tasks by reading the structured payload embedded in the prompt.
Requires no network and no API keys; this is the default provider for all
tests and the demo notebook.

The provider is document-type agnostic. Any domain-aware content (e.g. the
proposed dictionary categories) is supplied to it via the payload by the
calling service, not encoded here.
"""

from __future__ import annotations

import re
from typing import Any

from .base import LLMProvider, extract_payload

# Generic date patterns (no domain assumptions).
_DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{2,4}\b",
        re.IGNORECASE,
    ),
]
_NUMERIC_RE = re.compile(r"[-+]?\$?\d[\d,]*\.?\d*%?")
_BOOL_TRUE = ("yes", "true", "included", "enabled", "present")
_BOOL_FALSE = ("no", "false", "excluded", "disabled", "absent")
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{2,}")


class FakeLLMProvider:
    """Deterministic provider for local runs and tests."""

    name = "fake"

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = extract_payload(user_prompt)
        task = payload.get("task")
        if task == "propose_dictionary":
            return self._propose_dictionary(payload)
        if task == "extract":
            return self._extract(payload)
        # Unknown task: return an empty, schema-friendly object.
        return {}

    # -- dictionary proposal ---------------------------------------------

    def _propose_dictionary(self, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = payload.get("document_id")
        strategy = payload.get("strategy")
        # Items templates are supplied by the DictionaryService (configurable,
        # domain-aware). The fake provider only assembles them into the contract.
        items = payload.get("proposed_items", [])
        return {
            "dictionary_id": f"dict-{document_id}",
            "document_id": document_id,
            "name": "Proposed extraction dictionary",
            "description": (
                "Auto-proposed dictionary covering generic document metadata, "
                "dates, sections, identifiers, key metrics, statuses, totals, "
                "and disclaimers. Domain-aware but document-type agnostic."
            ),
            "generated_from_strategy": strategy,
            "items": items,
            "metadata": {"provider": self.name, "deterministic": True},
        }

    # -- extraction -------------------------------------------------------

    def _extract(self, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = payload.get("document_id")
        items = payload.get("items", [])
        candidates = payload.get("candidates", [])

        values: list[dict[str, Any]] = []
        for item in items:
            values.append(self._extract_one(document_id, item, candidates))

        return {
            "document_id": document_id,
            "values": values,
            "unmapped_observations": [],
        }

    def _extract_one(
        self,
        document_id: str,
        item: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        item_id = item.get("item_id")
        entity_name = item.get("entity_name", "")
        expected_type = item.get("expected_type", "string")
        keywords = self._keywords(item)

        for cand in candidates:
            text = cand.get("text", "") or ""
            match = self._find_value(text, keywords, expected_type)
            if match is not None:
                raw_value, line = match
                span = {
                    "document_id": document_id,
                    "page_start": cand.get("page_start", 1),
                    "page_end": cand.get("page_end", 1),
                    "chunk_id": cand.get("chunk_id"),
                }
                return {
                    "item_id": item_id,
                    "entity_name": entity_name,
                    "value": raw_value,
                    "raw_value": raw_value,
                    "normalized_value": None,
                    "confidence": 0.5,
                    "source_spans": [span],
                    "extraction_notes": (
                        f"Deterministic match on line: {line[:120]!r}"
                    ),
                    "warnings": [],
                }

        # Nothing found across candidate chunks.
        return {
            "item_id": item_id,
            "entity_name": entity_name,
            "value": None,
            "raw_value": None,
            "normalized_value": None,
            "confidence": 0.0,
            "source_spans": [],
            "extraction_notes": "No grounded value found in candidate chunks.",
            "warnings": ["value_not_found_in_candidates"],
        }

    # -- value detection helpers -----------------------------------------

    def _keywords(self, item: dict[str, Any]) -> list[str]:
        sources: list[str] = [item.get("entity_name", "")]
        sources.extend(item.get("candidate_selection_hints", []) or [])
        sources.extend(item.get("examples", []) or [])
        keywords: list[str] = []
        for source in sources:
            for word in _WORD_RE.findall(source or ""):
                lowered = word.lower()
                if lowered not in keywords:
                    keywords.append(lowered)
        return keywords

    def _find_value(
        self, text: str, keywords: list[str], expected_type: str
    ) -> tuple[str, str] | None:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # Prefer lines that mention one of the item keywords.
        keyword_lines = [
            ln for ln in lines if any(kw in ln.lower() for kw in keywords)
        ]
        search_order = keyword_lines + [ln for ln in lines if ln not in keyword_lines]

        for line in search_order:
            value = self._value_from_line(line, expected_type, keywords)
            if value is not None:
                return value, line
        return None

    def _value_from_line(
        self, line: str, expected_type: str, keywords: list[str]
    ) -> str | None:
        if expected_type == "date":
            for pat in _DATE_PATTERNS:
                m = pat.search(line)
                if m:
                    return m.group(0)
            return None
        if expected_type == "number":
            m = _NUMERIC_RE.search(line)
            return m.group(0) if m else None
        if expected_type == "boolean":
            lowered = line.lower()
            if any(t in lowered for t in _BOOL_TRUE):
                return "true"
            if any(t in lowered for t in _BOOL_FALSE):
                return "false"
            return None
        # string / list / table / object -> only return on a keyword hit so the
        # value is grounded rather than the first arbitrary line.
        if any(kw in line.lower() for kw in keywords):
            return line[:200]
        return None


# Static type check: FakeLLMProvider satisfies the LLMProvider protocol.
_PROTOCOL_CHECK: LLMProvider = FakeLLMProvider()
