"""Data subject analysis analyser for GDPR Article 30(1)(c) compliance."""

import importlib
import logging
from types import ModuleType
from typing import override

from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.v2 import LLMService

from .result_builder import DataSubjectResultBuilder
from .schemas.types import DataSubjectIndicatorModel
from .types import DataSubjectAnalyserConfig
from .validation import create_validation_orchestrator

logger = logging.getLogger(__name__)


class DataSubjectAnalyser(Analyser):
    """Analyser for identifying data subjects for GDPR Article 30(1)(c) compliance.

    This analyser identifies and categorises data subjects from various data sources
    to help organisations maintain systematic records of data processing activities.
    """

    def __init__(
        self,
        config: DataSubjectAnalyserConfig,
        llm_service: LLMService | None = None,
    ) -> None:
        """Initialise the data subject analyser with configuration and dependencies.

        Args:
            config: Analyser configuration
            llm_service: Optional LLM service for validation (injected by DI)

        """
        self._config = config
        self._result_builder = DataSubjectResultBuilder(config)
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

        # Extract run_id from inputs (set by executor, used for cache scoping)
        run_id = inputs[0].run_id

        # Apply LLM validation if enabled
        validation_result: ValidationResult[DataSubjectIndicatorModel] | None = None
        final_findings = indicators
        if self._config.llm_validation.enable_llm_validation:
            validated_findings, _, validation_result = self._validate_findings(
                indicators, run_id=run_id
            )
            final_findings = validated_findings

        # Build and return output message
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
        findings: list[DataSubjectIndicatorModel],
        run_id: str | None = None,
    ) -> tuple[
        list[DataSubjectIndicatorModel],
        bool,
        ValidationResult[DataSubjectIndicatorModel] | None,
    ]:
        """Validate findings using ValidationOrchestrator.

        The orchestrator handles:
        - Grouping by subject_category (design-time decision)
        - Sampling and group-level decisions (when sampling enabled)

        Args:
            findings: List of findings to validate.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            Tuple of (validated findings, validation applied, validation result).

        """
        if not findings:
            return findings, False, None

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False, None

        if run_id is None:
            logger.warning("run_id is required for LLM validation, skipping")
            return findings, False, None

        try:
            # Create orchestrator and validate with marker callback
            # Marker is applied at strategy level to only mark actually-validated findings
            orchestrator = create_validation_orchestrator(
                self._config.llm_validation, self._llm_service
            )
            result = orchestrator.validate(
                findings,
                self._config.llm_validation,
                run_id,
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
        self, finding: DataSubjectIndicatorModel
    ) -> DataSubjectIndicatorModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark.

        Returns:
            New finding with validation marker in metadata context.

        """
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["data_subject_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding
