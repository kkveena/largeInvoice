"""Phase 1 orchestration pipeline.

Wires the independent services together in the mandated dictionary-first order:

    parse -> profile -> chunk -> (build/load dictionary) -> select -> extract
          -> validate -> render (JSON + Markdown) [-> compare]

Each service is constructed once and remains independently testable/reusable so
later phases can wrap them as agent tools without rewriting core logic.
"""

from __future__ import annotations

from ..chunking.candidate_selector import CandidateSelector
from ..chunking.chunker import ChunkingService
from ..comparison.comparator import ParserPathComparator
from ..dictionary.generator import DictionaryService
from ..domain.models import (
    ArtifactRef,
    ArtifactType,
    DocumentChunk,
    ExtractionDictionary,
    ExtractionResult,
    ParsedDocument,
    ParserPathResult,
    ParseStrategy,
    PipelineStepResult,
    RunConfig,
    RunState,
)
from ..extraction.extractor import ExtractionEngine
from ..llm import get_provider
from ..observability.logging import get_logger
from ..parsing import get_parser
from ..profiling.document_profiler import DocumentProfiler, select_representative_chunks
from ..rendering.markdown_renderer import MarkdownRenderer
from ..storage.artifact_store import ArtifactStore
from ..utils.hashing import file_document_id
from .run_state import new_run_id, new_run_state

logger = get_logger(__name__)

# The two single parser strategies exercised in compare mode, in order.
_COMPARE_STRATEGIES = [ParseStrategy.PYMUPDF, ParseStrategy.DOCLING]


class Phase1Pipeline:
    """Orchestrates the Phase 1 extraction pipeline."""

    def __init__(self, config: RunConfig):
        self.config = config
        self.provider = get_provider(config.llm_provider)
        self.profiler = DocumentProfiler()
        self.chunker = ChunkingService(
            max_chunk_tokens=config.max_chunk_tokens,
            chunk_overlap_tokens=config.chunk_overlap_tokens,
        )
        self.selector = CandidateSelector()
        self.dictionary_service = DictionaryService(provider=self.provider)
        self.extractor = ExtractionEngine(self.provider, self.selector)
        self.comparator = ParserPathComparator(self.selector)
        self.renderer = MarkdownRenderer()

    # -- public entrypoint ------------------------------------------------

    def run(self) -> RunState:
        document_id = file_document_id(self.config.pdf_path)
        run_id = new_run_id()
        state = new_run_state(document_id, self.config, run_id)
        store = ArtifactStore(self.config.output_dir, document_id, run_id)

        logger.info(
            "Starting run %s for document %s (strategy=%s, provider=%s)",
            run_id,
            document_id,
            self.config.strategy.value,
            self.config.llm_provider,
        )

        if self.config.strategy == ParseStrategy.COMPARE:
            self._run_compare(state, store, document_id)
        else:
            self._run_single(state, store, document_id, self.config.strategy)

        # Always write run metadata last.
        meta_ref = store.write_model(
            state, "run_metadata.json", ArtifactType.RUN_METADATA
        )
        state.artifacts.append(meta_ref)
        return state

    # -- single strategy --------------------------------------------------

    def _run_single(
        self,
        state: RunState,
        store: ArtifactStore,
        document_id: str,
        strategy: ParseStrategy,
    ) -> ParserPathResult:
        path_result = self._build_parser_path(state, store, strategy)

        # Dictionary-first: build/load before extraction.
        dictionary = self._resolve_dictionary(
            state, store, path_result.document_profile, path_result.chunks
        )

        self._extract_path(state, store, dictionary, path_result)
        return path_result

    # -- compare ----------------------------------------------------------

    def _run_compare(
        self, state: RunState, store: ArtifactStore, document_id: str
    ) -> None:
        path_results: list[ParserPathResult] = []
        for strategy in _COMPARE_STRATEGIES:
            path_results.append(self._build_parser_path(state, store, strategy))

        # Build/load ONE shared dictionary so differences reflect parsing only.
        primary = self._primary_path(path_results)
        dictionary = self._resolve_dictionary(
            state,
            store,
            primary.document_profile,
            self._combined_representative_chunks(path_results),
        )

        for path_result in path_results:
            self._extract_path(state, store, dictionary, path_result)

        report = self.comparator.compare(document_id, dictionary, path_results)
        json_ref = store.write_model(
            report, "comparison_report.json", ArtifactType.COMPARISON_REPORT
        )
        md = self.renderer.render_comparison_report(report)
        md_ref = store.write_text(
            md, "comparison_report.md", ArtifactType.COMPARISON_REPORT
        )
        state.artifacts.extend([json_ref, md_ref])
        state.steps.append(
            PipelineStepResult(
                step_name="compare_parser_paths",
                success=True,
                artifacts=[json_ref, md_ref],
                metrics={
                    "compared_strategies": [s.value for s in report.compared_strategies]
                },
                warnings=report.warnings,
            )
        )

    # -- shared building blocks ------------------------------------------

    def _build_parser_path(
        self, state: RunState, store: ArtifactStore, strategy: ParseStrategy
    ) -> ParserPathResult:
        """Parse -> profile -> chunk for one strategy and persist artifacts."""
        result = ParserPathResult(strategy=strategy)
        strat = strategy.value

        # Parse.
        try:
            parser = get_parser(strategy)
            parsed: ParsedDocument = parser.parse(self.config.pdf_path)
        except Exception as exc:  # pragma: no cover - defensive
            result.errors.append(f"parse failed: {exc!r}")
            state.steps.append(
                PipelineStepResult(
                    step_name=f"parse[{strat}]", success=False, errors=result.errors
                )
            )
            return result

        result.parsed_document = parsed
        parser_warnings = list(parsed.metadata.get("warnings", []))
        result.warnings.extend(parser_warnings)
        skipped = bool(parsed.metadata.get("skipped"))

        ref = store.write_model(
            parsed,
            f"parsed_document.{strat}.json",
            ArtifactType.PARSED_DOCUMENT,
            strategy,
        )
        state.artifacts.append(ref)
        state.steps.append(
            PipelineStepResult(
                step_name=f"parse[{strat}]",
                success=not skipped,
                artifacts=[ref],
                warnings=parser_warnings,
                metrics={"page_count": parsed.page_count, "skipped": skipped},
            )
        )

        # Profile.
        profile = self.profiler.profile(parsed)
        result.document_profile = profile

        # Chunk.
        chunks = self.chunker.chunk(parsed, profile)
        result.chunks = chunks

        # Representative chunks (also fills profile.representative_chunk_ids).
        select_representative_chunks(profile, chunks)

        profile_ref = store.write_model(
            profile,
            f"document_profile.{strat}.json",
            ArtifactType.DOCUMENT_PROFILE,
            strategy,
        )
        chunks_ref = store.write_chunks(chunks, f"chunks.{strat}.jsonl", strategy)
        state.artifacts.extend([profile_ref, chunks_ref])
        state.steps.append(
            PipelineStepResult(
                step_name=f"profile_and_chunk[{strat}]",
                success=True,
                artifacts=[profile_ref, chunks_ref],
                metrics={
                    "total_char_count": profile.total_char_count,
                    "chunk_count": len(chunks),
                    "detected_table_count": profile.detected_table_count,
                },
            )
        )
        return result

    def _resolve_dictionary(
        self,
        state: RunState,
        store: ArtifactStore,
        profile,
        representative_chunks: list[DocumentChunk],
    ) -> ExtractionDictionary:
        """Load a provided dictionary or generate+save a proposed one."""
        if self.config.dictionary_path:
            dictionary = self.dictionary_service.load_dictionary(
                self.config.dictionary_path
            )
            step_name = "load_dictionary"
            artifacts: list[ArtifactRef] = []
        else:
            dictionary = self.dictionary_service.generate_proposed_dictionary(
                profile, representative_chunks
            )
            proposed_ref = store.write_model(
                dictionary,
                "extraction_dictionary.proposed.json",
                ArtifactType.EXTRACTION_DICTIONARY,
            )
            artifacts = [proposed_ref]
            step_name = "generate_dictionary"

        # The dictionary actually used (validated) is always saved as 'used'.
        used_ref = store.write_model(
            dictionary,
            "extraction_dictionary.used.json",
            ArtifactType.EXTRACTION_DICTIONARY,
        )
        artifacts.append(used_ref)

        # Shareable Excel workbook of the dictionary (for non-engineering review).
        excel_ref = store.write_dictionary_excel(
            dictionary, "extraction_dictionary.used.xlsx"
        )
        artifacts.append(excel_ref)

        state.artifacts.extend(artifacts)
        state.steps.append(
            PipelineStepResult(
                step_name=step_name,
                success=True,
                artifacts=artifacts,
                metrics={"item_count": len(dictionary.items)},
            )
        )
        return dictionary

    def _extract_path(
        self,
        state: RunState,
        store: ArtifactStore,
        dictionary: ExtractionDictionary,
        path_result: ParserPathResult,
    ) -> None:
        strategy = path_result.strategy
        strat = strategy.value

        working_chunks = self._working_chunks(path_result.chunks)

        if not working_chunks:
            # Graceful skip: no extraction possible (e.g. Docling unavailable).
            empty = ExtractionResult(
                document_id=path_result.parsed_document.document_id
                if path_result.parsed_document
                else (dictionary.document_id or "unknown"),
                dictionary_id=dictionary.dictionary_id,
                parse_strategy=strategy,
                values=[],
                unmapped_observations=[],
                metadata={"skipped": True},
            )
            path_result.extraction_result = empty
            path_result.warnings.append(
                f"No chunks available for '{strat}'; extraction skipped."
            )
            self._write_extraction(state, store, empty, strategy, skipped=True)
            return

        result = self.extractor.extract(dictionary, working_chunks, strategy)
        result.markdown_summary = self.renderer.render_extraction_result(result)
        path_result.extraction_result = result
        self._write_extraction(state, store, result, strategy, skipped=False)

    def _write_extraction(
        self,
        state: RunState,
        store: ArtifactStore,
        result: ExtractionResult,
        strategy: ParseStrategy,
        skipped: bool,
    ) -> None:
        strat = strategy.value
        json_ref = store.write_model(
            result,
            f"extraction_result.{strat}.json",
            ArtifactType.EXTRACTION_RESULT,
            strategy,
        )
        md_text = result.markdown_summary or self.renderer.render_extraction_result(
            result
        )
        md_ref = store.write_text(
            md_text,
            f"extraction_result.{strat}.md",
            ArtifactType.MARKDOWN_RESULT,
            strategy,
        )
        excel_ref = store.write_extraction_excel(
            result, f"extraction_result.{strat}.xlsx", strategy
        )
        state.artifacts.extend([json_ref, md_ref, excel_ref])
        populated = sum(1 for v in result.values if v.value is not None)
        state.steps.append(
            PipelineStepResult(
                step_name=f"extract[{strat}]",
                success=not skipped,
                artifacts=[json_ref, md_ref],
                metrics={
                    "values_populated": populated,
                    "value_count": len(result.values),
                    "skipped": skipped,
                },
            )
        )

    # -- helpers ----------------------------------------------------------

    def _working_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if self.config.max_chunks is not None:
            return chunks[: self.config.max_chunks]
        return chunks

    def _primary_path(self, results: list[ParserPathResult]) -> ParserPathResult:
        for result in results:
            if result.parsed_document and result.parsed_document.pages:
                return result
        return results[0]

    def _combined_representative_chunks(
        self, results: list[ParserPathResult]
    ) -> list[DocumentChunk]:
        combined: list[DocumentChunk] = []
        for result in results:
            if not result.document_profile:
                continue
            rep_ids = set(result.document_profile.representative_chunk_ids)
            for chunk in result.chunks:
                if chunk.chunk_id in rep_ids:
                    combined.append(chunk)
        if not combined:
            primary = self._primary_path(results)
            combined = primary.chunks[:6]
        return combined
