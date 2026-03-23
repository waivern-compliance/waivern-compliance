"""Result builder for service integration analyser output."""

import logging
from datetime import UTC, datetime
from pprint import pformat

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_schemas.service_integration_indicator import (
    ServiceCategoryBreakdown,
    ServiceIntegrationIndicatorModel,
    ServiceIntegrationIndicatorOutput,
    ServiceIntegrationIndicatorSummary,
)

from .types import ServiceIntegrationAnalyserConfig

logger = logging.getLogger(__name__)


class ServiceIntegrationResultBuilder:
    """Builds output results for service integration analysis."""

    def __init__(self, config: ServiceIntegrationAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[ServiceIntegrationIndicatorModel],
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Service integration indicators from pattern matching.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        category_counts: dict[str, int] = {}
        for finding in findings:
            category_counts[finding.service_category] = (
                category_counts.get(finding.service_category, 0) + 1
            )

        categories = sorted(
            [
                ServiceCategoryBreakdown(
                    service_category=category, findings_count=count
                )
                for category, count in category_counts.items()
            ],
            key=lambda c: c.findings_count,
            reverse=True,
        )

        summary = ServiceIntegrationIndicatorSummary(
            total_findings=len(findings),
            categories_identified=len(categories),
            categories=categories,
        )

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=False,
        )

        output_model = ServiceIntegrationIndicatorOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"service_integration_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"ServiceIntegrationAnalyser processed with {len(findings)} findings"
        )
        logger.debug(
            f"ServiceIntegrationAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message
