"""Parser-aware chunking engine.

Converts a `ParsedDocument` + `DocumentProfile` into `DocumentChunk` objects.
The same `DocumentChunk` contract is produced regardless of parser, but the
chunker uses profile signals (repeated headers/footers, table indicators) so
the two parser paths can be compared fairly.
"""

from __future__ import annotations

from ..domain.models import (
    ChunkType,
    DocumentChunk,
    DocumentProfile,
    ParsedDocument,
    SourceSpan,
)
from ..utils.text import (
    detect_headings,
    normalize_whitespace,
    table_like_ratio,
)
from ..utils.tokens import estimate_tokens
from .strategies import split_by_token_budget, strip_repeated_lines

TABLE_LIKE_THRESHOLD = 0.4


class ChunkingService:
    """Build parser-aware chunks. Designed to be an agent tool (`chunk_document`)."""

    def __init__(self, max_chunk_tokens: int = 4000, chunk_overlap_tokens: int = 300):
        self.max_chunk_tokens = max_chunk_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens

    def chunk(
        self, parsed: ParsedDocument, profile: DocumentProfile
    ) -> list[DocumentChunk]:
        repeated = {
            normalize_whitespace(x)
            for x in (
                profile.repeated_header_candidates
                + profile.repeated_footer_candidates
            )
        }

        chunks: list[DocumentChunk] = []
        for page in parsed.pages:
            raw_text = page.text or ""
            cleaned = strip_repeated_lines(raw_text, repeated).strip()
            if not cleaned:
                # Preserve an empty placeholder so page spans stay continuous.
                cleaned = raw_text.strip()
            if not cleaned:
                continue

            page_is_table = bool(page.tables) or table_like_ratio(cleaned) >= TABLE_LIKE_THRESHOLD
            heading = self._page_heading(cleaned)

            pieces = split_by_token_budget(
                cleaned, self.max_chunk_tokens, self.chunk_overlap_tokens
            )
            for piece_index, piece in enumerate(pieces):
                chunk_index = len(chunks)
                piece_is_table = (
                    page_is_table
                    or table_like_ratio(piece) >= TABLE_LIKE_THRESHOLD
                )
                chunk_id = f"{parsed.strategy.value}-c{chunk_index:04d}-p{page.page_number}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=parsed.document_id,
                        parser_strategy=parsed.strategy,
                        chunk_type=ChunkType.TABLE if piece_is_table else ChunkType.PAGE,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        text=piece,
                        token_estimate=estimate_tokens(piece),
                        heading=heading if piece_index == 0 else None,
                        table_like=piece_is_table,
                        source_spans=[
                            SourceSpan(
                                document_id=parsed.document_id,
                                page_start=page.page_number,
                                page_end=page.page_number,
                                chunk_id=chunk_id,
                            )
                        ],
                        metadata={
                            "piece_index": piece_index,
                            "piece_count": len(pieces),
                            "char_count": len(piece),
                        },
                    )
                )
        return chunks

    def _page_heading(self, text: str) -> str | None:
        headings = detect_headings(text, limit=1)
        return headings[0] if headings else None
