"""Result builder for processing purpose analysis output.

Handles construction of output messages, summaries, and validation statistics.
Keeps the analyser focused on orchestration.
"""

import logging

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas.types import (
    ProcessingPurposeFindingModel,
    ProcessingPurposeFindingOutput,
    ProcessingPurposeSummary,
    ProcessingPurposeValidationSummary,
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
        original_findings: list[ProcessingPurposeFindingModel],
        validated_findings: list[ProcessingPurposeFindingModel],
        validation_applied: bool,
        output_schema: Schema,
        validation_result: ValidationResult[ProcessingPurposeFindingModel]
        | None = None,
    ) -> Message:
        """Build the complete output message.

        Args:
            original_findings: Findings before LLM validation.
            validated_findings: Findings after LLM validation.
            validation_applied: Whether validation was applied.
            output_schema: Schema for output validation.
            validation_result: Optional validation result from orchestrator.

        Returns:
            Complete output message.

        """
        summary = self._build_findings_summary(validated_findings)

        # Skip old-style validation_summary when using orchestrator - metadata tells the story
        validation_summary = None
        if validation_applied and validation_result is None:
            validation_summary = self._build_validation_summary(
                original_findings, validated_findings
            )

        analysis_metadata = self._build_analysis_metadata(validation_result)

        output_model = ProcessingPurposeFindingOutput(
            findings=validated_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id="Processing_purpose_analysis",
            content=result_data,
            schema=output_schema,
        )

        logger.info(
            f"ProcessingPurposeAnalyser processed with {len(result_data['findings'])} findings"
        )

        return output_message

    def _build_findings_summary(
        self, findings: list[ProcessingPurposeFindingModel]
    ) -> ProcessingPurposeSummary:
        """Build summary statistics for findings.

        Args:
            findings: List of validated findings.

        Returns:
            Summary with purpose categories, totals, and per-purpose breakdown.

        """
        unique_purposes = set(f.purpose for f in findings)
        purpose_categories: dict[str, int] = {}
        purpose_counts: dict[str, int] = {}

        for finding in findings:
            category = finding.purpose_category or "uncategorised"
            purpose_categories[category] = purpose_categories.get(category, 0) + 1
            purpose_counts[finding.purpose] = purpose_counts.get(finding.purpose, 0) + 1

        purposes = [
            PurposeBreakdown(purpose=purpose, findings_count=count)
            for purpose, count in sorted(purpose_counts.items())
        ]

        return ProcessingPurposeSummary(
            total_findings=len(findings),
            purposes_identified=len(unique_purposes),
            purpose_categories=purpose_categories,
            purposes=purposes,
        )

    def _build_validation_summary(
        self,
        original_findings: list[ProcessingPurposeFindingModel],
        validated_findings: list[ProcessingPurposeFindingModel],
    ) -> ProcessingPurposeValidationSummary:
        """Build LLM validation summary statistics.

        Args:
            original_findings: Findings before validation.
            validated_findings: Findings after validation.

        Returns:
            Validation summary with effectiveness metrics.

        """
        original_count = len(original_findings)
        validated_count = len(validated_findings)
        false_positives_removed = original_count - validated_count
        validation_effectiveness = (false_positives_removed / original_count) * 100

        original_purposes = {f.purpose for f in original_findings}
        validated_purposes = {f.purpose for f in validated_findings}
        removed_purposes = original_purposes - validated_purposes

        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings "
            f"({false_positives_removed} false positives removed, "
            f"{validation_effectiveness:.1f}% effectiveness)"
        )

        return ProcessingPurposeValidationSummary(
            llm_validation_enabled=True,
            original_findings_count=original_count,
            validated_findings_count=validated_count,
            false_positives_removed=false_positives_removed,
            validation_effectiveness_percentage=round(validation_effectiveness, 1),
            validation_mode=self._config.llm_validation.llm_validation_mode,
            removed_purposes=sorted(list(removed_purposes)),
        )

    def _build_analysis_metadata(
        self,
        validation_result: ValidationResult[ProcessingPurposeFindingModel]
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
