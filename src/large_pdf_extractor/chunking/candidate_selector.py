"""Candidate chunk selection.

For each dictionary item, deterministically score and select the chunks most
likely to contain the item's value, before any LLM call. Phase 1 logic is
simple keyword/structure matching; later phases may swap in embeddings.
"""

from __future__ import annotations

import re

from ..domain.models import DocumentChunk, ExtractionDictionaryItem, ExpectedValueType

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{2,}")

# Hints (configurable) that suggest a field is document-level metadata, which
# typically appears on the first pages. Domain-agnostic, generic terms.
_METADATA_SECTION_HINTS = {
    "metadata",
    "document",
    "header",
    "report",
    "summary",
    "overview",
    "cover",
}


class CandidateSelector:
    """Select relevant chunks per dictionary item.

    Designed to be an agent tool (`select_candidate_chunks`).
    """

    def __init__(self, max_candidates: int = 4, early_page_window: int = 3):
        self.max_candidates = max_candidates
        self.early_page_window = early_page_window

    def select(
        self,
        dictionary_item: ExtractionDictionaryItem,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        if not chunks:
            return []

        keywords = self._build_keywords(dictionary_item)
        is_metadata = self._is_metadata_field(dictionary_item)
        wants_table = dictionary_item.expected_type in (
            ExpectedValueType.TABLE,
            ExpectedValueType.LIST,
        )

        scored: list[tuple[float, int, DocumentChunk]] = []
        for order, chunk in enumerate(chunks):
            score = self._score(chunk, keywords, is_metadata, wants_table)
            if score > 0:
                scored.append((score, order, chunk))

        scored.sort(key=lambda t: (-t[0], t[1]))
        selected = [chunk for _, _, chunk in scored[: self.max_candidates]]

        # Guarantee at least one candidate so extraction always has context.
        if not selected:
            if is_metadata:
                selected = chunks[: min(self.max_candidates, len(chunks))]
            else:
                selected = [chunks[0]]
        return selected

    # -- scoring helpers --------------------------------------------------

    def _build_keywords(self, item: ExtractionDictionaryItem) -> list[str]:
        sources: list[str] = [
            item.entity_name,
            item.document_section,
            *item.examples,
            *item.candidate_selection_hints,
        ]
        keywords: list[str] = []
        for source in sources:
            for word in _WORD_RE.findall(source or ""):
                lowered = word.lower()
                if lowered not in keywords:
                    keywords.append(lowered)
        return keywords

    def _is_metadata_field(self, item: ExtractionDictionaryItem) -> bool:
        section = (item.document_section or "").lower()
        return any(hint in section for hint in _METADATA_SECTION_HINTS)

    def _score(
        self,
        chunk: DocumentChunk,
        keywords: list[str],
        is_metadata: bool,
        wants_table: bool,
    ) -> float:
        text = chunk.text.lower()
        heading = (chunk.heading or "").lower()

        score = 0.0
        for kw in keywords:
            if kw in text:
                score += 1.0
            if kw in heading:
                score += 1.5  # heading matches are stronger signals

        if wants_table and chunk.table_like:
            score += 2.0

        if is_metadata and chunk.page_start <= self.early_page_window:
            score += 2.0

        return score
