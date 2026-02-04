"""LLM validation strategy for processing purpose analysis."""

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

from .prompts.prompt_builder import ProcessingPurposePromptBuilder
from .schemas.types import ProcessingPurposeIndicatorModel

logger = logging.getLogger(__name__)


class ProcessingPurposeValidationStrategy(
    LLMValidationStrategy[
        ProcessingPurposeIndicatorModel,
        LLMValidationOutcome[ProcessingPurposeIndicatorModel],
    ]
):
    """LLM validation strategy for processing purpose indicators.

    Uses LLMService to validate findings, categorising them as
    TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove).
    """

    def __init__(self, llm_service: LLMService) -> None:
        """Initialise strategy with LLM service.

        Args:
            llm_service: LLMService instance for making validation calls.

        """
        self._llm_service = llm_service

    @override
    def validate_findings(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> LLMValidationOutcome[ProcessingPurposeIndicatorModel]:
        """Validate findings using LLM service.

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
        groups = [ItemGroup(items=findings, content=None)]
        prompt_builder = ProcessingPurposePromptBuilder(
            validation_mode=config.llm_validation_mode
        )

        result = await self._llm_service.complete(
            groups,
            prompt_builder=prompt_builder,
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )

        return self._map_to_outcome(findings, result.responses, result.skipped)

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
