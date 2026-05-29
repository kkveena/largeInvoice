"""Dictionary service: generate proposed dictionaries and load curated ones.

Dictionary-first is mandatory: this service runs before extraction. With the
FakeLLMProvider, generation is fully deterministic. Domain-aware hints come
from a configurable category template, never from core pipeline code.
"""

from __future__ import annotations

import copy
from typing import Any

from ..domain.models import (
    DocumentChunk,
    DocumentProfile,
    ExtractionDictionary,
    ParseStrategy,
)
from ..llm import embed_payload, get_provider
from ..llm.base import LLMProvider
from .loader import DictionaryLoader
from .prompts import (
    DEFAULT_CATEGORY_TEMPLATES,
    DICTIONARY_SYSTEM_PROMPT,
    DICTIONARY_USER_INSTRUCTIONS,
)


class DictionaryService:
    """Generate, load, and validate extraction dictionaries."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        category_templates: list[dict[str, Any]] | None = None,
    ):
        self.provider = provider or get_provider("fake")
        # Configurable + replaceable. Defaults are finance-ops-aware but generic.
        self.category_templates = category_templates or DEFAULT_CATEGORY_TEMPLATES
        self._loader = DictionaryLoader()

    def generate_proposed_dictionary(
        self,
        profile: DocumentProfile,
        representative_chunks: list[DocumentChunk],
    ) -> ExtractionDictionary:
        """Propose a dictionary from representative document signals.

        Builds a structured payload (profile signals + representative text +
        candidate item templates), asks the provider for a dictionary-only JSON
        response, then validates it with Pydantic.
        """
        proposed_items = self._build_candidate_items(profile, representative_chunks)
        payload = {
            "task": "propose_dictionary",
            "document_id": profile.document_id,
            "strategy": profile.strategy.value,
            "profile": {
                "page_count": profile.page_count,
                "detected_headings": profile.detected_headings[:15],
                "detected_table_count": profile.detected_table_count,
                "repeated_header_candidates": profile.repeated_header_candidates,
                "repeated_footer_candidates": profile.repeated_footer_candidates,
            },
            "representative_texts": [
                c.text[:1500] for c in representative_chunks[:6]
            ],
            "proposed_items": proposed_items,
        }
        user_prompt = embed_payload(DICTIONARY_USER_INSTRUCTIONS, payload)
        raw = self.provider.generate_json(DICTIONARY_SYSTEM_PROMPT, user_prompt)

        # Defensive defaults so a sparse provider response still validates.
        raw.setdefault("dictionary_id", f"dict-{profile.document_id}")
        raw.setdefault("document_id", profile.document_id)
        raw.setdefault("name", "Proposed extraction dictionary")
        raw.setdefault("description", "Auto-proposed dictionary.")
        raw.setdefault("generated_from_strategy", profile.strategy.value)
        if not raw.get("items"):
            raw["items"] = proposed_items

        return ExtractionDictionary.model_validate(raw)

    def load_dictionary(self, path: str) -> ExtractionDictionary:
        """Load and validate a curated dictionary from disk."""
        return self._loader.load(path)

    def validate_dictionary(self, data: Any) -> ExtractionDictionary:
        """Validate an in-memory dictionary (dict or model)."""
        return self._loader.validate(data)

    # -- internal helpers -------------------------------------------------

    def _build_candidate_items(
        self,
        profile: DocumentProfile,
        representative_chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """Tune the configurable templates with document-derived examples."""
        headings = profile.detected_headings[:5]
        items = copy.deepcopy(self.category_templates)
        for item in items:
            # Seed product/section examples from detected headings deterministically.
            if item["item_id"] == "product_or_business_section" and headings:
                item["examples"] = headings[:3]
            if item["item_id"] == "document_title" and headings:
                item["examples"] = headings[:1]
        return items
