"""Result builder for GDPR data subject classification output.

Handles construction of output messages and summaries.
Keeps the classifier focused on orchestration.
"""

import logging

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas import (
    GDPRDataSubjectFindingModel,
    GDPRDataSubjectFindingOutput,
    GDPRDataSubjectSummary,
)
from .types import GDPRDataSubjectClassifierConfig
from .validation.models import RiskModifierValidationResult

logger = logging.getLogger(__name__)


class GDPRDataSubjectResultBuilder:
    """Builds output results for GDPR data subject classification.

    Encapsulates all result construction logic, keeping the classifier
    focused on processing orchestration.
    """

    def __init__(self, config: GDPRDataSubjectClassifierConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Classifier configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        output_schema: Schema,
        ruleset_name: str,
        ruleset_version: str,
        validation_result: RiskModifierValidationResult | None,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Classified GDPR data subject findings.
            output_schema: Schema for output validation.
            ruleset_name: Name of the ruleset used.
            ruleset_version: Version of the ruleset used.
            validation_result: Validation result from LLM strategy (None if regex path).

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(findings)
        analysis_metadata = self._build_analysis_metadata(
            ruleset_name, ruleset_version, validation_result
        )

        output = GDPRDataSubjectFindingOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id="gdpr_data_subject_classification",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"GDPRDataSubjectClassifier processed with {len(result_data['findings'])} findings"
        )

        return output_message

    def _build_summary(
        self, findings: list[GDPRDataSubjectFindingModel]
    ) -> GDPRDataSubjectSummary:
        """Build summary statistics from classified findings.

        Args:
            findings: List of classified findings.

        Returns:
            Summary statistics model.

        """
        categories = list({f.data_subject_category for f in findings})
        high_risk_count = len([f for f in findings if f.risk_modifiers])
        requires_review_count = len([f for f in findings if f.require_review is True])

        return GDPRDataSubjectSummary(
            total_findings=len(findings),
            categories_identified=sorted(categories),
            high_risk_count=high_risk_count,
            requires_review_count=requires_review_count,
        )

    def _build_analysis_metadata(
        self,
        ruleset_name: str,
        ruleset_version: str,
        validation_result: RiskModifierValidationResult | None,
    ) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Args:
            ruleset_name: Name of the ruleset used.
            ruleset_version: Version of the ruleset used.
            validation_result: Validation result from LLM strategy (None if regex path).

        Returns:
            Analysis metadata with all fields.

        """
        extra_fields: dict[str, object] = {}

        # Add validation summary for observability
        if validation_result is not None:
            extra_fields["validation_summary"] = {
                "method_used": "llm",
                "total_findings": validation_result.total_findings,
                "llm_samples_processed": validation_result.total_sampled,
                "categories_validated": len(validation_result.category_results),
            }
        else:
            extra_fields["validation_summary"] = {
                "method_used": "regex",
            }

        return BaseAnalysisOutputMetadata(
            ruleset_used=f"local/{ruleset_name}/{ruleset_version}",
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            **extra_fields,
        )
