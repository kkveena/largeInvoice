"""Deterministic hashing helpers for document and chunk identity."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_text(text: str) -> str:
    """Return the hex sha256 of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str, length: int = 12) -> str:
    """Return a short, stable hash prefix for identifiers."""
    return sha256_text(text)[:length]


def file_document_id(pdf_path: str) -> str:
    """Build a stable document id from a file's name and content hash.

    The id is content-addressed so re-running on the same file yields the same
    document folder, while different files never collide.
    """
    path = Path(pdf_path)
    stem = path.stem.replace(" ", "_")
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    except OSError:
        digest = short_hash(str(path), 10)
    return f"{stem}-{digest}"
