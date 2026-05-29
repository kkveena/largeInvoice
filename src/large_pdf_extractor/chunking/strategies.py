"""Chunking helper strategies.

These functions hold reusable, parser-agnostic chunk-building logic so the
chunker stays readable. They are pure functions over text.
"""

from __future__ import annotations

from ..utils.text import normalize_whitespace
from ..utils.tokens import estimate_tokens


def strip_repeated_lines(text: str, repeated: set[str]) -> str:
    """Remove lines that match known repeated header/footer text."""
    if not repeated:
        return text
    kept = []
    for line in text.splitlines():
        if normalize_whitespace(line) in repeated:
            continue
        kept.append(line)
    return "\n".join(kept)


def split_by_token_budget(
    text: str, max_tokens: int, overlap_tokens: int
) -> list[str]:
    """Split text into pieces that each fit roughly within ``max_tokens``.

    Splits on line boundaries to preserve table rows, and applies a small line
    overlap so narrative context is not lost across boundaries.
    """
    if estimate_tokens(text) <= max_tokens:
        return [text]

    lines = text.splitlines()
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0

    overlap_lines = max(1, overlap_tokens // 20) if overlap_tokens else 0

    for line in lines:
        line_tokens = estimate_tokens(line) + 1
        if current and current_tokens + line_tokens > max_tokens:
            pieces.append("\n".join(current))
            # Seed the next piece with a few trailing lines for overlap.
            tail = current[-overlap_lines:] if overlap_lines else []
            current = list(tail)
            current_tokens = sum(estimate_tokens(x) + 1 for x in current)
        current.append(line)
        current_tokens += line_tokens

    if current:
        pieces.append("\n".join(current))
    return [p for p in pieces if p.strip()]
