"""Personal data analysis analyser."""

import logging
from dataclasses import dataclass
from pprint import pformat
from typing import Any, cast

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import (
    LLMAnalysisRunner,
    LLMAnalysisRunnerConfig,
    PatternMatchingAnalysisRunner,
    PatternMatchingRunnerConfig,
)
from wct.message import Message
from wct.schemas import (
    PersonalDataFindingSchema,
    Schema,
    SourceCodeDataModel,
    SourceCodeSchema,
    StandardInputData,
    StandardInputSchema,
    parse_data_model,
)

from .llm_validation_strategy import personal_data_validation_strategy
from .pattern_matcher import personal_data_pattern_matcher
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import PersonalDataFinding

logger = logging.getLogger(__name__)

# Schema constants
_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
    SourceCodeSchema(),
]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    PersonalDataFindingSchema(),
]

# Configuration constants
_DEFAULT_MAXIMUM_EVIDENCE_COUNT = 3
_DEFAULT_RULESET_NAME = "personal_data"
_DEFAULT_EVIDENCE_CONTEXT_SIZE = "small"
_DEFAULT_LLM_BATCH_SIZE = 50
_DEFAULT_LLM_VALIDATION_MODE = "standard"

# Schema names
_SOURCE_CODE_SCHEMA_NAME = "source_code"

# Risk level constants
_HIGH_RISK_LEVEL = "high"
_SPECIAL_CATEGORY_YES = "Y"

# Message constants
_OUTPUT_MESSAGE_ID = "Personal data analysis"

# Analyser identification
_ANALYSER_NAME = "personal_data_analyser"


@dataclass
class PersonalDataAnalyserConfig:
    """Configuration for PersonalDataAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    """

    ruleset_name: str = _DEFAULT_RULESET_NAME
    evidence_context_size: str = _DEFAULT_EVIDENCE_CONTEXT_SIZE
    maximum_evidence_count: int = _DEFAULT_MAXIMUM_EVIDENCE_COUNT
    enable_llm_validation: bool = True
    llm_batch_size: int = 10
    llm_validation_mode: str = _DEFAULT_LLM_VALIDATION_MODE


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in various content formats, including source code and structured data.
    It supports LLM-based validation to filter false positives.
    """

    def __init__(
        self,
        config: PersonalDataAnalyserConfig | None = None,
        pattern_runner: PatternMatchingAnalysisRunner[PersonalDataFinding]
        | None = None,
        llm_runner: LLMAnalysisRunner[PersonalDataFinding] | None = None,
    ) -> None:
        """Initialise the analyser with specified configuration and runners.

        Args:
            config: Configuration object with analysis settings (uses defaults if None)
            pattern_runner: Pattern matching runner (optional, will create default if None)
            llm_runner: LLM validation runner (optional, will create default if None)

        """
        # Store strongly-typed configuration
        self.config: PersonalDataAnalyserConfig = config or PersonalDataAnalyserConfig()

        # Initialise runners with personal data specific strategies
        self.pattern_runner = pattern_runner or PatternMatchingAnalysisRunner[
            PersonalDataFinding
        ](pattern_matcher=personal_data_pattern_matcher)

        self.llm_runner = llm_runner or LLMAnalysisRunner[PersonalDataFinding](
            validation_strategy=personal_data_validation_strategy,
            enable_llm_validation=self.config.enable_llm_validation,
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return _ANALYSER_NAME

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        ruleset_name = properties.get("ruleset", _DEFAULT_RULESET_NAME)
        evidence_context_size = properties.get(
            "evidence_context_size", _DEFAULT_EVIDENCE_CONTEXT_SIZE
        )
        maximum_evidence_count = properties.get(
            "maximum_evidence_count", _DEFAULT_MAXIMUM_EVIDENCE_COUNT
        )
        enable_llm_validation = properties.get("enable_llm_validation", True)
        llm_batch_size = properties.get("llm_batch_size", _DEFAULT_LLM_BATCH_SIZE)
        llm_validation_mode = properties.get(
            "llm_validation_mode", _DEFAULT_LLM_VALIDATION_MODE
        )

        config = PersonalDataAnalyserConfig(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            maximum_evidence_count=maximum_evidence_count,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            llm_validation_mode=llm_validation_mode,
        )

        return cls(config=config)

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

        # Data model validation at entry point - proper runtime validation
        if input_schema.name == _SOURCE_CODE_SCHEMA_NAME:
            # Ensure JSON schema validation has passed before data model validation
            if not message.schema_validated:
                message.validate()
            # Parse dictionary content into strongly typed data model
            typed_data = parse_data_model(message.content, SourceCodeDataModel)
            findings = self._process_source_code_findings(typed_data)
        else:
            # Type narrowing: we know this is StandardInputData structure
            typed_data = cast(StandardInputData, message.content)
            findings = self._process_standard_input_with_runners(typed_data)

        validated_findings = self.llm_runner.run_analysis(
            findings, {}, self._get_llm_config()
        )
        result_data = self._build_result_data(findings, validated_findings)

        output_message = Message(
            id=_OUTPUT_MESSAGE_ID,
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"PersonalDataAnalyser processed with {len(result_data['findings'])} findings"
        )

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message

    def _process_standard_input_with_runners(
        self, data: StandardInputData
    ) -> list[PersonalDataFinding]:
        """Process standard_input schema data using runners.

        Args:
            data: Input data in StandardInputData format

        Returns:
            List of typed PersonalDataFinding objects

        """
        findings: list[PersonalDataFinding] = []

        # Process each data item in the array using the pattern runner
        for data_item in data["data"]:
            # Get content and metadata (types guaranteed by StandardInputDataItem)
            content = data_item["content"]
            item_metadata = cast(dict[str, Any], data_item["metadata"])

            # Use pattern runner for analysis - returns PersonalDataFinding objects
            item_findings = self.pattern_runner.run_analysis(
                content, item_metadata, self._get_pattern_matching_config()
            )
            findings.extend(item_findings)

        return findings

    def _process_source_code_findings(
        self, data: SourceCodeDataModel
    ) -> list[PersonalDataFinding]:
        """Process source code data and return typed findings.

        Args:
            data: Pydantic validated source code data to process

        Returns:
            List of typed PersonalDataFinding objects

        """
        # Handle source code format - delegate completely to handler
        # TODO: Create a SourceCodePatternRunner in the future for consistency
        findings = SourceCodeSchemaInputHandler().analyse_source_code_data(data)

        return findings

    def _convert_findings_to_dicts(
        self, typed_findings: list[PersonalDataFinding]
    ) -> list[dict[str, Any]]:
        """Convert PersonalDataFinding objects to dictionary format.

        Args:
            typed_findings: List of PersonalDataFinding objects

        Returns:
            List of findings converted to dictionary format

        """
        findings: list[dict[str, Any]] = []
        for finding in typed_findings:
            finding_dict = {
                "type": finding.type,
                "risk_level": finding.risk_level,
                "special_category": finding.special_category,
                "matched_pattern": finding.matched_pattern,
                "evidence": finding.evidence,
                "metadata": finding.metadata,
            }
            findings.append(finding_dict)
        return findings

    def _get_pattern_matching_config(self) -> PatternMatchingRunnerConfig:
        """Extract pattern matching configuration from the full config."""
        return PatternMatchingRunnerConfig(
            ruleset_name=self.config.ruleset_name,
            max_evidence=self.config.maximum_evidence_count,
            maximum_evidence_count=self.config.maximum_evidence_count,
            context_size=self.config.evidence_context_size,
            evidence_context_size=self.config.evidence_context_size,
        )

    def _get_llm_config(self) -> LLMAnalysisRunnerConfig:
        """Extract LLM analysis configuration from the full config."""
        return LLMAnalysisRunnerConfig(
            enable_llm_validation=self.config.enable_llm_validation,
            llm_batch_size=self.config.llm_batch_size,
            llm_validation_mode=self.config.llm_validation_mode,
        )

    def _build_result_data(
        self,
        original_findings: list[PersonalDataFinding],
        validated_findings: list[PersonalDataFinding],
    ) -> dict[str, Any]:
        """Build the final result data structure.

        Args:
            original_findings: Original findings before LLM validation
            validated_findings: Findings after LLM validation

        Returns:
            Complete result data dictionary

        """
        # Convert typed findings to dicts for final output
        validated_findings_dicts = self._convert_findings_to_dicts(validated_findings)

        result_data: dict[str, Any] = {
            "findings": validated_findings_dicts,
            "summary": self._build_findings_summary(validated_findings),
        }

        if self.config.enable_llm_validation and len(original_findings) > 0:
            result_data["validation_summary"] = self._build_validation_summary(
                original_findings, validated_findings
            )

        return result_data

    def _build_findings_summary(
        self, findings: list[PersonalDataFinding]
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
        original_findings: list[PersonalDataFinding],
        validated_findings: list[PersonalDataFinding],
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
            "validation_mode": self.config.llm_validation_mode,
        }
