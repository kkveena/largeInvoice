"""Dictionary loading and validation.

Curated dictionaries are loaded from JSON and validated with Pydantic. Invalid
dictionaries raise a clear error rather than silently degrading extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..domain.models import ExtractionDictionary


class DictionaryValidationError(ValueError):
    """Raised when a dictionary fails Pydantic validation."""


class DictionaryLoader:
    """Load and validate `ExtractionDictionary` objects."""

    def load(self, path: str) -> ExtractionDictionary:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dictionary file not found: {path}")
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DictionaryValidationError(
                f"Dictionary file is not valid JSON: {exc}"
            ) from exc
        return self.validate(data)

    def validate(self, data: Any) -> ExtractionDictionary:
        if isinstance(data, ExtractionDictionary):
            return data
        try:
            dictionary = ExtractionDictionary.model_validate(data)
        except ValidationError as exc:
            raise DictionaryValidationError(
                f"Dictionary failed schema validation: {exc}"
            ) from exc
        if not dictionary.items:
            raise DictionaryValidationError("Dictionary must contain at least one item.")
        return dictionary
