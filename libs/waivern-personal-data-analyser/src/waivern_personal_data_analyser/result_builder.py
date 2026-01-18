"""Result builder for personal data analysis output.

Handles construction of output messages, summaries, and validation statistics.
Keeps the analyser focused on orchestration.
"""

import logging
from pprint import pformat

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas.types import (
    PersonalDataIndicatorModel,
    PersonalDataIndicatorOutput,
    PersonalDataIndicatorSummary,
    PersonalDataValidationSummary,
)
from .types import PersonalDataAnalyserConfig

logger = logging.getLogger(__name__)


class PersonalDataResultBuilder:
    """Builds output results for personal data analysis.

    Encapsulates all result construction logic, keeping the analyser
    focused on processing orchestration.
    """

    def __init__(self, config: PersonalDataAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        original_findings: list[PersonalDataIndicatorModel],
        validated_findings: list[PersonalDataIndicatorModel],
        validation_applied: bool,
        output_schema: Schema,
        validation_result: ValidationResult[PersonalDataIndicatorModel] | None = None,
    ) -> Message:
        """Build the complete output message.

        Args:
            original_findings: Findings before LLM validation.
            validated_findings: Findings after LLM validation.
            validation_applied: Whether validation was applied.
            output_schema: Schema for output validation.
            validation_result: Optional validation result from orchestrator.

        Returns:
            Complete validated output message.

        """
        summary = self._build_findings_summary(validated_findings)

        # Skip old-style validation_summary when using orchestrator - metadata tells the story
        validation_summary = None
        if validation_applied and validation_result is None:
            validation_summary = self._build_validation_summary(
                original_findings, validated_findings
            )

        analysis_metadata = self._build_analysis_metadata(validation_result)

        output_model = PersonalDataIndicatorOutput(
            findings=validated_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id="Personal_data_analysis",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"PersonalDataAnalyser processed with {len(result_data['findings'])} findings"
        )

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message

    def _build_findings_summary(
        self, findings: list[PersonalDataIndicatorModel]
    ) -> PersonalDataIndicatorSummary:
        """Build summary statistics for indicators.

        Args:
            findings: List of validated indicators.

        Returns:
            Summary statistics model.

        """
        return PersonalDataIndicatorSummary(
            total_findings=len(findings),
        )

    def _build_validation_summary(
        self,
        original_findings: list[PersonalDataIndicatorModel],
        validated_findings: list[PersonalDataIndicatorModel],
    ) -> PersonalDataValidationSummary:
        """Build LLM validation summary statistics.

        Args:
            original_findings: Original findings before validation.
            validated_findings: Findings after validation.

        Returns:
            Validation summary model.

        """
        original_count = len(original_findings)
        validated_count = len(validated_findings)
        false_positives_removed = original_count - validated_count

        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings "
            f"({false_positives_removed} false positives removed)"
        )

        return PersonalDataValidationSummary(
            llm_validation_enabled=True,
            original_findings_count=original_count,
            validated_findings_count=validated_count,
            false_positives_removed=false_positives_removed,
            validation_mode=self._config.llm_validation.llm_validation_mode,
        )

    def _build_analysis_metadata(
        self,
        validation_result: ValidationResult[PersonalDataIndicatorModel] | None = None,
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

            # Map RemovedGroup to categories_removed for output
            if validation_result.removed_groups:
                extra_fields["categories_removed"] = [
                    {
                        "category": rg.concern_value,
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
