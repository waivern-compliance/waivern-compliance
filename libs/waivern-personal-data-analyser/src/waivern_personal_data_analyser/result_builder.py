"""Result builder for personal data analysis output.

Handles construction of output messages, summaries, and validation statistics.
Keeps the analyser focused on orchestration.
"""

import logging
from pprint import pformat

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
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            original_findings: Findings before LLM validation.
            validated_findings: Findings after LLM validation.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        summary = self._build_findings_summary(validated_findings)

        validation_summary = None
        if (
            self._config.llm_validation.enable_llm_validation
            and len(original_findings) > 0
        ):
            validation_summary = self._build_validation_summary(
                original_findings, validated_findings
            )

        analysis_metadata = self._build_analysis_metadata()

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

    def _build_analysis_metadata(self) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Returns:
            Analysis metadata with all fields.

        """
        return BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
        )
