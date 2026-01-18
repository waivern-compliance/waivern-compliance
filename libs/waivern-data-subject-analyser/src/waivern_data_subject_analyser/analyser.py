"""Data subject analysis analyser for GDPR Article 30(1)(c) compliance."""

import importlib
import logging
from types import ModuleType
from typing import override

from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BaseLLMService

from .result_builder import DataSubjectResultBuilder
from .schemas.types import DataSubjectIndicatorModel
from .types import DataSubjectAnalyserConfig

logger = logging.getLogger(__name__)


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
        self._result_builder = DataSubjectResultBuilder(config)
        # TODO: LLM validation is not yet implemented for DataSubjectAnalyser.
        # The llm_service is accepted for interface consistency with other analysers
        # and to prepare for future implementation. When implementing:
        # 1. Create llm_validation_strategy.py similar to personal-data-analyser
        # 2. Add validation prompts in prompts/ directory
        # 3. Call validation after pattern matching in process()
        # 4. Add comprehensive tests for the validation strategy
        # 5. Add integration tests (see personal-data-analyser's test_integration.py)
        self._llm_service = llm_service

    @classmethod
    @override
    def get_name(cls) -> str:
        """Get the name of the analyser."""
        return "data_subject_analyser"

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
            f"waivern_data_subject_analyser.schema_readers.{module_name}"
        )

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        DataSubjectAnalyser accepts either standard_input OR source_code schema.
        Each is a valid alternative input. Multiple messages of the same schema are
        supported (fan-in).
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
            [InputRequirement("source_code", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("data_subject_indicator", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to identify data subjects using dynamic reader/handler dispatch.

        Supports same-schema fan-in: multiple messages of the same schema type are
        processed and their findings aggregated. Each finding retains its original
        metadata for tracing.

        Args:
            inputs: List of input messages (same schema, fan-in supported).
            output_schema: Expected output schema.

        Returns:
            Output message with findings from all inputs combined.

        """
        logger.info("Starting data subject analysis")

        input_schema = inputs[0].schema
        logger.debug(
            f"Processing {len(inputs)} message(s) with schema: {input_schema.name}"
        )

        # Load reader and handler once (same schema for all messages)
        reader = self._load_reader_module(input_schema)
        handler = reader.create_handler(self._config)

        # Process all input messages and aggregate findings (fan-in)
        indicators: list[DataSubjectIndicatorModel] = []
        for message in inputs:
            input_data = reader.read(message.content)
            message_indicators = handler.analyse(input_data)
            indicators.extend(message_indicators)

        # Build and return output message
        return self._result_builder.build_output_message(indicators, output_schema)

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
