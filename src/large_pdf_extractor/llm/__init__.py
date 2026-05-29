"""LLM provider layer with a small factory.

Vendor SDKs are only imported when their provider is actually constructed.
"""

from __future__ import annotations

from .base import LLMError, LLMProvider, embed_payload, extract_payload
from .fake_provider import FakeLLMProvider


def get_provider(name: str = "fake") -> LLMProvider:
    """Return an LLM provider by name. Defaults to the deterministic fake."""
    key = (name or "fake").lower()
    if key == "fake":
        return FakeLLMProvider()
    if key == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider()
    if key == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"Unknown LLM provider: {name!r}")


__all__ = [
    "LLMError",
    "LLMProvider",
    "FakeLLMProvider",
    "embed_payload",
    "extract_payload",
    "get_provider",
]
