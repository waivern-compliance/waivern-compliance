"""Source code validation strategy for processing purpose findings.

Builds EXTENDED_CONTEXT ``LLMRequest`` objects that group findings by source
file with full file content attached. The executor dispatches them; outcome
categorisation is inherited from ``FilteringValidationStrategy``.
"""

from typing import override

from pydantic import BaseModel
from waivern_analysers_shared.llm_validation.models import LLMValidationResponseModel
from waivern_analysers_shared.llm_validation.strategy import (
    FilteringValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.types import JsonValue
from waivern_llm import BatchingMode, ItemGroup, LLMRequest
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorModel,
)

from waivern_processing_purpose_analyser.prompts import SourceCodePromptBuilder

from .providers import SourceCodeSourceProvider


class SourceCodeStrategyState(BaseModel):
    """Persistence state for ``SourceCodeValidationStrategy`` across dispatch rounds.

    Captures the file content map held by the strategy's source provider so
    that the orchestrator can be reconstructed (with its primary strategy in
    the correct shape) on the fallback or batch-mode resume rounds.
    """

    source_contents: dict[str, str]


class SourceCodeValidationStrategy(
    FilteringValidationStrategy[ProcessingPurposeIndicatorModel]
):
    """Validation strategy for source_code schema findings.

    Uses full file content in prompts for richer validation context.
    Groups findings by source file and uses EXTENDED_CONTEXT batching
    so each source file gets its own LLM call.
    """

    def __init__(self, source_provider: SourceCodeSourceProvider) -> None:
        """Initialise with a source provider.

        Args:
            source_provider: Provider for file paths and content.

        """
        self._source_provider = source_provider

    @override
    def export_persistence_state(self) -> dict[str, JsonValue] | None:
        """Return the strategy's source content map for multi-round reconstruction.

        The strategy's identity is its ``source_provider``, which holds a file
        content map that must survive across dispatch rounds so that the
        primary strategy can be reconstructed identically on the
        fallback/resume path.
        """
        return SourceCodeStrategyState(
            source_contents=self._source_provider.snapshot_contents()
        ).model_dump(mode="json")

    @override
    def prepare_validation(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[
        list[ProcessingPurposeIndicatorModel],
        LLMRequest[ProcessingPurposeIndicatorModel] | None,
    ]:
        """Build an EXTENDED_CONTEXT LLMRequest grouped by source file."""
        if not findings:
            return ([], None)

        request: LLMRequest[ProcessingPurposeIndicatorModel] = LLMRequest(
            groups=self._create_groups_by_source(findings),
            prompt_builder=SourceCodePromptBuilder(
                validation_mode=config.llm_validation_mode
            ),
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id=run_id,
        )
        return (findings, request)

    def _create_groups_by_source(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
    ) -> list[ItemGroup[ProcessingPurposeIndicatorModel]]:
        """Group findings by source file with content.

        Each group contains all findings from a single source file, along with
        the file content for context-aware validation. Findings without source
        metadata are grouped together with ``content=None`` (BatchPlanner will
        handle these as MISSING_CONTENT).
        """
        findings_by_source: dict[str, list[ProcessingPurposeIndicatorModel]] = {}

        for finding in findings:
            source = finding.metadata.source if finding.metadata else None
            source_key = source or "__no_source__"
            findings_by_source.setdefault(source_key, []).append(finding)

        groups: list[ItemGroup[ProcessingPurposeIndicatorModel]] = []
        for source, source_findings in findings_by_source.items():
            if source == "__no_source__":
                groups.append(
                    ItemGroup(items=source_findings, content=None, group_id=None)
                )
            else:
                content = self._source_provider.get_source_content(source)
                groups.append(
                    ItemGroup(items=source_findings, content=content, group_id=source)
                )

        return groups
