"""Dictionary-driven extraction engine.

Extracts only fields defined in the validated dictionary. Anything the provider
returns outside the dictionary item IDs is redirected to
``unmapped_observations``. Each value carries source spans for traceability.
"""

from __future__ import annotations

from typing import Any

from ..chunking.candidate_selector import CandidateSelector
from ..domain.models import (
    DocumentChunk,
    ExtractedValue,
    ExtractionDictionary,
    ExtractionDictionaryItem,
    ExtractionResult,
    ParseStrategy,
    SourceSpan,
)
from ..llm import embed_payload
from ..llm.base import LLMProvider
from .prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_INSTRUCTIONS


class ExtractionEngine:
    """Run dictionary-driven extraction over chunks.

    Designed to be an agent tool (`extract_values` / `extract_dictionary_item`).
    """

    def __init__(
        self,
        provider: LLMProvider,
        selector: CandidateSelector | None = None,
    ):
        self.provider = provider
        self.selector = selector or CandidateSelector()

    def extract(
        self,
        dictionary: ExtractionDictionary,
        chunks: list[DocumentChunk],
        strategy: ParseStrategy,
    ) -> ExtractionResult:
        values: list[ExtractedValue] = []
        unmapped: list[str] = []
        valid_item_ids = {item.item_id for item in dictionary.items}

        for item in dictionary.items:
            candidates = self.selector.select(item, chunks)
            value, extra_unmapped = self._extract_item(
                dictionary.document_id or (chunks[0].document_id if chunks else "unknown"),
                item,
                candidates,
                valid_item_ids,
            )
            values.append(value)
            unmapped.extend(extra_unmapped)

        document_id = dictionary.document_id or (
            chunks[0].document_id if chunks else "unknown"
        )
        return ExtractionResult(
            document_id=document_id,
            dictionary_id=dictionary.dictionary_id,
            parse_strategy=strategy,
            values=values,
            unmapped_observations=unmapped,
            metadata={"provider": getattr(self.provider, "name", "unknown")},
        )

    # -- internal --------------------------------------------------------

    def _extract_item(
        self,
        document_id: str,
        item: ExtractionDictionaryItem,
        candidates: list[DocumentChunk],
        valid_item_ids: set[str],
    ) -> tuple[ExtractedValue, list[str]]:
        payload = {
            "task": "extract",
            "document_id": document_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "entity_name": item.entity_name,
                    "expected_type": item.expected_type.value,
                    "document_section": item.document_section,
                    "examples": item.examples,
                    "candidate_selection_hints": item.candidate_selection_hints,
                }
            ],
            "candidates": [
                {
                    "chunk_id": c.chunk_id,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "text": c.text[:4000],
                }
                for c in candidates
            ],
        }
        user_prompt = embed_payload(EXTRACTION_USER_INSTRUCTIONS, payload)
        raw = self.provider.generate_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)

        unmapped = list(raw.get("unmapped_observations", []) or [])
        raw_values = raw.get("values", []) or []

        chosen: dict[str, Any] | None = None
        for rv in raw_values:
            rid = rv.get("item_id")
            if rid == item.item_id:
                chosen = rv
            elif rid not in valid_item_ids:
                # Provider returned an out-of-dictionary field: keep as observation.
                unmapped.append(
                    f"out-of-dictionary field '{rid}': {rv.get('value')!r}"
                )

        if chosen is None:
            return self._missing_value(item, "Provider returned no value for item."), unmapped

        return self._build_value(document_id, item, chosen), unmapped

    def _build_value(
        self, document_id: str, item: ExtractionDictionaryItem, rv: dict[str, Any]
    ) -> ExtractedValue:
        spans: list[SourceSpan] = []
        for span in rv.get("source_spans", []) or []:
            try:
                spans.append(
                    SourceSpan(
                        document_id=span.get("document_id", document_id),
                        page_start=int(span.get("page_start", 1)),
                        page_end=int(span.get("page_end", span.get("page_start", 1))),
                        chunk_id=span.get("chunk_id"),
                        char_start=span.get("char_start"),
                        char_end=span.get("char_end"),
                        bbox=span.get("bbox"),
                    )
                )
            except (TypeError, ValueError):
                continue

        return ExtractedValue(
            item_id=item.item_id,
            entity_name=item.entity_name,
            value=rv.get("value"),
            raw_value=rv.get("raw_value"),
            normalized_value=rv.get("normalized_value"),
            confidence=rv.get("confidence"),
            source_spans=spans,
            extraction_notes=rv.get("extraction_notes"),
            warnings=list(rv.get("warnings", []) or []),
        )

    def _missing_value(
        self, item: ExtractionDictionaryItem, note: str
    ) -> ExtractedValue:
        return ExtractedValue(
            item_id=item.item_id,
            entity_name=item.entity_name,
            value=None,
            confidence=0.0,
            source_spans=[],
            extraction_notes=note,
            warnings=["value_not_found"],
        )
