"""Run-state helpers.

A run id is time-ordered and stable enough for distinct runs while keeping the
document folder content-addressed. RunState itself lives in domain.models.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..domain.models import RunConfig, RunState


def new_run_id() -> str:
    """Return a UTC, sortable run id."""
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")


def new_run_state(document_id: str, config: RunConfig, run_id: str | None = None) -> RunState:
    """Create a fresh RunState."""
    return RunState(
        run_id=run_id or new_run_id(),
        document_id=document_id,
        config=config,
        metadata={"created_at": datetime.now(timezone.utc).isoformat()},
    )
