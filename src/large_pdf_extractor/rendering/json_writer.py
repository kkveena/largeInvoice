"""JSON writing helpers for Pydantic models and JSONL chunk streams."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ..domain.models import DocumentChunk


class JSONWriter:
    """Write Pydantic models to JSON and chunks to JSONL."""

    def write_model(self, model: BaseModel, path: str) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            model.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return str(out)

    def write_text(self, text: str, path: str) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return str(out)

    def write_chunks_jsonl(self, chunks: list[DocumentChunk], path: str) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for chunk in chunks:
                fh.write(chunk.model_dump_json())
                fh.write("\n")
        return str(out)

    def write_dict(self, data: dict, path: str) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(out)
