"""Result builder for security control analyser output."""

import logging
from datetime import UTC, datetime
from pprint import pformat

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_security_evidence import (
    SecurityEvidenceModel,
    SecurityEvidenceOutput,
    SecurityEvidenceSummary,
)
from waivern_security_evidence.schemas.types import DomainBreakdown

from .types import SecurityControlAnalyserConfig

logger = logging.getLogger(__name__)


class SecurityControlResultBuilder:
    """Builds output results for security control analysis."""

    def __init__(self, config: SecurityControlAnalyserConfig) -> None:
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
            findings: Security evidence items from pattern matching.
            output_schema: Schema for output validation.

        Returns:
            Complete validated output message.

        """
        domain_counts: dict[str, int] = {}
        for finding in findings:
            domain_counts[finding.security_domain] = (
                domain_counts.get(finding.security_domain, 0) + 1
            )
        domains = sorted(
            [
                DomainBreakdown(security_domain=domain, findings_count=count)
                for domain, count in domain_counts.items()
            ],
            key=lambda d: d.findings_count,
            reverse=True,
        )
        summary = SecurityEvidenceSummary(
            total_findings=len(findings),
            domains_identified=len(domains),
            domains=domains,
        )
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=False,
        )

        output_model = SecurityEvidenceOutput(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id=f"security_control_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(f"SecurityControlAnalyser processed with {len(findings)} findings")
        logger.debug(
            f"SecurityControlAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message
