"""Result builder for GDPR personal data classification output.

Handles construction of output messages and summaries.
Keeps the classifier focused on orchestration.
"""

import logging

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas import (
    GDPRPersonalDataFindingModel,
    GDPRPersonalDataFindingOutput,
    GDPRPersonalDataSummary,
)

logger = logging.getLogger(__name__)


class GDPRClassifierResultBuilder:
    """Builds output results for GDPR personal data classification.

    Encapsulates all result construction logic, keeping the classifier
    focused on processing orchestration.
    """

    def build_output_message(
        self,
        findings: list[GDPRPersonalDataFindingModel],
        output_schema: Schema,
        ruleset_name: str,
        ruleset_version: str,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Classified GDPR findings.
            output_schema: Schema for output validation.
            ruleset_name: Name of the ruleset used.
            ruleset_version: Version of the ruleset used.

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(findings)
        analysis_metadata = self._build_analysis_metadata(ruleset_name, ruleset_version)

        output = GDPRPersonalDataFindingOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id="gdpr_personal_data_classification",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"GDPRPersonalDataClassifier processed with {len(result_data['findings'])} findings"
        )

        return output_message

    def _build_summary(
        self, findings: list[GDPRPersonalDataFindingModel]
    ) -> GDPRPersonalDataSummary:
        """Build summary statistics from classified findings.

        Args:
            findings: List of classified findings.

        Returns:
            Summary statistics model.

        """
        return GDPRPersonalDataSummary(
            total_findings=len(findings),
            special_category_count=len([f for f in findings if f.special_category]),
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
