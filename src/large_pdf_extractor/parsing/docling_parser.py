"""Layout/table-aware parser using Docling.

Docling is an optional, heavy dependency. This parser must never crash the
pipeline if Docling is unavailable or fails: in that case it returns a
`ParsedDocument` with zero pages and a structured warning in metadata, plus
`metadata["skipped"] = True`. The comparator reports the skip explicitly.

Apple Silicon (macOS / MPS) note
--------------------------------
Docling runs PyTorch models for layout/table detection. On Apple Silicon the
MPS backend frequently raises dtype/op-support errors mid-inference, which can
make ``compare`` mode fail or return blank Docling output. To stay robust we:

1. Force the Docling accelerator onto **CPU** by default (configurable via the
   ``LPE_DOCLING_DEVICE`` env var: ``cpu`` | ``mps`` | ``cuda`` | ``auto``).
2. Enable the PyTorch MPS->CPU fallback and pin the default dtype to float32.
3. Capture any runtime error as a structured warning so a failure degrades to a
   clean, explainable skip rather than a blank/raised result.
"""

from __future__ import annotations

import os
import time
import traceback
from pathlib import Path

from ..domain.models import ParsedDocument, ParsedPage, ParseStrategy
from ..utils.hashing import file_document_id

# Default to CPU: the safest, most portable device (notably on macOS/MPS).
_DEFAULT_DEVICE = os.getenv("LPE_DOCLING_DEVICE", "cpu").lower()


class DoclingParser:
    """Docling-backed parser with graceful fallback and CPU-first execution."""

    strategy: ParseStrategy = ParseStrategy.DOCLING
    name = "docling"

    def __init__(self, device: str | None = None):
        self.device = (device or _DEFAULT_DEVICE).lower()

    def is_available(self) -> bool:
        """Return True if the Docling dependency can be imported."""
        _configure_torch_runtime(self.device)
        try:
            import docling  # noqa: F401

            return True
        except Exception:
            return False

    def parse(self, pdf_path: str) -> ParsedDocument:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        document_id = file_document_id(pdf_path)

        if not self.is_available():
            return self._skipped_document(
                document_id,
                path.name,
                "Docling is not installed; Docling parser path was skipped.",
            )

        try:
            return self._parse_with_docling(pdf_path, document_id, path.name)
        except Exception as exc:  # pragma: no cover - depends on docling internals
            detail = traceback.format_exc(limit=4)
            return self._skipped_document(
                document_id,
                path.name,
                f"Docling parsing failed and was skipped ({self.device}): {exc!r}",
                extra_warnings=[f"traceback: {detail.strip().splitlines()[-1]}"],
            )

    # -- internal helpers -------------------------------------------------

    def _parse_with_docling(
        self, pdf_path: str, document_id: str, filename: str
    ) -> ParsedDocument:
        _configure_torch_runtime(self.device)

        start = time.perf_counter()
        converter, device_used = _build_converter(self.device)
        result = converter.convert(pdf_path)
        doc = result.document

        pages = self._extract_pages(doc)
        table_count = self._count_tables(doc)
        runtime = time.perf_counter() - start

        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            page_count=len(pages),
            strategy=self.strategy,
            pages=pages,
            metadata={
                "parser": self.name,
                "parser_version": _docling_version(),
                "parse_runtime_seconds": round(runtime, 4),
                "docling_table_count": table_count,
                "device": device_used,
                "skipped": False,
                "warnings": [],
            },
        )

    def _extract_pages(self, doc) -> list[ParsedPage]:
        """Build per-page text from a Docling document, robust to API variants."""
        page_texts: dict[int, list[str]] = {}
        page_tables: dict[int, list[dict]] = {}

        for table in getattr(doc, "tables", []) or []:
            page_no = _provenance_page(table)
            try:
                md = table.export_to_markdown()
            except Exception:
                md = str(table)
            page_tables.setdefault(page_no, []).append({"markdown": md})
            page_texts.setdefault(page_no, []).append(md)

        for item in getattr(doc, "texts", []) or []:
            page_no = _provenance_page(item)
            text = getattr(item, "text", "") or ""
            if text:
                page_texts.setdefault(page_no, []).append(text)

        num_pages = 0
        pages_attr = getattr(doc, "pages", None)
        if isinstance(pages_attr, dict) and pages_attr:
            num_pages = max(int(k) for k in pages_attr.keys())
        if page_texts:
            num_pages = max(num_pages, max(page_texts.keys()))

        if num_pages <= 0:
            try:
                full_md = doc.export_to_markdown()
            except Exception:
                full_md = ""
            return [ParsedPage(page_number=1, text=full_md, metadata={"char_count": len(full_md)})]

        pages: list[ParsedPage] = []
        for page_no in range(1, num_pages + 1):
            text = "\n".join(page_texts.get(page_no, []))
            pages.append(
                ParsedPage(
                    page_number=page_no,
                    text=text,
                    tables=page_tables.get(page_no, []),
                    metadata={"char_count": len(text)},
                )
            )
        return pages

    def _count_tables(self, doc) -> int:
        return len(getattr(doc, "tables", []) or [])

    def _skipped_document(
        self,
        document_id: str,
        filename: str,
        warning: str,
        extra_warnings: list[str] | None = None,
    ) -> ParsedDocument:
        warnings = [warning]
        if extra_warnings:
            warnings.extend(extra_warnings)
        return ParsedDocument(
            document_id=document_id,
            filename=filename,
            page_count=0,
            strategy=self.strategy,
            pages=[],
            metadata={
                "parser": self.name,
                "parser_version": _docling_version(),
                "device": self.device,
                "skipped": True,
                "warnings": warnings,
            },
        )


def _configure_torch_runtime(device: str) -> None:
    """Make PyTorch safe to run under Docling, especially on macOS/MPS.

    Sets the MPS->CPU fallback and pins float32. This is a no-op when torch is
    not installed.
    """
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    if device == "cpu":
        # Hard-hide MPS/CUDA so any auto-detection inside Docling stays on CPU.
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    try:
        import torch

        try:
            torch.set_default_dtype(torch.float32)
        except Exception:
            pass
    except ImportError:
        pass


def _build_converter(device: str):
    """Build a Docling converter pinned to the requested accelerator device.

    Tries the modern Docling accelerator API and falls back to a default
    converter if that API is unavailable in the installed version. Returns the
    converter and the device string actually requested.
    """
    from docling.document_converter import DocumentConverter

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            AcceleratorDevice,
            AcceleratorOptions,
            PdfPipelineOptions,
        )
        from docling.document_converter import PdfFormatOption

        device_map = {
            "cpu": AcceleratorDevice.CPU,
            "mps": getattr(AcceleratorDevice, "MPS", AcceleratorDevice.CPU),
            "cuda": getattr(AcceleratorDevice, "CUDA", AcceleratorDevice.CPU),
            "auto": getattr(AcceleratorDevice, "AUTO", AcceleratorDevice.CPU),
        }
        accel = AcceleratorOptions(device=device_map.get(device, AcceleratorDevice.CPU))
        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accel

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        return converter, device
    except Exception:
        # Older/newer Docling without this API: fall back to defaults.
        return DocumentConverter(), f"{device} (default-pipeline)"


def _provenance_page(item) -> int:
    """Best-effort extraction of a 1-based page number from a Docling item."""
    prov = getattr(item, "prov", None)
    if prov:
        try:
            page_no = getattr(prov[0], "page_no", None)
            if page_no is not None:
                return int(page_no)
        except Exception:
            pass
    return 1


def _docling_version() -> str:
    try:
        import docling

        return getattr(docling, "__version__", "unknown")
    except Exception:
        return "unavailable"
