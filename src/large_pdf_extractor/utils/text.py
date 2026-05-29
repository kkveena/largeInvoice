"""Generic text utilities for profiling and chunking.

All helpers here are document-type agnostic heuristics. They detect structural
signals (headings, table-like rows, repeated lines) without assuming any
particular domain vocabulary.
"""

from __future__ import annotations

import re
from collections import Counter

_WHITESPACE_RE = re.compile(r"\s+")
# A run of 2+ spaces or a tab is a strong "column gap" signal in flattened PDF text.
_COLUMN_GAP_RE = re.compile(r"(\s{2,}|\t)")
_NUMERIC_TOKEN_RE = re.compile(r"[-+]?\$?\d[\d,]*\.?\d*%?")
# A line that is essentially a single short numeric/placeholder cell. PyMuPDF
# text extraction often flattens table columns into one such token per line.
_NUMERIC_ONLY_RE = re.compile(r"^[-+]?\$?\d[\d,]*\.?\d*%?$")
_PLACEHOLDER_CELLS = {"----", "---", "--", "unch", "new", "n/a", "nan"}


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip ends."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def non_empty_lines(text: str) -> list[str]:
    """Return stripped, non-empty lines."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def is_table_like_line(line: str) -> bool:
    """Heuristic: a line looks table-like if it has column gaps and numbers.

    Generic across domains: we look for multiple columns (large whitespace gaps)
    combined with several numeric tokens, which is typical of any tabular data.
    """
    if len(_COLUMN_GAP_RE.findall(line)) >= 2:
        return True
    numeric_tokens = _NUMERIC_TOKEN_RE.findall(line)
    return len(numeric_tokens) >= 3


def is_table_cell_line(line: str) -> bool:
    """A line that is a single flattened table cell (number or placeholder).

    Many parsers (notably PyMuPDF text mode) emit one table cell per line, so a
    high density of such lines is a strong table-region signal.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 12:
        return False
    if _NUMERIC_ONLY_RE.match(stripped):
        return True
    return stripped.lower() in _PLACEHOLDER_CELLS


def table_like_ratio(text: str) -> float:
    """Fraction of non-empty lines that look table-like (0.0-1.0).

    Counts both multi-column lines and dense single-cell numeric/placeholder
    lines so that column-flattened tables are still recognized.
    """
    lines = non_empty_lines(text)
    if not lines:
        return 0.0
    table_lines = sum(
        1 for ln in lines if is_table_like_line(ln) or is_table_cell_line(ln)
    )
    return table_lines / len(lines)


def looks_like_heading(line: str) -> bool:
    """Heuristic heading detector, domain agnostic.

    A heading is a short line that is not table-like and is either uppercase or
    title-cased without sentence-ending punctuation.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if is_table_like_line(stripped):
        return False
    if stripped.endswith((".", ",", ";", ":")):
        return False
    words = stripped.split()
    if len(words) > 10:
        return False
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio >= 0.7:
        return True
    # Title-case-ish: most words start capitalized.
    capitalized = sum(1 for w in words if w[:1].isupper())
    return capitalized >= max(1, int(0.7 * len(words)))


def detect_headings(text: str, limit: int = 25) -> list[str]:
    """Return candidate heading lines from a block of text."""
    headings: list[str] = []
    for line in non_empty_lines(text):
        if looks_like_heading(line) and line not in headings:
            headings.append(line)
            if len(headings) >= limit:
                break
    return headings


def repeated_line_candidates(
    page_lines: list[list[str]],
    position: str = "header",
    top_n_lines: int = 3,
    min_fraction: float = 0.4,
) -> list[str]:
    """Find lines repeated across many pages near the top (header) or bottom (footer).

    Args:
        page_lines: per-page list of non-empty lines.
        position: "header" (top of page) or "footer" (bottom of page).
        top_n_lines: how many lines from the edge to inspect per page.
        min_fraction: minimum fraction of pages a line must appear in.
    """
    if not page_lines:
        return []
    counter: Counter[str] = Counter()
    for lines in page_lines:
        if not lines:
            continue
        edge = lines[:top_n_lines] if position == "header" else lines[-top_n_lines:]
        for ln in set(normalize_whitespace(x) for x in edge):
            if ln:
                counter[ln] += 1
    threshold = max(2, int(min_fraction * len(page_lines)))
    candidates = [line for line, count in counter.most_common() if count >= threshold]
    return candidates


def keyword_overlap_score(text: str, keywords: list[str]) -> int:
    """Count how many keywords (case-insensitive) appear in text."""
    lowered = text.lower()
    return sum(1 for kw in keywords if kw and kw.lower() in lowered)
