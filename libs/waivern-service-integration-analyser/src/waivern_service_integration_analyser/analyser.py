"""Service integration analyser."""

import importlib
import logging
from typing import override

from waivern_analysers_shared import SchemaReader
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_rulesets.service_integrations import ServiceIntegrationRule
from waivern_source_code_analyser.schemas.source_code import SourceCodeDataModel

from .result_builder import ServiceIntegrationResultBuilder
from .schemas.types import ServiceIntegrationIndicatorModel
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import ServiceIntegrationAnalyserConfig

logger = logging.getLogger(__name__)


class ServiceIntegrationAnalyser(Analyser):
    """Analyser for detecting third-party service integrations in source code.

    Uses predefined rulesets to identify service integration patterns and
    assign service_category and purpose_category to each match. No LLM
    is required — detection is fully deterministic.
    """

    def __init__(self, config: ServiceIntegrationAnalyserConfig) -> None:
        """Initialise the analyser with configuration.

        Args:
            config: Validated configuration object.

        """
        self._config = config
        rules = RulesetManager.get_rules(
            config.pattern_matching.ruleset, ServiceIntegrationRule
        )
        self._handler = SourceCodeSchemaInputHandler(
            rules=rules,
            context_window=config.source_code_context_window,
        )
        self._result_builder = ServiceIntegrationResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "service_integration"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("source_code", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this analyser can produce."""
        return [Schema("service_integration_indicator", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process source code to find service integration patterns.

        Orchestrates the analysis flow:
        1. Read each input message via schema reader
        2. Analyse each source code model for patterns
        3. Build and return the output message

        Args:
            inputs: List of input messages (source_code/1.0.0, fan-in supported).
            output_schema: Expected output schema.

        Returns:
            Output message with service integration findings.

        """
        findings: list[ServiceIntegrationIndicatorModel] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            source_data = reader.read(message.content)
            findings.extend(self._handler.analyse(source_data))

        return self._result_builder.build_output_message(findings, output_schema)

    def _load_reader(self, schema: Schema) -> SchemaReader[SourceCodeDataModel]:
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
            f"waivern_service_integration_analyser.schema_readers.{module_name}"
        )
