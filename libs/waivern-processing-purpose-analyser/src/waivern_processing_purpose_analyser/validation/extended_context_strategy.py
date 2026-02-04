"""Source code validation strategy for processing purpose findings.

Uses LLMService with EXTENDED_CONTEXT batching mode to validate findings
with full source file content for context-aware validation.
"""

import asyncio
import logging
from typing import override

from waivern_analysers_shared.llm_validation.decision_engine import (
    ValidationDecisionEngine,
)
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    LLMValidationResponseModel,
)
from waivern_analysers_shared.llm_validation.strategy import LLMValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm import (
    BatchingMode,
    ItemGroup,
    LLMService,
    SkippedFinding,
    SkipReason,
)

from waivern_processing_purpose_analyser.prompts import SourceCodePromptBuilder
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)

from .providers import SourceCodeSourceProvider

logger = logging.getLogger(__name__)


class SourceCodeValidationStrategy(
    LLMValidationStrategy[
        ProcessingPurposeIndicatorModel,
        LLMValidationOutcome[ProcessingPurposeIndicatorModel],
    ]
):
    """Validation strategy for source_code schema findings.

    Uses full file content in prompts for richer validation context.
    Groups findings by source file and uses EXTENDED_CONTEXT batching
    so BatchPlanner can bin-pack groups by token count.
    """

    def __init__(
        self,
        llm_service: LLMService,
        source_provider: SourceCodeSourceProvider,
    ) -> None:
        """Initialise with LLM service and source provider.

        Args:
            llm_service: LLMService instance for making validation calls.
            source_provider: Provider for file paths and content.

        """
        self._llm_service = llm_service
        self._source_provider = source_provider

    @override
    def validate_findings(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> LLMValidationOutcome[ProcessingPurposeIndicatorModel]:
        """Validate findings using LLM with full source file context.

        Orchestrates the complete validation flow:
        1. Group findings by source file
        2. Create ItemGroup per source with file content
        3. Call LLMService.complete() with EXTENDED_CONTEXT mode
        4. Map responses to validation outcome

        Args:
            findings: Findings to validate.
            config: Validation configuration.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            LLMValidationOutcome with categorised findings.

        """
        if not findings:
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[],
            )

        try:
            return asyncio.run(self._validate_async(findings, config, run_id))
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return self._handle_total_failure(findings)

    async def _validate_async(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> LLMValidationOutcome[ProcessingPurposeIndicatorModel]:
        """Async validation implementation."""
        groups = self._create_groups_by_source(findings)
        prompt_builder = SourceCodePromptBuilder(
            validation_mode=config.llm_validation_mode
        )

        result = await self._llm_service.complete(
            groups,
            prompt_builder=prompt_builder,
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id=run_id,
        )

        return self._map_to_outcome(findings, result.responses, result.skipped)

    def _create_groups_by_source(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
    ) -> list[ItemGroup[ProcessingPurposeIndicatorModel]]:
        """Group findings by source file with content.

        Each group contains all findings from a single source file,
        along with the file content for context-aware validation.

        Findings without source metadata are grouped together with
        content=None (BatchPlanner will handle as MISSING_CONTENT).
        """
        findings_by_source: dict[str, list[ProcessingPurposeIndicatorModel]] = {}

        for finding in findings:
            source = finding.metadata.source if finding.metadata else None
            source_key = source or "__no_source__"
            findings_by_source.setdefault(source_key, []).append(finding)

        groups: list[ItemGroup[ProcessingPurposeIndicatorModel]] = []

        for source, source_findings in findings_by_source.items():
            if source == "__no_source__":
                # Findings without source - content is None
                groups.append(
                    ItemGroup(
                        items=source_findings,
                        content=None,
                        group_id=None,
                    )
                )
            else:
                # Get content from source provider
                content = self._source_provider.get_source_content(source)
                groups.append(
                    ItemGroup(
                        items=source_findings,
                        content=content,
                        group_id=source,
                    )
                )

        return groups

    def _map_to_outcome(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        responses: list[LLMValidationResponseModel],
        skipped: list[SkippedFinding[ProcessingPurposeIndicatorModel]],
    ) -> LLMValidationOutcome[ProcessingPurposeIndicatorModel]:
        """Map LLM responses to validation outcome."""
        findings_by_id = {f.id: f for f in findings}

        kept, removed, processed_ids = self._categorise_by_responses(
            responses, findings_by_id
        )
        not_flagged = self._get_not_flagged(findings_by_id, processed_ids, skipped)

        return LLMValidationOutcome(
            llm_validated_kept=kept,
            llm_validated_removed=removed,
            llm_not_flagged=not_flagged,
            skipped=list(skipped),
        )

    def _categorise_by_responses(
        self,
        responses: list[LLMValidationResponseModel],
        findings_by_id: dict[str, ProcessingPurposeIndicatorModel],
    ) -> tuple[
        list[ProcessingPurposeIndicatorModel],
        list[ProcessingPurposeIndicatorModel],
        set[str],
    ]:
        """Categorise findings based on LLM responses."""
        kept: list[ProcessingPurposeIndicatorModel] = []
        removed: list[ProcessingPurposeIndicatorModel] = []
        processed_ids: set[str] = set()

        for response in responses:
            for result in response.results:
                finding = findings_by_id.get(result.finding_id)
                if finding is None:
                    logger.warning(f"Unknown finding_id from LLM: {result.finding_id}")
                    continue

                processed_ids.add(result.finding_id)
                ValidationDecisionEngine.log_validation_decision(result, finding)

                if ValidationDecisionEngine.should_keep_finding(result, finding):
                    kept.append(finding)
                else:
                    removed.append(finding)

        return kept, removed, processed_ids

    def _get_not_flagged(
        self,
        findings_by_id: dict[str, ProcessingPurposeIndicatorModel],
        processed_ids: set[str],
        skipped: list[SkippedFinding[ProcessingPurposeIndicatorModel]],
    ) -> list[ProcessingPurposeIndicatorModel]:
        """Get findings not flagged by LLM (kept via fail-safe)."""
        skipped_ids = {s.finding.id for s in skipped}
        not_flagged_ids = set(findings_by_id.keys()) - processed_ids - skipped_ids
        not_flagged = [findings_by_id[fid] for fid in not_flagged_ids]

        if not_flagged:
            logger.debug(
                f"{len(not_flagged)} findings not flagged by LLM, keeping as valid"
            )

        return not_flagged

    def _handle_total_failure(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
    ) -> LLMValidationOutcome[ProcessingPurposeIndicatorModel]:
        """Handle total validation failure."""
        return LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(finding=f, reason=SkipReason.BATCH_ERROR)
                for f in findings
            ],
        )
