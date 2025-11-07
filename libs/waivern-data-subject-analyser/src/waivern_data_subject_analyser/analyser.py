"""Data subject analysis analyser for GDPR Article 30(1)(c) compliance."""

import importlib
import logging
from datetime import UTC, datetime
from types import ModuleType
from typing import override

from waivern_core import Analyser
from waivern_core.message import Message
from waivern_core.schemas import (
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    Schema,
)
from waivern_llm import BaseLLMService

from .pattern_matcher import DataSubjectPatternMatcher
from .schemas.types import DataSubjectFindingModel
from .types import DataSubjectAnalyserConfig

logger = logging.getLogger(__name__)

_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("data_subject_finding", "1.0.0")]


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

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module with read() function

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_data_subject_analyser.schema_readers.{module_name}"
        )

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Output schema to load producer for

        Returns:
            Producer module with produce() function

        Raises:
            ModuleNotFoundError: If producer module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_data_subject_analyser.schema_producers.{module_name}"
        )

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
        """Process data to identify data subjects using dynamic reader/producer."""
        logger.info("Starting data subject analysis")

        # Validate input message
        Analyser.validate_input_message(message, input_schema)

        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Load reader and transform to canonical Pydantic model
        reader = self._load_reader(input_schema)
        typed_data = reader.read(message.content)

        # Process each data item using the pattern matcher
        findings: list[DataSubjectFindingModel] = []
        for data_item in typed_data.data:
            content = data_item.content
            metadata = data_item.metadata

            # Find patterns using pattern matcher
            item_findings = self._pattern_matcher.find_patterns(content, metadata)
            findings.extend(item_findings)

        # Update analysis chain with this analyser
        updated_chain_dicts = self.update_analyses_chain(
            message, "data_subject_analyser"
        )
        # Convert to strongly-typed models for WCT
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Create and validate output message
        return self._create_output_message(findings, output_schema, updated_chain)

    def _create_output_message(
        self,
        findings: list[DataSubjectFindingModel],
        output_schema: Schema,
        analyses_chain: list[AnalysisChainEntry],
    ) -> Message:
        """Create output message with data subject findings using producer.

        Args:
            findings: List of data subject findings
            output_schema: Output schema for validation
            analyses_chain: Updated analysis chain with proper ordering

        Returns:
            Message containing data subject analysis results

        """
        # Create summary statistics
        total_classifications = len(findings)
        categories_identified = list(set(f.primary_category for f in findings))

        summary = {
            "total_classifications": total_classifications,
            "categories_identified": categories_identified,
        }

        # Create analysis metadata for chaining support
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            analyses_chain=analyses_chain,
        )

        # Load producer and transform to wire format
        producer = self._load_producer(output_schema)
        result_data = producer.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        output_message = Message(
            id=f"data_subject_analysis_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.info(
            f"DataSubjectAnalyser processed with {len(result_data['findings'])} findings"
        )

        return output_message
