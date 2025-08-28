"""Personal data analysis analyser."""

import logging
from pprint import pformat
from typing import Any, Self, override

from wct.analysers.base import Analyser
from wct.analysers.utilities import LLMServiceManager
from wct.message import Message
from wct.schemas import (
    PersonalDataFindingSchema,
    Schema,
    StandardInputDataModel,
    StandardInputSchema,
)

from .llm_validation_strategy import personal_data_validation_strategy
from .pattern_matcher import PersonalDataPatternMatcher
from .types import PersonalDataAnalyserConfig, PersonalDataFindingModel

logger = logging.getLogger(__name__)

# Schema constants
_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    PersonalDataFindingSchema(),
]


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in structured data content. It supports LLM-based validation to filter
    false positives.
    """

    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        pattern_matcher: PersonalDataPatternMatcher,
        llm_service_manager: LLMServiceManager,
    ) -> None:
        """Initialise the analyser with configuration and utilities.

        Args:
            config: Strongly typed configuration
            pattern_matcher: Pattern matcher for personal data detection
            llm_service_manager: LLM service manager for validation

        """
        self._config = config
        self.pattern_matcher = pattern_matcher
        self.llm_service_manager = llm_service_manager

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "personal_data_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties with self-configuring runners."""
        try:
            # Validate and parse properties using strong typing
            config = PersonalDataAnalyserConfig.from_properties(properties)

            # Create utilities with their specific configurations
            pattern_matcher = PersonalDataPatternMatcher(config.pattern_matching)
            llm_service_manager = LLMServiceManager(
                config.llm_validation.enable_llm_validation
            )

            return cls(
                config=config,
                pattern_matcher=pattern_matcher,
                llm_service_manager=llm_service_manager,
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
        Analyser.validate_input_message(message, input_schema)

        # Extract and validate data using Pydantic.model_validate
        typed_data = StandardInputDataModel.model_validate(message.content)

        # Process each data item using the pattern matcher
        findings: list[PersonalDataFindingModel] = []
        for data_item in typed_data.data:
            content = data_item.content
            item_metadata = data_item.metadata

            item_findings = self.pattern_matcher.find_patterns(content, item_metadata)
            findings.extend(item_findings)

        # Run LLM validation if enabled
        validated_findings = self._validate_findings_with_llm(findings)

        # Create and validate output message
        return self._create_output_message(findings, validated_findings, output_schema)

    def _create_output_message(
        self,
        original_findings: list[PersonalDataFindingModel],
        validated_findings: list[PersonalDataFindingModel],
        output_schema: Schema,
    ) -> Message:
        """Create and validate output message.

        Args:
            original_findings: Original findings before LLM validation
            validated_findings: Findings after LLM validation
            output_schema: Schema for output validation

        Returns:
            Validated output message

        """
        # Convert models to dicts for final output
        validated_findings_dicts = [
            finding.model_dump(mode="json") for finding in validated_findings
        ]

        result_data: dict[str, Any] = {
            "findings": validated_findings_dicts,
            "summary": self._build_findings_summary(validated_findings),
        }

        if (
            self._config.llm_validation.enable_llm_validation
            and len(original_findings) > 0
        ):
            result_data["validation_summary"] = self._build_validation_summary(
                original_findings, validated_findings
            )

        output_message = Message(
            id="Personal_data_analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.info(
            f"PersonalDataAnalyser processed with {len(result_data['findings'])} findings"
        )

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message

    def _validate_findings_with_llm(
        self, findings: list[PersonalDataFindingModel]
    ) -> list[PersonalDataFindingModel]:
        """Validate findings using LLM if enabled and available.

        Args:
            findings: List of findings to validate

        Returns:
            List of validated findings (filtered/modified by LLM validation)

        """
        if not self._config.llm_validation.enable_llm_validation:
            return findings

        if not findings:
            return findings

        if self.llm_service_manager.llm_service is None:
            logger.warning("LLM service not available, skipping validation")
            return findings

        try:
            logger.info(f"Starting LLM validation of {len(findings)} findings")

            llm_service = self.llm_service_manager.llm_service
            validated_findings, validation_succeeded = (
                personal_data_validation_strategy(
                    findings, self._config.llm_validation, llm_service
                )
            )

            if validation_succeeded:
                logger.info(
                    f"LLM validation completed: {len(findings)} → {len(validated_findings)} findings"
                )
            else:
                logger.warning("LLM validation failed, using original findings")

            return validated_findings

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning unvalidated findings due to LLM validation error")
            return findings

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
            "high_risk_count": len([f for f in findings if f.risk_level == "high"]),
            "special_category_count": len(
                [f for f in findings if f.special_category is True]
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
            "validation_mode": self._config.llm_validation.llm_validation_mode,
        }
