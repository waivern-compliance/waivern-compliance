"""Result builder for data collection analyser output."""

import logging
from datetime import UTC, datetime
from pprint import pformat

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_schemas.data_collection_indicator import (
    CollectionTypeBreakdown,
    DataCollectionIndicatorModel,
    DataCollectionIndicatorOutput,
    DataCollectionIndicatorSummary,
)

from .types import DataCollectionAnalyserConfig

logger = logging.getLogger(__name__)


class DataCollectionResultBuilder:
    """Builds output results for data collection analysis."""

    def __init__(self, config: DataCollectionAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[DataCollectionIndicatorModel],
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Data collection indicators from pattern matching.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        category_counts: dict[str, int] = {}
        for finding in findings:
            category_counts[finding.collection_type] = (
                category_counts.get(finding.collection_type, 0) + 1
            )

        categories = sorted(
            [
                CollectionTypeBreakdown(collection_type=category, findings_count=count)
                for category, count in category_counts.items()
            ],
            key=lambda c: c.findings_count,
            reverse=True,
        )

        summary = DataCollectionIndicatorSummary(
            total_findings=len(findings),
            categories_identified=len(categories),
            categories=categories,
        )

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=False,
        )

        output_model = DataCollectionIndicatorOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"data_collection_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(f"DataCollectionAnalyser processed with {len(findings)} findings")
        logger.debug(
            f"DataCollectionAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message
