"""Optional Gemini provider.

The vendor SDK is imported lazily inside methods so that importing this module
never requires the dependency. Used only when llm_provider="gemini".
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import LLMError


class GeminiProvider:
    """Google Gemini provider (optional)."""

    name = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or os.getenv("LPE_GEMINI_MODEL", "gemini-1.5-flash")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("GOOGLE_API_KEY is not set; cannot use GeminiProvider.")
        try:
            import google.generativeai as genai
        except Exception as exc:  # pragma: no cover - optional dep
            raise LLMError(f"google-generativeai not installed: {exc!r}") from exc

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(user_prompt)
        return _loads(response.text)


def _loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - depends on model
        raise LLMError(f"Provider did not return valid JSON: {exc!r}") from exc
