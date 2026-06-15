"""Abstract base classes for LLM validation strategies."""

import logging
from abc import ABC, abstractmethod
from typing import override

from waivern_core import Finding, LLMValidationResponseModel
from waivern_core.types import JsonValue
from waivern_llm import LLMDispatchResult, LLMRequest, SkippedFinding, SkipReason

from waivern_analysers_shared.llm_validation.decision_engine import (
    ValidationDecisionEngine,
)
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    RemovedItem,
)
from waivern_analysers_shared.types import LLMValidationConfig

logger = logging.getLogger(__name__)


class LLMValidationStrategy[TFinding: Finding, TResult](ABC):
    """Abstract base class for LLM validation strategies.

    Defines the interface that all validation strategies must implement.
    Concrete implementations handle batching and LLM interaction differently.

    Type parameters:
        TFinding: The finding type, bound to the Finding protocol.
        TResult: The strategy result type (e.g., LLMValidationOutcome for filtering,
            EnrichmentResult for enrichment). Unbounded because different paradigms
            have no common result interface.

    Note on TFinding bound:
        Uses the ``Finding`` protocol bound (not ``BaseFindingModel``) because
        protocols provide structural typing that avoids generic invariance issues.
        A ``BaseFindingModel[ChildMetadata]`` is NOT a subtype of
        ``BaseFindingModel[BaseMetadata]`` due to invariance, but any finding class
        satisfies the ``Finding`` protocol regardless of its metadata type parameter.
    """

    @abstractmethod
    def prepare_validation(
        self,
        findings: list[TFinding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[list[TFinding], LLMRequest[TFinding] | None]:
        """Prepare an LLM request for dispatch.

        Builds groups and constructs the LLMRequest without making any LLM calls.
        The returned findings are the state passed back to finalise_validation().

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            Tuple of (findings for finalise, LLMRequest or None if no dispatch needed).

        """
        ...

    @abstractmethod
    def finalise_validation(
        self,
        findings: list[TFinding],
        result: LLMDispatchResult | None,
    ) -> TResult:
        """Interpret dispatch results and produce the strategy result.

        Args:
            findings: Original findings passed to prepare_validation.
            result: Dispatch result from the executor, or None if no dispatch occurred.

        Returns:
            Strategy-specific result type.

        """
        ...

    def export_persistence_state(self) -> dict[str, JsonValue] | None:
        """Return construction-time state needed for cross-round reconstruction.

        Strategies whose construction requires stateful inputs beyond injected
        services (e.g., a source content map held by a ``SourceProvider``)
        override this to return a serialisable snapshot. All other strategies
        inherit the default ``None``, signalling that their reconstruction
        needs nothing beyond their injected dependencies.

        Captured by ``ValidationOrchestrator.prepare()`` into
        ``OrchestratorPrepareState.strategy_state``. Interpreted by the
        processor's reconstruction path (typically inside a processor-specific
        factory) on the fallback/resume rounds.

        Returns:
            A JSON-serialisable dict representing the strategy's persistence
            state, or ``None`` if no reconstruction state is needed.

        """
        return None


class FilteringValidationStrategy[TFinding: Finding](
    LLMValidationStrategy[TFinding, LLMValidationOutcome[TFinding]]
):
    """Base class for filtering strategies that produce LLMValidationOutcome.

    Provides a default finalise_validation() implementation that handles the
    standard deserialise -> categorise -> outcome flow used by all filtering
    strategies. Concrete filtering strategies only need to implement
    prepare_validation().
    """

    @override
    def finalise_validation(
        self,
        findings: list[TFinding],
        result: LLMDispatchResult | None,
    ) -> LLMValidationOutcome[TFinding]:
        """Deserialise responses, categorise findings, and produce outcome.

        1. If result is None -> return all findings as skipped (BATCH_ERROR).
        2. Deserialise raw dict responses to LLMValidationResponseModel.
        3. Match skipped findings from result back to typed findings by ID.
        4. Categorise: TRUE_POSITIVE -> kept, FALSE_POSITIVE -> removed,
           unmentioned -> not_flagged (fail-safe).
        """
        if result is None:
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[
                    SkippedFinding(finding=f, reason=SkipReason.BATCH_ERROR)
                    for f in findings
                ],
            )

        findings_by_id = {f.id: f for f in findings}

        kept, removed, processed_ids = self._deserialise_and_categorise(
            result.responses, findings_by_id
        )
        skipped_typed = self._match_skipped_to_typed(result.skipped, findings_by_id)
        not_flagged = self._compute_not_flagged(
            findings_by_id, processed_ids, skipped_typed
        )

        return LLMValidationOutcome(
            llm_validated_kept=kept,
            llm_validated_removed=removed,
            llm_not_flagged=not_flagged,
            skipped=skipped_typed,
        )

    def _deserialise_and_categorise(
        self,
        raw_responses: list[dict[str, JsonValue]],
        findings_by_id: dict[str, TFinding],
    ) -> tuple[list[TFinding], list[RemovedItem[TFinding]], set[str]]:
        """Deserialise raw responses and split findings into kept/removed.

        Each removed finding is paired with the LLM verdict's ``reasoning``
        field verbatim, surfacing the model's own justification at the point
        of removal for downstream audit-trail consumers.
        """
        kept: list[TFinding] = []
        removed: list[RemovedItem[TFinding]] = []
        processed_ids: set[str] = set()

        for raw_response in raw_responses:
            response = LLMValidationResponseModel.model_validate(raw_response)
            for item in response.results:
                finding = findings_by_id.get(item.finding_id)
                if finding is None:
                    logger.warning(f"Unknown finding_id from LLM: {item.finding_id}")
                    continue

                processed_ids.add(item.finding_id)
                ValidationDecisionEngine.log_validation_decision(item, finding)

                if ValidationDecisionEngine.should_keep_finding(item, finding):
                    kept.append(finding)
                else:
                    removed.append(RemovedItem(finding=finding, reason=item.reasoning))

        return kept, removed, processed_ids

    def _match_skipped_to_typed(
        self,
        skipped: list[SkippedFinding[Finding]],
        findings_by_id: dict[str, TFinding],
    ) -> list[SkippedFinding[TFinding]]:
        """Re-type SkippedFinding[Finding] entries by looking up by finding ID."""
        matched: list[SkippedFinding[TFinding]] = []
        for entry in skipped:
            typed_finding = findings_by_id.get(entry.finding.id)
            if typed_finding is None:
                logger.warning(
                    f"Skipped finding id {entry.finding.id} not in input findings"
                )
                continue
            matched.append(SkippedFinding(finding=typed_finding, reason=entry.reason))
        return matched

    def _compute_not_flagged(
        self,
        findings_by_id: dict[str, TFinding],
        processed_ids: set[str],
        skipped: list[SkippedFinding[TFinding]],
    ) -> list[TFinding]:
        """Return findings LLM saw but didn't mention (kept via fail-safe)."""
        skipped_ids = {s.finding.id for s in skipped}
        not_flagged_ids = set(findings_by_id.keys()) - processed_ids - skipped_ids
        not_flagged = [findings_by_id[fid] for fid in not_flagged_ids]

        if not_flagged:
            logger.debug(
                f"{len(not_flagged)} findings not flagged by LLM, keeping as valid"
            )

        return not_flagged
