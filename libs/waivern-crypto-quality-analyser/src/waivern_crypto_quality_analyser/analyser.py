"""Cryptographic quality analyser."""

import importlib
import logging
from typing import override

from waivern_analysers_shared import SchemaReader
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from .pattern_matcher import CryptoQualityPatternMatcher
from .result_builder import CryptoQualityResultBuilder
from .schemas.types import CryptoQualityIndicatorModel
from .types import CryptoQualityAnalyserConfig

logger = logging.getLogger(__name__)


class CryptoQualityAnalyser(Analyser):
    """Analyser for detecting cryptographic algorithm quality in source code.

    Uses predefined rulesets to identify cryptographic patterns and assign
    quality ratings (strong, weak, deprecated) and polarity (positive,
    negative). No LLM is required — algorithm quality is deterministic.
    """

    def __init__(self, config: CryptoQualityAnalyserConfig) -> None:
        """Initialise the analyser with dependency injection.

        Args:
            config: Validated configuration object

        """
        self._config = config
        self._pattern_matcher = CryptoQualityPatternMatcher(config.pattern_matching)
        self._result_builder = CryptoQualityResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "crypto_quality_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        CryptoQualityAnalyser accepts either standard_input OR source_code schema.
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
        """Declare output schemas this analyser can produce."""
        return [Schema("crypto_quality_indicator", "1.0.0")]

    def _load_reader(
        self, schema: Schema
    ) -> SchemaReader[StandardInputDataModel[BaseMetadata]]:
        """Dynamically import reader module for the given input schema.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Input schema to load reader for.

        Returns:
            Reader module with typed read() function.

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version.

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(  # type: ignore[return-value]
            f"waivern_crypto_quality_analyser.schema_readers.{module_name}"
        )

    def _merge_input_data_items(
        self, inputs: list[Message]
    ) -> list[StandardInputDataItemModel[BaseMetadata]]:
        """Merge data items from multiple input messages (fan-in).

        Args:
            inputs: List of input messages with same schema.

        Returns:
            Flattened list of all data items from all inputs.

        """
        # Explicit annotation required: basedpyright strict mode infers [] as
        # list[Unknown], causing reportUnknownMemberType on .extend() calls.
        # Follow this pattern in all analyser methods that accumulate findings.
        all_data_items: list[StandardInputDataItemModel[BaseMetadata]] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            input_data = reader.read(message.content)
            all_data_items.extend(input_data.data)
        return all_data_items

    def _find_patterns_in_data_items(
        self, data_items: list[StandardInputDataItemModel[BaseMetadata]]
    ) -> list[CryptoQualityIndicatorModel]:
        """Run pattern matching on all data items.

        Args:
            data_items: List of data items to scan for patterns.

        Returns:
            List of crypto quality findings from all data items.

        """
        findings: list[CryptoQualityIndicatorModel] = []
        for item in data_items:
            item_findings = self._pattern_matcher.find_patterns(
                item.content, item.metadata
            )
            findings.extend(item_findings)
        return findings

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to find cryptographic algorithm patterns.

        Supports same-schema fan-in: multiple standard_input messages are merged
        before processing. Each data item retains its original metadata for tracing.

        Args:
            inputs: List of input messages (same schema, fan-in supported).
            output_schema: Expected output schema.

        Returns:
            Output message with crypto quality findings from all inputs combined.

        """
        data_items = self._merge_input_data_items(inputs)
        findings = self._find_patterns_in_data_items(data_items)
        return self._result_builder.build_output_message(findings, output_schema)
