"""Artifact store.

Owns the on-disk layout for a run: data/output/<document_id>/<run_id>/...
Returns `ArtifactRef` objects so run state stays serializable and future agents
can locate every produced artifact.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..domain.models import (
    ArtifactRef,
    ArtifactType,
    DocumentChunk,
    ExtractionDictionary,
    ExtractionResult,
    ParseStrategy,
)
from ..rendering.excel_writer import ExcelExporter
from ..rendering.json_writer import JSONWriter


class ArtifactStore:
    """Filesystem-backed artifact store for a single run."""

    def __init__(self, output_dir: str, document_id: str, run_id: str):
        self.base = Path(output_dir) / document_id / run_id
        self.document_id = document_id
        self.run_id = run_id
        self._writer = JSONWriter()
        self._excel = ExcelExporter()
        self.base.mkdir(parents=True, exist_ok=True)

    def path_for(self, filename: str) -> str:
        return str(self.base / filename)

    def write_model(
        self,
        model: BaseModel,
        filename: str,
        artifact_type: ArtifactType,
        strategy: ParseStrategy | None = None,
    ) -> ArtifactRef:
        path = self._writer.write_model(model, self.path_for(filename))
        return ArtifactRef(
            artifact_type=artifact_type, path=path, strategy=strategy
        )

    def write_text(
        self,
        text: str,
        filename: str,
        artifact_type: ArtifactType,
        strategy: ParseStrategy | None = None,
    ) -> ArtifactRef:
        path = self._writer.write_text(text, self.path_for(filename))
        return ArtifactRef(
            artifact_type=artifact_type, path=path, strategy=strategy
        )

    def write_chunks(
        self,
        chunks: list[DocumentChunk],
        filename: str,
        strategy: ParseStrategy | None = None,
    ) -> ArtifactRef:
        path = self._writer.write_chunks_jsonl(chunks, self.path_for(filename))
        return ArtifactRef(
            artifact_type=ArtifactType.CHUNKS, path=path, strategy=strategy
        )

    def write_dict(
        self,
        data: dict,
        filename: str,
        artifact_type: ArtifactType,
        strategy: ParseStrategy | None = None,
    ) -> ArtifactRef:
        path = self._writer.write_dict(data, self.path_for(filename))
        return ArtifactRef(
            artifact_type=artifact_type, path=path, strategy=strategy
        )

    def write_dictionary_excel(
        self, dictionary: ExtractionDictionary, filename: str
    ) -> ArtifactRef:
        path = self._excel.export_dictionary(dictionary, self.path_for(filename))
        return ArtifactRef(
            artifact_type=ArtifactType.EXTRACTION_DICTIONARY,
            path=path,
            metadata={"format": "xlsx"},
        )

    def write_extraction_excel(
        self,
        result: ExtractionResult,
        filename: str,
        strategy: ParseStrategy | None = None,
    ) -> ArtifactRef:
        path = self._excel.export_extraction_result(result, self.path_for(filename))
        return ArtifactRef(
            artifact_type=ArtifactType.EXTRACTION_RESULT,
            path=path,
            strategy=strategy,
            metadata={"format": "xlsx"},
        )
