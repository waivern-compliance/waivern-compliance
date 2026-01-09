"""Processing purpose analysis analyser for GDPR compliance."""

import importlib
import logging
from types import ModuleType
from typing import override

from waivern_core import Analyser, InputRequirement, update_analyses_chain
from waivern_core.message import Message
from waivern_core.schemas import (
    AnalysisChainEntry,
    ChainEntryValidationStats,
    Schema,
)
from waivern_llm import BaseLLMService

from .llm_validation_strategy import processing_purpose_validation_strategy
from .protocols import SchemaInputHandler
from .result_builder import ProcessingPurposeResultBuilder
from .schemas.types import ProcessingPurposeFindingModel
from .types import ProcessingPurposeAnalyserConfig

logger = logging.getLogger(__name__)


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        config: ProcessingPurposeAnalyserConfig,
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the processing purpose analyser with dependency injection.

        Args:
            config: Configuration object with analysis settings
            llm_service: Optional LLM service for validation (injected by factory)

        """
        self._config = config
        self._llm_service = llm_service
        self._result_builder = ProcessingPurposeResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        The reader module provides both read() and create_handler() functions,
        co-locating schema reading and handler creation.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module with read() and create_handler() functions

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_processing_purpose_analyser.schema_readers.{module_name}"
        )

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        ProcessingPurposeAnalyser accepts either standard_input OR source_code schema.
        Each is a valid alternative input.
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
            [InputRequirement("source_code", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("processing_purpose_finding", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to identify processing purposes.

        Supports multiple input schema types. The reader module for each schema
        provides both data reading and handler creation, keeping schema knowledge
        co-located.

        Args:
            inputs: List of input messages (single message expected)
            output_schema: Expected output schema

        Returns:
            Output message with processing purpose findings

        """
        logger.info("Starting processing purpose analysis")

        message = inputs[0]
        input_schema = message.schema
        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Load reader and process findings
        reader = self._load_reader_module(input_schema)
        input_data = reader.read(message.content)
        handler = self._create_handler(reader)
        findings = handler.analyse(input_data)

        # Apply LLM validation
        validated_findings, validation_applied = self._validate_findings_with_llm(
            findings
        )

        # Build analysis chain
        chain_validation_stats = ChainEntryValidationStats.from_counts(
            validation_applied=validation_applied,
            original_count=len(findings),
            validated_count=len(validated_findings),
            validation_mode=self._config.llm_validation.llm_validation_mode,
        )
        updated_chain_dicts = update_analyses_chain(
            message,
            "processing_purpose_analyser",
            validation_stats=chain_validation_stats,
        )
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Build output message
        return self._result_builder.build_output_message(
            findings,
            validated_findings,
            validation_applied,
            output_schema,
            updated_chain,
        )

    def _load_reader_module(self, schema: Schema) -> ModuleType:
        """Load reader module for the given schema.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module

        Raises:
            ValueError: If schema is not supported

        """
        try:
            return self._load_reader(schema)
        except (ModuleNotFoundError, AttributeError) as e:
            raise ValueError(f"Unsupported input schema: {schema.name}") from e

    def _create_handler(self, reader: ModuleType) -> SchemaInputHandler:
        """Create handler from reader module.

        Args:
            reader: Reader module with create_handler() function

        Returns:
            Handler implementing SchemaInputHandler protocol

        """
        return reader.create_handler(self._config)

    def _validate_findings_with_llm(
        self, findings: list[ProcessingPurposeFindingModel]
    ) -> tuple[list[ProcessingPurposeFindingModel], bool]:
        """Validate findings using LLM if enabled and available.

        Args:
            findings: List of findings to validate

        Returns:
            Tuple of (validated findings, validation_was_applied)

        """
        if not self._config.llm_validation.enable_llm_validation:
            return findings, False

        if not findings:
            return findings, False

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False

        try:
            validated_findings, validation_succeeded = (
                processing_purpose_validation_strategy(
                    findings, self._config.llm_validation, self._llm_service
                )
            )
            return validated_findings, validation_succeeded
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning original findings due to validation error")
            return findings, False
