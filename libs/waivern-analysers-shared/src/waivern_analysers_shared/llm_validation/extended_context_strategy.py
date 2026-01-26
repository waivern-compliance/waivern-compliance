"""Extended context LLM validation strategy with source-based batching.

Provides validation with full source content, batching findings by their source
(file, table, API endpoint) to enable richer LLM context.

Flow
----

::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                 ExtendedContextLLMValidationStrategy                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  Findings ──► Group by source ──► Estimate tokens per source            │
    │                     │                      │                            │
    │                     ▼                      ▼                            │
    │              ┌─────────────────────────────────────┐                    │
    │              │ Token-aware batch creation:         │                    │
    │              │ • Sort sources by token count       │                    │
    │              │ • Greedy bin-packing into batches   │                    │
    │              │ • Respect model context window      │                    │
    │              │ • Handle oversized sources          │                    │
    │              └─────────────────────────────────────┘                    │
    │                              │                                          │
    │                              ▼                                          │
    │              For each batch (with full source content):                 │
    │                              │                                          │
    │                              ├──► get_batch_validation_prompt()         │
    │                              │         (abstract, includes content)     │
    │                              │                                          │
    │                              ├──► LLM call                              │
    │                              │                                          │
    │                              └──► categorise findings                   │
    │                                                                         │
    │                              ▼                                          │
    │              Aggregate + handle skipped ──► LLMValidationOutcome        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Batching is token-aware: sources are grouped into batches that fit within the
model's context window. Oversized or missing sources are skipped with reason.
For simple count-based batching, use :class:`DefaultLLMValidationStrategy`.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import override

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .decision_engine import ValidationDecisionEngine
from .models import (
    SKIP_REASON_BATCH_ERROR,
    SKIP_REASON_MISSING_CONTENT,
    SKIP_REASON_NO_SOURCE,
    SKIP_REASON_OVERSIZED,
    LLMValidationOutcome,
    LLMValidationResponseModel,
    LLMValidationResultModel,
    SkippedFinding,
)
from .protocols import SourceProvider
from .strategy import LLMValidationStrategy
from .token_estimation import (
    calculate_max_payload_tokens,
    estimate_tokens,
    get_model_context_window,
)

logger = logging.getLogger(__name__)

# Estimated tokens per finding in the prompt (ID, patterns, line number, etc.)
# Used for token budget calculation when batching. Conservative estimate to
# avoid exceeding context limits.
_TOKENS_PER_FINDING_ESTIMATE = 50


@dataclass
class SourceBatch:
    """A batch of sources to validate together."""

    sources: list[str]
    """List of source identifiers in this batch."""

    estimated_tokens: int
    """Estimated total tokens for this batch."""


@dataclass
class _SourceInfo:
    """Information about a source for batching."""

    source_id: str
    content: str | None
    estimated_tokens: int
    finding_count: int


@dataclass
class _BatchResult[T]:
    """Result of validating a single batch."""

    kept: list[T] = field(default_factory=list)
    removed: list[T] = field(default_factory=list)
    not_flagged: list[T] = field(default_factory=list)


class _BatchBuilder:
    """Accumulates sources into batches respecting token limits.

    Uses greedy bin-packing: adds sources until limit reached, then starts new batch.
    """

    _max_tokens: int
    _batches: list[SourceBatch]
    _current_sources: list[str]
    _current_tokens: int

    def __init__(self, max_tokens: int) -> None:
        """Initialise batch builder.

        Args:
            max_tokens: Maximum tokens allowed per batch.

        """
        self._max_tokens = max_tokens
        self._batches = []
        self._current_sources = []
        self._current_tokens = 0

    def add_source(self, source_id: str, source_tokens: int) -> None:
        """Add a source to the current batch, starting new batch if needed."""
        if self._current_tokens + source_tokens <= self._max_tokens:
            self._current_sources.append(source_id)
            self._current_tokens += source_tokens
        else:
            self._finalise_current_batch()
            self._current_sources = [source_id]
            self._current_tokens = source_tokens

    def _finalise_current_batch(self) -> None:
        """Finalise the current batch if non-empty."""
        if self._current_sources:
            self._batches.append(
                SourceBatch(
                    sources=list(self._current_sources),
                    estimated_tokens=self._current_tokens,
                )
            )
            self._current_sources = []
            self._current_tokens = 0

    def build(self) -> list[SourceBatch]:
        """Finalise and return all batches."""
        self._finalise_current_batch()
        return self._batches


class ExtendedContextLLMValidationStrategy[T: Finding](LLMValidationStrategy[T], ABC):
    """LLM validation strategy with full source content.

    Batches findings by source (file, table, etc.) and includes full source
    content in prompts for richer validation context. Uses token-aware batching
    to fit within model context limits.

    Requires a SourceProvider to extract source identifiers and content.
    Falls back to evidence-only validation for sources without available content.

    Type parameter T is the finding type, must satisfy the Finding protocol.
    """

    _source_provider: SourceProvider[T]

    def __init__(self, source_provider: SourceProvider[T]) -> None:
        """Initialise strategy with source provider.

        Args:
            source_provider: Provider for source IDs and content.

        """
        self._source_provider = source_provider

    @abstractmethod
    def get_batch_validation_prompt(
        self,
        batch: SourceBatch,
        findings_by_source: dict[str, list[T]],
        source_contents: dict[str, str],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for a batch of sources.

        Args:
            batch: The batch of sources to validate.
            findings_by_source: Mapping of source IDs to their findings.
            source_contents: Mapping of source IDs to their content.
            config: LLM validation configuration.

        Returns:
            Validation prompt string for the LLM.

        """
        ...

    @override
    def validate_findings(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> LLMValidationOutcome[T]:
        """Validate findings using source-based batching with full content.

        Groups findings by source, creates token-aware batches, includes full
        source content in prompts, and categorises based on LLM responses.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            LLMValidationOutcome with detailed breakdown of validation results.

        """
        if not findings:
            logger.debug("No findings to validate")
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[],
            )

        try:
            # Group findings by source
            findings_by_source = self._group_findings_by_source(findings)

            # Calculate max tokens per batch
            max_tokens = self._calculate_max_tokens(config, llm_service)

            # Create token-aware batches
            (
                batches,
                oversized_sources,
                missing_content_sources,
                no_source_sources,
                source_contents,
            ) = self._create_batches(findings_by_source, max_tokens)

            # Validate each batch and collect detailed results
            outcome = self._validate_batches(
                batches,
                findings_by_source,
                source_contents,
                config,
                llm_service,
            )

            # Handle oversized sources (skipped with reason)
            for source_id in oversized_sources:
                logger.warning(
                    f"Source '{source_id}' exceeds token limit, marking as skipped"
                )
                for finding in findings_by_source[source_id]:
                    outcome.skipped.append(
                        SkippedFinding(finding=finding, reason=SKIP_REASON_OVERSIZED)
                    )

            # Handle missing content sources (skipped with reason)
            for source_id in missing_content_sources:
                logger.warning(
                    f"Source '{source_id}' has no content available, marking as skipped"
                )
                for finding in findings_by_source[source_id]:
                    outcome.skipped.append(
                        SkippedFinding(
                            finding=finding, reason=SKIP_REASON_MISSING_CONTENT
                        )
                    )

            # Handle findings without source (skipped with reason)
            for source_id in no_source_sources:
                logger.warning("Findings without source metadata, marking as skipped")
                for finding in findings_by_source[source_id]:
                    outcome.skipped.append(
                        SkippedFinding(finding=finding, reason=SKIP_REASON_NO_SOURCE)
                    )

            logger.debug(
                f"Extended context validation: {len(findings)} → "
                f"{len(outcome.kept_findings)} kept "
                f"({len(outcome.llm_validated_kept)} validated, "
                f"{len(outcome.llm_not_flagged)} not flagged, "
                f"{len(outcome.skipped)} skipped)"
            )

            return outcome

        except Exception as e:
            logger.error(f"Extended context validation failed: {e}")
            logger.warning(
                "Returning original findings as skipped due to validation error"
            )
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[
                    SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                    for f in findings
                ],
            )

    def _group_findings_by_source(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by their source identifier.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping source IDs to their findings.

        """
        grouped: dict[str, list[T]] = {}

        for finding in findings:
            source_id = self._source_provider.get_source_id(finding)
            if source_id not in grouped:
                grouped[source_id] = []
            grouped[source_id].append(finding)

        logger.debug(f"Grouped {len(findings)} findings into {len(grouped)} sources")
        return grouped

    def _calculate_max_tokens(
        self, config: LLMValidationConfig, llm_service: BaseLLMService
    ) -> int:
        """Calculate maximum tokens per batch based on config and model.

        Args:
            config: LLM validation configuration.
            llm_service: LLM service to detect model context window.

        Returns:
            Maximum tokens allowed per batch.

        """
        context_window = config.batching.model_context_window
        if context_window is None:
            context_window = get_model_context_window(llm_service.model_name)
            logger.debug(f"Auto-detected context window: {context_window} tokens")

        max_tokens = calculate_max_payload_tokens(context_window)
        logger.debug(f"Max tokens per batch: {max_tokens}")
        return max_tokens

    def _create_batches(
        self,
        findings_by_source: dict[str, list[T]],
        max_tokens: int,
    ) -> tuple[list[SourceBatch], list[str], list[str], list[str], dict[str, str]]:
        """Create token-aware batches of sources.

        Args:
            findings_by_source: Mapping of source IDs to findings.
            max_tokens: Maximum tokens per batch.

        Returns:
            Tuple of (batches, oversized_ids, missing_content_ids, no_source_ids, source_contents).
            Sources without content or source ID are returned separately.

        """
        # Collect source info with content and token estimates
        source_infos: list[_SourceInfo] = []
        source_contents: dict[str, str] = {}
        missing_content: list[str] = []
        no_source: list[str] = []

        for source_id, source_findings in findings_by_source.items():
            # Handle empty source IDs (findings without source metadata)
            if not source_id:
                no_source.append(source_id)
                continue

            content = self._source_provider.get_source_content(source_id)

            if content is None:
                # No content available - can't use extended context strategy
                missing_content.append(source_id)
                continue

            source_contents[source_id] = content
            content_tokens = estimate_tokens(content)
            findings_summary_tokens = self._estimate_findings_tokens(source_findings)
            total_tokens = content_tokens + findings_summary_tokens

            source_infos.append(
                _SourceInfo(
                    source_id=source_id,
                    content=content,
                    estimated_tokens=total_tokens,
                    finding_count=len(source_findings),
                )
            )

        # Sort by token estimate (largest first) for better bin-packing
        source_infos.sort(key=lambda s: s.estimated_tokens, reverse=True)

        # Build batches
        builder: _BatchBuilder = _BatchBuilder(max_tokens=max_tokens)
        oversized: list[str] = []

        for info in source_infos:
            if info.estimated_tokens > max_tokens:
                oversized.append(info.source_id)
            else:
                builder.add_source(info.source_id, info.estimated_tokens)

        batches = builder.build()

        logger.info(
            f"Created {len(batches)} batches from {len(source_infos)} sources, "
            f"{len(oversized)} oversized, {len(missing_content)} missing content, "
            f"{len(no_source)} no source"
        )

        return batches, oversized, missing_content, no_source, source_contents

    def _estimate_findings_tokens(self, findings: list[T]) -> int:
        """Estimate tokens for findings summary in prompt.

        Args:
            findings: List of findings.

        Returns:
            Estimated token count.

        """
        return len(findings) * _TOKENS_PER_FINDING_ESTIMATE

    def _validate_batches(
        self,
        batches: list[SourceBatch],
        findings_by_source: dict[str, list[T]],
        source_contents: dict[str, str],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> LLMValidationOutcome[T]:
        """Validate all batches and collect results.

        Args:
            batches: List of batches to validate.
            findings_by_source: Mapping of source IDs to findings.
            source_contents: Mapping of source IDs to content.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            LLMValidationOutcome with aggregated results from all batches.

        """
        # Accumulators for all batches
        all_kept: list[T] = []
        all_removed: list[T] = []
        all_not_flagged: list[T] = []
        all_skipped: list[SkippedFinding[T]] = []

        for batch_idx, batch in enumerate(batches):
            try:
                batch_result = self._validate_batch(
                    batch,
                    findings_by_source,
                    source_contents,
                    config,
                    llm_service,
                )
                all_kept.extend(batch_result.kept)
                all_removed.extend(batch_result.removed)
                all_not_flagged.extend(batch_result.not_flagged)
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} validation failed: {e}")
                logger.warning(
                    "Marking batch findings as skipped due to validation error"
                )
                # Batch error - all findings in this batch are skipped
                for source_id in batch.sources:
                    all_skipped.extend(
                        SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                        for f in findings_by_source[source_id]
                    )

        return LLMValidationOutcome(
            llm_validated_kept=all_kept,
            llm_validated_removed=all_removed,
            llm_not_flagged=all_not_flagged,
            skipped=all_skipped,
        )

    def _validate_batch(
        self,
        batch: SourceBatch,
        findings_by_source: dict[str, list[T]],
        source_contents: dict[str, str],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> _BatchResult[T]:
        """Validate a single batch of sources.

        Args:
            batch: The batch to validate.
            findings_by_source: Mapping of source IDs to findings.
            source_contents: Mapping of source IDs to content.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            BatchResult with categorised findings from this batch.

        """
        # Collect all findings in batch
        batch_findings: list[T] = []
        for source_id in batch.sources:
            batch_findings.extend(findings_by_source[source_id])

        # Build batch-specific content map (only sources in this batch)
        batch_contents = {
            source_id: source_contents[source_id]
            for source_id in batch.sources
            if source_id in source_contents
        }

        # Generate prompt
        prompt = self.get_batch_validation_prompt(
            batch=batch,
            findings_by_source=findings_by_source,
            source_contents=batch_contents,
            config=config,
        )

        # Call LLM with structured output
        logger.debug(f"Validating batch with {len(batch_findings)} findings")
        response = llm_service.invoke_with_structured_output(
            prompt, LLMValidationResponseModel
        )
        logger.debug(f"Received {len(response.results)} validation results")

        # Categorise findings based on results
        return self._categorise_findings_by_results(batch_findings, response.results)

    def _categorise_findings_by_results(
        self,
        findings: list[T],
        validation_results: list[LLMValidationResultModel],
    ) -> _BatchResult[T]:
        """Categorise findings based on LLM validation results.

        Uses fail-safe approach: findings not mentioned by LLM are categorised
        as 'not_flagged' and kept, consistent with existing validation error handling.

        Args:
            findings: List of findings in the batch.
            validation_results: Validation results from LLM.

        Returns:
            BatchResult with findings categorised as kept, removed, or not_flagged.

        """
        findings_by_id = {f.id: f for f in findings}
        result = _BatchResult[T]()
        processed_ids: set[str] = set()

        for llm_result in validation_results:
            finding = findings_by_id.get(llm_result.finding_id)

            if finding is None:
                logger.warning(f"Unknown finding_id from LLM: {llm_result.finding_id}")
                continue

            processed_ids.add(llm_result.finding_id)

            # Log and evaluate validation decision
            ValidationDecisionEngine.log_validation_decision(llm_result, finding)

            # Categorise based on decision engine
            if ValidationDecisionEngine.should_keep_finding(llm_result, finding):
                result.kept.append(finding)
            else:
                result.removed.append(finding)

        # Findings not flagged by LLM are considered valid
        not_flagged_ids = set(findings_by_id.keys()) - processed_ids
        if not_flagged_ids:
            logger.debug(
                f"{len(not_flagged_ids)} findings not flagged by LLM, keeping as valid"
            )
            for finding_id in not_flagged_ids:
                result.not_flagged.append(findings_by_id[finding_id])

        return result
