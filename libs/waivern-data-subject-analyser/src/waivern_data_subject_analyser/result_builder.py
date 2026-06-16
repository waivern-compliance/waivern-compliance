"""Result builder for data subject analysis output.

Handles construction of output messages and summaries.
Keeps the analyser focused on orchestration.
"""

import logging
from datetime import UTC, datetime

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_schemas.data_subject_indicator import (
    DataSubjectIndicatorModel,
    DataSubjectIndicatorOutput,
    DataSubjectIndicatorSummary,
)
from waivern_schemas.removed_findings import RemovedFinding, RemovedFindingsOutput

from .types import DataSubjectAnalyserConfig

_REMOVED_FINDINGS_SCHEMA = Schema("removed_findings", "1.0.0")

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
        findings: list[DataSubjectIndicatorModel],
        output_schema: Schema,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None = None,
    ) -> Message:
        """Build the complete output message.

        Args:
            findings: Data subject indicators (validated if LLM validation was applied).
            output_schema: Schema for output validation.
            validation_result: Validation result from orchestrator (None if validation disabled).

        Returns:
            Complete validated output message.

        """
        summary = self._build_summary(findings)
        analysis_metadata = self._build_analysis_metadata(validation_result)

        output_model = DataSubjectIndicatorOutput(
            findings=findings,
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

    def build_sidecars(
        self,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None,
        run_id: str,
    ) -> list[Message]:
        """Build the analyser's sidecar Messages.

        Dispatches to one private builder per sidecar type. Each builder
        returns ``Message | None`` so this method can filter the absent ones
        out — a sidecar is "absent" when there is no content to record.
        Adding a new sidecar type is a new ``_build_X_sidecar`` method plus
        one line here; the analyser call site does not change.
        """
        candidates = [
            self._build_removed_findings_sidecar(validation_result, run_id),
        ]
        return [s for s in candidates if s is not None]

    def _build_removed_findings_sidecar(
        self,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None,
        run_id: str,
    ) -> Message | None:
        """Build the audit-trail sidecar listing LLM-removed findings.

        Returns None when validation was disabled or produced no removals —
        there is no audit content to record.
        """
        if validation_result is None or not validation_result.removed_findings:
            return None

        payload = RemovedFindingsOutput(
            analyser_name="data_subject_analyser",
            run_id=run_id,
            ruleset=self._config.pattern_matching.ruleset,
            removed_findings=[
                RemovedFinding(
                    original_finding=item.finding.model_dump(mode="json"),
                    reason=item.reason,
                )
                for item in validation_result.removed_findings
            ],
        )

        sidecar = Message(
            id=f"data_subject_removed_findings_{datetime.now(UTC).isoformat()}",
            content=payload.model_dump(mode="json"),
            schema=_REMOVED_FINDINGS_SCHEMA,
        )
        sidecar.validate()
        return sidecar

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

    def _build_analysis_metadata(
        self,
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None = None,
    ) -> BaseAnalysisOutputMetadata:
        """Build analysis metadata for output.

        Args:
            validation_result: Validation result from orchestrator (None if validation disabled).

        Returns:
            Analysis metadata with all fields.

        """
        extra_fields: dict[str, object] = {
            "llm_validation_mode": self._config.llm_validation.llm_validation_mode,
            "analyser_version": "1.0.0",
        }

        # Add validation info when orchestrator was used
        if validation_result:
            extra_fields["validation_summary"] = {
                "strategy": "orchestrated",
                "samples_validated": validation_result.samples_validated,
                "all_succeeded": validation_result.all_succeeded,
                "skipped_count": len(validation_result.skipped_samples),
                # Pre-emitted so the key is always present once validation ran;
                # DAGExecutor stamps the sidecar's artifact_id when removals
                # produced an audit-trail sidecar.
                "removed_findings_artifact_id": None,
            }

            # Map RemovedGroup to subject_categories_removed for output
            if validation_result.removed_groups:
                extra_fields["subject_categories_removed"] = [
                    {
                        "subject_category": rg.concern_value,
                        "reason": rg.reason,
                        "require_review": rg.require_review,
                    }
                    for rg in validation_result.removed_groups
                ]

        return BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            **extra_fields,
        )
