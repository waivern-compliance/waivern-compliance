"""Personal data analysis analyser."""

import logging
from pprint import pformat
from typing import Any

from pydantic import BaseModel
from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import (
    LLMAnalysisRunner,
    PatternMatchingAnalysisRunner,
)
from wct.message import Message
from wct.schemas import (
    PersonalDataFindingSchema,
    Schema,
    StandardInputDataModel,
    StandardInputSchema,
)

from .config import PersonalDataAnalyserProperties
from .llm_validation_strategy import personal_data_validation_strategy
from .pattern_matcher import personal_data_pattern_matcher
from .types import PersonalDataFindingModel

logger = logging.getLogger(__name__)

# Schema constants
_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    PersonalDataFindingSchema(),
]

# Risk level constants
_HIGH_RISK_LEVEL = "high"
_SPECIAL_CATEGORY_YES = "Y"

# Message constants
_OUTPUT_MESSAGE_ID = "Personal data analysis"

# Analyser identification
_ANALYSER_NAME = "personal_data_analyser"


class _EmptyMetadata(BaseModel):
    """Empty metadata model for LLM runner when no metadata is needed."""

    pass


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in structured data content. It supports LLM-based validation to filter
    false positives.
    """

    def __init__(
        self,
        config: PersonalDataAnalyserProperties,
        pattern_runner: PatternMatchingAnalysisRunner[PersonalDataFindingModel],
        llm_runner: LLMAnalysisRunner[PersonalDataFindingModel],
    ) -> None:
        """Initialise the analyser with configuration and pre-configured runners.

        Args:
            config: Strongly typed configuration
            pattern_runner: Pre-configured pattern matching runner
            llm_runner: Pre-configured LLM validation runner

        """
        self.config = config
        self.pattern_runner = pattern_runner
        self.llm_runner = llm_runner

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return _ANALYSER_NAME

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties with self-configuring runners."""
        try:
            # Validate and parse properties using strong typing
            config = PersonalDataAnalyserProperties.from_properties(properties)

            # Create runners with their specific configurations
            pattern_runner = PatternMatchingAnalysisRunner(
                pattern_matcher=personal_data_pattern_matcher
            )

            llm_runner = LLMAnalysisRunner(
                validation_strategy=personal_data_validation_strategy,
                enable_llm_validation=config.llm_validation.enable_llm_validation,
            )

            return cls(
                config=config, pattern_runner=pattern_runner, llm_runner=llm_runner
            )
        except Exception as e:
            logger.error(f"Failed to create PersonalDataAnalyser from properties: {e}")
            logger.debug(f"Properties provided: {properties}")
            raise ValueError(
                f"Invalid configuration for PersonalDataAnalyser: {e}"
            ) from e

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
        """Process data to find personal data patterns using runners."""
        Analyser._validate_input_message(message, input_schema)

        # Extract and validate data using Pydantic.model_validate
        typed_data = StandardInputDataModel.model_validate(message.content)

        # Process each data item using the pattern runner
        findings: list[PersonalDataFindingModel] = []
        for data_item in typed_data.data:
            content = data_item.content

            # Pass strongly typed Pydantic metadata model directly
            item_metadata = data_item.metadata

            item_findings = self.pattern_runner.run_analysis(
                content, item_metadata, self.config.pattern_matching
            )
            findings.extend(item_findings)

        # Run LLM validation if enabled (using minimal metadata model)
        empty_metadata = _EmptyMetadata()
        validated_findings = self.llm_runner.run_analysis(
            findings, empty_metadata, self.config.llm_validation
        )

        # Build final result data
        result_data = self._build_result_data(findings, validated_findings)

        # Create and validate output message in one step
        output_message = Message(
            id=_OUTPUT_MESSAGE_ID,
            content=result_data,
            schema=output_schema,
        ).validate()

        logger.info(
            f"PersonalDataAnalyser processed with {len(result_data['findings'])} findings"
        )

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message

    def _build_result_data(
        self,
        original_findings: list[PersonalDataFindingModel],
        validated_findings: list[PersonalDataFindingModel],
    ) -> dict[str, Any]:
        """Build the final result data structure.

        Args:
            original_findings: Original findings before LLM validation
            validated_findings: Findings after LLM validation

        Returns:
            Complete result data dictionary

        """
        # Convert models to dicts for final output
        validated_findings_dicts = [
            finding.model_dump() for finding in validated_findings
        ]

        result_data: dict[str, Any] = {
            "findings": validated_findings_dicts,
            "summary": self._build_findings_summary(validated_findings),
        }

        if (
            self.config.llm_validation.enable_llm_validation
            and len(original_findings) > 0
        ):
            result_data["validation_summary"] = self._build_validation_summary(
                original_findings, validated_findings
            )

        return result_data

    def _build_findings_summary(
        self, findings: list[PersonalDataFindingModel]
    ) -> dict[str, Any]:
        """Build summary statistics for findings.

        Args:
            findings: List of validated findings

        Returns:
            Summary statistics dictionary

        """
        return {
            "total_findings": len(findings),
            "high_risk_count": len(
                [f for f in findings if f.risk_level == _HIGH_RISK_LEVEL]
            ),
            "special_category_count": len(
                [f for f in findings if f.special_category == _SPECIAL_CATEGORY_YES]
            ),
        }

    def _build_validation_summary(
        self,
        original_findings: list[PersonalDataFindingModel],
        validated_findings: list[PersonalDataFindingModel],
    ) -> dict[str, Any]:
        """Build LLM validation summary statistics.

        Args:
            original_findings: Original findings before validation
            validated_findings: Findings after validation

        Returns:
            Validation summary dictionary

        """
        original_count = len(original_findings)
        validated_count = len(validated_findings)
        false_positives_removed = original_count - validated_count

        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings "
            f"({false_positives_removed} false positives removed)"
        )

        return {
            "llm_validation_enabled": True,
            "original_findings_count": original_count,
            "validated_findings_count": validated_count,
            "false_positives_removed": false_positives_removed,
            "validation_mode": self.config.llm_validation.llm_validation_mode,
        }
