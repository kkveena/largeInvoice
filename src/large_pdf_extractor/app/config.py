"""Application settings and run-config construction.

Settings are environment-driven (via pydantic-settings) but the system runs
fully with defaults and the FakeLLMProvider — no keys required.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from ..domain.models import ParseStrategy, RunConfig


class AppSettings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="LPE_", env_file=".env", extra="ignore"
    )

    llm_provider: str = "fake"
    max_chunk_tokens: int = 4000
    chunk_overlap_tokens: int = 300


def build_run_config(
    pdf_path: str,
    output_dir: str,
    strategy: ParseStrategy = ParseStrategy.PYMUPDF,
    dictionary_path: str | None = None,
    llm_provider: str | None = None,
    max_chunks: int | None = None,
    settings: AppSettings | None = None,
) -> RunConfig:
    """Construct a `RunConfig`, filling defaults from settings."""
    settings = settings or AppSettings()
    return RunConfig(
        pdf_path=pdf_path,
        output_dir=output_dir,
        strategy=strategy,
        dictionary_path=dictionary_path,
        llm_provider=llm_provider or settings.llm_provider,
        max_chunk_tokens=settings.max_chunk_tokens,
        chunk_overlap_tokens=settings.chunk_overlap_tokens,
        max_chunks=max_chunks,
    )
