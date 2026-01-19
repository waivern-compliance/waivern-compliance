"""Result builder for data subject analysis output.

Handles construction of output messages and summaries.
Keeps the analyser focused on orchestration.
"""

import logging
from datetime import UTC, datetime

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
        indicators: list[DataSubjectIndicatorModel],
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            indicators: Data subject indicators.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(indicators)
        analysis_metadata = self._build_analysis_metadata()

        output_model = DataSubjectIndicatorOutput(
            findings=indicators,
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
