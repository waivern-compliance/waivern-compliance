"""Result builder for security evidence normaliser output."""

import logging
from datetime import UTC, datetime
from pprint import pformat

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_security_evidence.schemas.types import (
    SecurityEvidenceModel,
    SecurityEvidenceOutput,
    SecurityEvidenceSummary,
)

from .types import SecurityEvidenceNormaliserConfig

logger = logging.getLogger(__name__)


class SecurityEvidenceResultBuilder:
    """Builds output results for security evidence normalisation."""

    def __init__(self, config: SecurityEvidenceNormaliserConfig) -> None:
        """Initialise result builder with configuration.

        Args:
            config: Analyser configuration for metadata.

        """
        self._config = config

    def build_output_message(
        self,
        findings: list[SecurityEvidenceModel],
        output_schema: Schema,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Normalised security evidence items.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        summary = SecurityEvidenceSummary(total_findings=len(findings))
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.domain_ruleset,
            llm_validation_enabled=False,
        )

        output_model = SecurityEvidenceOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"security_evidence_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"SecurityEvidenceNormaliser produced {len(findings)} evidence items"
        )
        logger.debug(f"SecurityEvidenceNormaliser output:\n{pformat(result_data)}")

        return output_message
