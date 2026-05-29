"""Chunking layer: parser-aware chunker and candidate selector."""

from .candidate_selector import CandidateSelector
from .chunker import ChunkingService

__all__ = ["CandidateSelector", "ChunkingService"]
