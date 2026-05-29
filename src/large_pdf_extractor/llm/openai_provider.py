"""Optional OpenAI provider.

The vendor SDK is imported lazily inside methods so importing this module never
requires the dependency. Used only when llm_provider="openai".
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import LLMError


class OpenAIProvider:
    """OpenAI provider (optional)."""

    name = "openai"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or os.getenv("LPE_OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set; cannot use OpenAIProvider.")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dep
            raise LLMError(f"openai not installed: {exc!r}") from exc

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return _loads(response.choices[0].message.content or "{}")


def _loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - depends on model
        raise LLMError(f"Provider did not return valid JSON: {exc!r}") from exc
