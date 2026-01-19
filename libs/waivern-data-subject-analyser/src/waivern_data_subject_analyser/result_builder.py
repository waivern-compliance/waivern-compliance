"""Result builder for data subject analysis output.

Handles construction of output messages and summaries.
Keeps the analyser focused on orchestration.
"""

import logging
from datetime import UTC, datetime

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas.types import (
    DataSubjectIndicatorModel,
    DataSubjectIndicatorOutput,
    DataSubjectIndicatorSummary,
)
from .types import DataSubjectAnalyserConfig

logger = logging.getLogger(__name__)


class DataSubjectResultBuilder:
    """Builds output results for data subject analysis.

    Encapsulates all result construction logic, keeping the analyser
    focused on processing orchestration.
    """

    def __init__(self, config: DataSubjectAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[DataSubjectIndicatorModel],
        output_schema: Schema,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None = None,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Data subject indicators (validated if LLM validation was applied).
            output_schema: Schema for output validation.
            validation_result: Validation result from orchestrator (None if validation disabled).

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(findings)
        analysis_metadata = self._build_analysis_metadata(validation_result)

        output_model = DataSubjectIndicatorOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"data_subject_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"DataSubjectAnalyser processed with {len(result_data['findings'])} indicators"
        )

        return output_message

    def _build_summary(
        self, indicators: list[DataSubjectIndicatorModel]
    ) -> DataSubjectIndicatorSummary:
        """Build summary statistics for data subject indicators.

        Args:
            indicators: List of data subject indicators.

        Returns:
            Summary statistics model.

        """
        return DataSubjectIndicatorSummary(
            total_indicators=len(indicators),
            categories_identified=list(set(i.subject_category for i in indicators)),
        )

    def _build_analysis_metadata(
        self,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None = None,
    ) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Args:
            validation_result: Validation result from orchestrator (None if validation disabled).

        Returns:
            Analysis metadata with all fields.

        """
        extra_fields: dict[str, object] = {
            "llm_validation_mode": self._config.llm_validation.llm_validation_mode,
            "analyser_version": "1.0.0",
        }

        # Add validation info when orchestrator was used
        if validation_result:
            extra_fields["validation_summary"] = {
                "strategy": "orchestrated",
                "samples_validated": validation_result.samples_validated,
                "all_succeeded": validation_result.all_succeeded,
                "skipped_count": len(validation_result.skipped_samples),
            }

            # Map RemovedGroup to subject_categories_removed for output
            if validation_result.removed_groups:
                extra_fields["subject_categories_removed"] = [
                    {
                        "subject_category": rg.concern_value,
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
