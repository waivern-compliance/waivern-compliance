"""Personal data analysis analyser for GDPR compliance."""

import logging
from pprint import pformat
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import LLMValidationRunner, PatternMatchingRunner
from wct.message import Message
from wct.schemas import (
    PersonalDataFindingSchema,
    Schema,
    SourceCodeSchema,
    StandardInputSchema,
)

from .llm_validation_strategy import personal_data_validation_strategy
from .pattern_matcher import personal_data_pattern_matcher
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler

# from .types import PersonalDataFinding  # Only needed for LLM validation strategy

logger = logging.getLogger(__name__)

SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
    SourceCodeSchema(),
]

SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    PersonalDataFindingSchema(),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]

DEFAULT_MAXIMUM_EVIDENCE_COUNT = 3


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in various content formats, including source code and structured data.
    It supports LLM-based validation to filter false positives.
    """

    def __init__(
        self,
        ruleset_name: str = "personal_data",
        evidence_context_size: str = "small",
        maximum_evidence_count: int = DEFAULT_MAXIMUM_EVIDENCE_COUNT,
        enable_llm_validation: bool = True,
        llm_batch_size: int = 10,
        llm_validation_mode: str = "standard",
        pattern_runner: PatternMatchingRunner | None = None,
        llm_runner: LLMValidationRunner | None = None,
    ):
        """Initialise the analyser with specified configuration and runners.

        Args:
            ruleset_name: Name of the ruleset to use for analysis
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            maximum_evidence_count: Maximum number of evidence snippets to collect per finding
            enable_llm_validation: Whether to use LLM for false positive detection (default: True)
            llm_batch_size: Number of findings to validate in each LLM batch (default: 10)
            llm_validation_mode: LLM validation mode ('standard' or 'conservative', default: 'standard')
            pattern_runner: Pattern matching runner (optional, will create default if None)
            llm_runner: LLM validation runner (optional, will create default if None)
        """
        super().__init__()  # Call Analyser.__init__ directly

        # Store configuration
        self.config = {
            "ruleset_name": ruleset_name,
            "evidence_context_size": evidence_context_size,
            "maximum_evidence_count": maximum_evidence_count,
            "enable_llm_validation": enable_llm_validation,
            "llm_batch_size": llm_batch_size,
            "llm_validation_mode": llm_validation_mode,
            "max_evidence": maximum_evidence_count,  # Alias for runner compatibility
            "context_size": evidence_context_size,  # Alias for runner compatibility
        }

        # Initialise runners with personal data specific strategies
        self.pattern_runner = pattern_runner or PatternMatchingRunner(
            pattern_matcher=personal_data_pattern_matcher
        )
        self.llm_runner = llm_runner or LLMValidationRunner(
            validation_strategy=personal_data_validation_strategy,
            enable_llm_validation=enable_llm_validation,
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "personal_data_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        ruleset_name = properties.get("ruleset", "personal_data")
        evidence_context_size = properties.get("evidence_context_size", "small")
        maximum_evidence_count = properties.get(
            "maximum_evidence_count", DEFAULT_MAXIMUM_EVIDENCE_COUNT
        )
        enable_llm_validation = properties.get("enable_llm_validation", True)
        llm_batch_size = properties.get("llm_batch_size", 50)
        llm_validation_mode = properties.get("llm_validation_mode", "standard")

        return cls(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            maximum_evidence_count=maximum_evidence_count,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            llm_validation_mode=llm_validation_mode,
        )

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process data to find personal data patterns using runners."""
        Analyser.validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content

        # Process content based on input schema format using runners
        if input_schema.name == "source_code":
            # Handle source code format - delegate completely to handler
            # TODO: Create a SourceCodePatternRunner in the future for consistency
            raw_findings_list = SourceCodeSchemaInputHandler().analyse_source_code_data(
                data
            )
            # Convert to list of dicts for compatibility with runners
            findings = []
            for finding_obj in raw_findings_list:
                finding_dict = {
                    "type": finding_obj.type,
                    "risk_level": finding_obj.risk_level,
                    "special_category": finding_obj.special_category,
                    "matched_pattern": finding_obj.matched_pattern,
                    "evidence": finding_obj.evidence,
                    "metadata": finding_obj.metadata,
                }
                findings.append(finding_dict)
        else:
            # Process standard_input schema using pattern runner
            findings = self._process_standard_input_with_runners(data)

        # Apply LLM validation using LLM runner
        validated_findings = self.llm_runner.run_analysis(findings, {}, self.config)

        # Create result data with validated findings
        result_data: dict[str, Any] = {
            "findings": validated_findings,
            "summary": {
                "total_findings": len(validated_findings),
                "high_risk_count": len(
                    [f for f in validated_findings if f.get("risk_level") == "high"]
                ),
                "special_category_count": len(
                    [f for f in validated_findings if f.get("special_category") == "Y"]
                ),
            },
        }

        # Add validation statistics if LLM validation was used
        if self.config["enable_llm_validation"] and len(findings) > 0:
            original_count = len(findings)
            validated_count = len(validated_findings)
            false_positives_removed = original_count - validated_count

            result_data["validation_summary"] = {
                "llm_validation_enabled": True,
                "original_findings_count": original_count,
                "validated_findings_count": validated_count,
                "false_positives_removed": false_positives_removed,
                "validation_mode": self.config["llm_validation_mode"],
            }

            logger.info(
                f"LLM validation completed: {original_count} → {validated_count} findings "
                f"({false_positives_removed} false positives removed)"
            )

        output_message = Message(
            id="Personal data analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(findings)}"
        )

        # Return new Message with analysis results
        return output_message

    def _process_standard_input_with_runners(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Process standard_input schema data using runners.

        Args:
            data: Input data in standard_input schema format

        Returns:
            List of findings from pattern matching
        """
        findings = []

        if "data" in data and isinstance(data["data"], list):
            # Process each data item in the array using the pattern runner
            for item in data["data"]:
                content = item.get("content", "")
                item_metadata = item.get("metadata", {})

                # Use pattern runner for analysis
                item_findings = self.pattern_runner.run_analysis(
                    content, item_metadata, self.config
                )
                findings.extend(item_findings)
        else:
            # Handle direct content format (fallback)
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            findings = self.pattern_runner.run_analysis(content, metadata, self.config)

        return findings
