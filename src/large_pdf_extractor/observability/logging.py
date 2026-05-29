"""Lightweight logging helper built on rich when available."""

from __future__ import annotations

import logging

_CONFIGURED = False


def get_logger(name: str = "large_pdf_extractor") -> logging.Logger:
    """Return a configured logger, using rich formatting if installed."""
    global _CONFIGURED
    if not _CONFIGURED:
        handler: logging.Handler
        try:
            from rich.logging import RichHandler

            handler = RichHandler(rich_tracebacks=True, show_path=False)
            fmt = "%(message)s"
        except Exception:  # pragma: no cover - rich optional
            handler = logging.StreamHandler()
            fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        logging.basicConfig(level=logging.INFO, format=fmt, handlers=[handler])
        _CONFIGURED = True
    return logging.getLogger(name)
