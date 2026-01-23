"""Processing purpose analysis analyser for compliance frameworks."""

import importlib
import logging
from types import ModuleType
from typing import override

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BaseLLMService
from waivern_source_code_analyser import SourceCodeDataModel

from .result_builder import ProcessingPurposeResultBuilder
from .schemas.types import ProcessingPurposeIndicatorModel
from .types import ProcessingPurposeAnalyserConfig
from .validation import create_validation_orchestrator

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
        return [Schema("processing_purpose_indicator", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to identify processing purposes.

        Supports same-schema fan-in: multiple messages of the same schema type are
        processed and their findings aggregated. Each finding retains its original
        metadata for tracing.

        Args:
            inputs: List of input messages (same schema, fan-in supported)
            output_schema: Expected output schema

        Returns:
            Output message with processing purpose findings from all inputs

        """
        logger.info("Starting processing purpose analysis")

        input_schema = inputs[0].schema
        logger.debug(
            f"Processing {len(inputs)} message(s) with schema: {input_schema.name}"
        )

        # Load reader and handler once (same schema for all messages)
        reader = self._load_reader_module(input_schema)
        handler = reader.create_handler(self._config)

        # Process all input messages and aggregate findings (fan-in)
        findings: list[ProcessingPurposeIndicatorModel] = []
        for message in inputs:
            input_data = reader.read(message.content)
            message_findings = handler.analyse(input_data)
            findings.extend(message_findings)

        # Apply LLM validation if enabled
        validation_result: ValidationResult[ProcessingPurposeIndicatorModel] | None = (
            None
        )
        final_findings = findings
        if self._config.llm_validation.enable_llm_validation:
            validated_findings, _, validation_result = self._validate_findings(
                findings, inputs
            )
            final_findings = validated_findings

        # Build output message
        return self._result_builder.build_output_message(
            final_findings,
            output_schema,
            validation_result,
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

    def _validate_findings(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        input_messages: list[Message],
    ) -> tuple[
        list[ProcessingPurposeIndicatorModel],
        bool,
        ValidationResult[ProcessingPurposeIndicatorModel] | None,
    ]:
        """Validate findings using ValidationOrchestrator.

        The orchestrator handles:
        - LLM strategy selection based on input schema (source_code vs standard_input)
        - Grouping by purpose (when sampling is enabled)
        - Sampling and group-level decisions

        Args:
            findings: List of findings to validate.
            input_messages: Input messages for context (fan-in supported).

        Returns:
            Tuple of (validated findings, validation applied, validation result).

        """
        if not findings:
            return findings, False, None

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False, None

        try:
            # Extract source contents from all messages if source_code schema (fan-in)
            source_contents: dict[str, str] | None = None
            input_schema = input_messages[0].schema
            if input_schema.name == "source_code":
                source_contents = {}
                for message in input_messages:
                    source_data = SourceCodeDataModel.model_validate(message.content)
                    for f in source_data.data:
                        source_contents[f.file_path] = f.raw_content

            # Create orchestrator and validate with marker callback
            # Marker is applied at strategy level to only mark actually-validated findings
            orchestrator = create_validation_orchestrator(
                self._config.llm_validation,
                input_schema.name,
                source_contents,
            )
            result = orchestrator.validate(
                findings,
                self._config.llm_validation,
                self._llm_service,
                marker=self._mark_finding_validated,
            )

            logger.info(
                f"Validation complete: {len(findings)} → {len(result.kept_findings)} findings "
                f"({len(result.removed_groups)} groups removed)"
            )

            return result.kept_findings, result.all_succeeded, result

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning original findings due to validation error")
            return findings, False, None

    def _mark_finding_validated(
        self, finding: ProcessingPurposeIndicatorModel
    ) -> ProcessingPurposeIndicatorModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark.

        Returns:
            New finding with validation marker in metadata context.

        """
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["processing_purpose_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding
