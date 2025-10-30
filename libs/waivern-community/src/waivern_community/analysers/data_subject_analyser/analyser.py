"""Data subject analysis analyser for GDPR Article 30(1)(c) compliance."""

import logging
from datetime import UTC, datetime
from typing import override

from waivern_core import Analyser
from waivern_core.message import Message
from waivern_core.schemas import (
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseMetadata,
    Schema,
    StandardInputDataModel,
    StandardInputSchema,
)
from waivern_llm import BaseLLMService

from .pattern_matcher import DataSubjectPatternMatcher
from .schemas import DataSubjectFindingSchema
from .schemas.types import DataSubjectFindingModel
from .types import DataSubjectAnalyserConfig

logger = logging.getLogger(__name__)

_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [StandardInputSchema()]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [DataSubjectFindingSchema()]


class DataSubjectAnalyser(Analyser):
    """Analyser for identifying data subjects for GDPR Article 30(1)(c) compliance.

    This analyser identifies and categorises data subjects from various data sources
    to help organisations maintain systematic records of data processing activities.
    """

    def __init__(
        self,
        config: DataSubjectAnalyserConfig,
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the data subject analyser with configuration and dependencies.

        Args:
            config: Analyser configuration
            llm_service: Optional LLM service for validation (injected by DI)

        """
        self._config = config
        self._pattern_matcher = DataSubjectPatternMatcher(config.pattern_matching)
        self._llm_service = llm_service

    @classmethod
    @override
    def get_name(cls) -> str:
        """Get the name of the analyser."""
        return "data_subject_analyser"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return _SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process data to identify data subjects."""
        logger.info("Starting data subject analysis")

        # Validate input message
        Analyser.validate_input_message(message, input_schema)

        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Process standard_input schema data
        if isinstance(input_schema, StandardInputSchema):
            typed_data = StandardInputDataModel[BaseMetadata].model_validate(
                message.content
            )
            findings = self._process_standard_input_data(typed_data)
        else:
            raise ValueError(f"Unsupported input schema: {input_schema.name}")

        # Update analysis chain with this analyser
        updated_chain_dicts = self.update_analyses_chain(
            message, "data_subject_analyser"
        )
        # Convert to strongly-typed models for WCT
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Create and validate output message
        return self._create_output_message(
            findings, input_schema, output_schema, updated_chain
        )

    def _process_standard_input_data(
        self, typed_data: StandardInputDataModel[BaseMetadata]
    ) -> list[DataSubjectFindingModel]:
        """Process standard_input schema data.

        Args:
            typed_data: Validated standard input data

        Returns:
            List of data subject findings

        """
        findings: list[DataSubjectFindingModel] = []

        for data_item in typed_data.data:
            content = data_item.content
            metadata = data_item.metadata

            # Find patterns using pattern matcher
            item_findings = self._pattern_matcher.find_patterns(content, metadata)
            findings.extend(item_findings)

        return findings

    def _create_output_message(
        self,
        findings: list[DataSubjectFindingModel],
        input_schema: Schema,
        output_schema: Schema,
        analyses_chain: list[AnalysisChainEntry],
    ) -> Message:
        """Create output message with data subject findings.

        Args:
            findings: List of data subject findings
            input_schema: Input schema used for processing
            output_schema: Output schema for validation
            analyses_chain: Updated analysis chain with proper ordering

        Returns:
            Message containing data subject analysis results

        """
        # Create summary statistics
        total_classifications = len(findings)
        categories_identified = list(set(f.primary_category for f in findings))

        # Create analysis metadata for chaining support
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            analyses_chain=analyses_chain,
        )

        # Build complete output structure
        output_content = {
            "findings": [
                finding.model_dump(mode="json", exclude_none=True)
                for finding in findings
            ],
            "summary": {
                "total_classifications": total_classifications,
                "categories_identified": categories_identified,
            },
            "analysis_metadata": analysis_metadata.model_dump(
                mode="json", exclude_none=True
            ),
        }

        return Message(
            id=f"data_subject_analysis_{datetime.now(UTC).isoformat()}",
            content=output_content,
            schema=output_schema,
        )
