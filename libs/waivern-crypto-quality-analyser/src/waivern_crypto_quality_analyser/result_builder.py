"""Result builder for crypto quality analysis output."""

import logging
from datetime import UTC, datetime
from pprint import pformat

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_schemas.crypto_quality_indicator import (
    CryptoQualityIndicatorModel,
    CryptoQualityIndicatorOutput,
    CryptoQualityIndicatorSummary,
)

from .types import CryptoQualityAnalyserConfig

logger = logging.getLogger(__name__)


class CryptoQualityResultBuilder:
    """Builds output results for crypto quality analysis.

    Simpler than personal data result builder: no LLM validation result
    to include in metadata, since quality assessment is deterministic.
    """

    def __init__(self, config: CryptoQualityAnalyserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[CryptoQualityIndicatorModel],
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Crypto quality indicators from pattern matching.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        summary = CryptoQualityIndicatorSummary(total_findings=len(findings))
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=False,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
        )

        output_model = CryptoQualityIndicatorOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"crypto_quality_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"CryptoQualityAnalyser processed with {len(result_data['findings'])} findings"
        )
        logger.debug(
            f"CryptoQualityAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message
