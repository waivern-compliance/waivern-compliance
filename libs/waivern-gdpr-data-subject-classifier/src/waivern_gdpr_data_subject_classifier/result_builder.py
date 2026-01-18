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

logger = logging.getLogger(__name__)


class GDPRDataSubjectResultBuilder:
    """Builds output results for GDPR data subject classification.

    Encapsulates all result construction logic, keeping the classifier
    focused on processing orchestration.
    """

    def build_output_message(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        output_schema: Schema,
        ruleset_name: str,
        ruleset_version: str,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Classified GDPR data subject findings.
            output_schema: Schema for output validation.
            ruleset_name: Name of the ruleset used.
            ruleset_version: Version of the ruleset used.

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(findings)
        analysis_metadata = self._build_analysis_metadata(ruleset_name, ruleset_version)

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

        return GDPRDataSubjectSummary(
            total_findings=len(findings),
            categories_identified=sorted(categories),
            high_risk_count=high_risk_count,
        )

    def _build_analysis_metadata(
        self, ruleset_name: str, ruleset_version: str
    ) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Args:
            ruleset_name: Name of the ruleset used.
            ruleset_version: Version of the ruleset used.

        Returns:
            Analysis metadata with all fields.

        """
        return BaseAnalysisOutputMetadata(
            ruleset_used=f"local/{ruleset_name}/{ruleset_version}",
            llm_validation_enabled=False,
        )
