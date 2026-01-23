"""Result builder for processing purpose analysis output.

Handles construction of output messages and summaries.
Keeps the analyser focused on orchestration.
"""

import logging
from datetime import UTC, datetime

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas.types import (
    ProcessingPurposeIndicatorModel,
    ProcessingPurposeIndicatorOutput,
    ProcessingPurposeIndicatorSummary,
    PurposeBreakdown,
)
from .types import ProcessingPurposeAnalyserConfig

logger = logging.getLogger(__name__)


class ProcessingPurposeResultBuilder:
    """Builds output results for processing purpose analysis.

    Encapsulates all result construction logic, keeping the analyser
    focused on processing orchestration.
    """

    def __init__(self, config: ProcessingPurposeAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        output_schema: Schema,
        validation_result: ValidationResult[ProcessingPurposeIndicatorModel]
        | None = None,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Processing purpose findings (validated if LLM validation was applied).
            output_schema: Schema for output validation.
            validation_result: Validation result from orchestrator (None if validation disabled).

        Returns:
            Complete output message.

        """
        summary = self._build_findings_summary(findings)
        analysis_metadata = self._build_analysis_metadata(validation_result)

        output_model = ProcessingPurposeIndicatorOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"processing_purpose_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        logger.info(
            f"ProcessingPurposeAnalyser processed with {len(result_data['findings'])} findings"
        )

        return output_message

    def _build_findings_summary(
        self, findings: list[ProcessingPurposeIndicatorModel]
    ) -> ProcessingPurposeIndicatorSummary:
        """Build summary statistics for findings.

        Args:
            findings: List of validated findings.

        Returns:
            Summary with totals and per-purpose breakdown.

        """
        unique_purposes = set(f.purpose for f in findings)
        purpose_counts: dict[str, int] = {}

        for finding in findings:
            purpose_counts[finding.purpose] = purpose_counts.get(finding.purpose, 0) + 1

        purposes = [
            PurposeBreakdown(purpose=purpose, findings_count=count)
            for purpose, count in sorted(purpose_counts.items())
        ]

        return ProcessingPurposeIndicatorSummary(
            total_findings=len(findings),
            purposes_identified=len(unique_purposes),
            purposes=purposes,
        )

    def _build_analysis_metadata(
        self,
        validation_result: ValidationResult[ProcessingPurposeIndicatorModel]
        | None = None,
    ) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Args:
            validation_result: Optional validation result from orchestrator.

        Returns:
            Analysis metadata with all fields.

        """
        extra_fields: dict[str, object] = {
            "llm_validation_mode": self._config.llm_validation.llm_validation_mode,
            "analyser_version": "1.0.0",
        }

        # Add validation info if provided
        if validation_result:
            extra_fields["validation_summary"] = {
                "strategy": "orchestrated",
                "samples_validated": validation_result.samples_validated,
                "all_succeeded": validation_result.all_succeeded,
                "skipped_count": len(validation_result.skipped_samples),
            }

            # Map RemovedGroup to purposes_removed for backwards compatibility
            if validation_result.removed_groups:
                extra_fields["purposes_removed"] = [
                    {
                        "purpose": rg.concern_value,
                        "reason": rg.reason,
                        "require_review": rg.require_review,
                    }
                    for rg in validation_result.removed_groups
                ]

        return BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            **extra_fields,
        )
