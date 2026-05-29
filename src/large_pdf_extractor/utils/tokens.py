"""Lightweight, dependency-free token estimation.

Phase 1 does not require an exact tokenizer. A stable heuristic is enough to
drive chunk-size decisions and comparison metrics. The estimate is intentionally
deterministic so tests and comparison reports are reproducible.
"""

from __future__ import annotations

# Rough average characters-per-token for English/financial text.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a string.

    Uses a blended heuristic of character count and whitespace word count so
    that dense numeric tables (few spaces) are not under-counted.
    """
    if not text:
        return 0
    char_based = len(text) / _CHARS_PER_TOKEN
    word_based = len(text.split())
    return max(1, int(round((char_based + word_based) / 2)))
