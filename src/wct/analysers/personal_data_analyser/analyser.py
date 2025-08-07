"""Personal data analysis analyser for GDPR compliance."""

import json
from pprint import pformat
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.llm_service import LLMServiceError, LLMServiceFactory
from wct.message import Message
from wct.prompts.personal_data_validation import (
    RecommendedAction,
    ValidationResult,
    extract_json_from_response,
    get_batch_validation_prompt,
)
from wct.rulesets import get_ruleset
from wct.schema import WctSchema

from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import PersonalDataFinding

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="text", type=dict[str, Any]),
    WctSchema(name="source_code", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="personal_data_analysis_findings", type=dict[str, Any]),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]

DEFAULT_MAXIMUM_EVIDENCE_COUNT = 3


class PersonalDataAnalyser(Analyser):
    """Analyser for analyzing personal data patterns for GDPR compliance."""

    def __init__(
        self,
        ruleset_name: str = "personal_data",
        evidence_context_size: str = "small",
        maximum_evidence_count: int = DEFAULT_MAXIMUM_EVIDENCE_COUNT,
        enable_llm_validation: bool = True,
        llm_batch_size: int = 10,
        llm_validation_mode: str = "standard",
    ):
        """Initialize the analyser with specified ruleset and LLM validation options.

        Args:
            ruleset_name: Name of the ruleset to use for analysis
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            maximum_evidence_count: Maximum number of evidence snippets to collect per finding
            enable_llm_validation: Whether to use LLM for false positive detection (default: True)
            llm_batch_size: Number of findings to validate in each LLM batch (default: 10)
            llm_validation_mode: LLM validation mode ('standard' or 'conservative', default: 'standard')
        """
        super().__init__()  # Initialize logger from base class
        self.ruleset_name = ruleset_name
        self.evidence_context_size = evidence_context_size
        self.maximum_evidence_count = maximum_evidence_count
        self.enable_llm_validation = enable_llm_validation
        self.llm_batch_size = llm_batch_size
        self.llm_validation_mode = llm_validation_mode
        self._patterns = None
        self._llm_service = None

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
        llm_batch_size = properties.get("llm_batch_size", 10)
        llm_validation_mode = properties.get("llm_validation_mode", "standard")

        return cls(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            maximum_evidence_count=maximum_evidence_count,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            llm_validation_mode=llm_validation_mode,
        )

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            self._patterns = get_ruleset(self.ruleset_name)
        return self._patterns

    @property
    def llm_service(self):
        """Get the LLM service, creating it if necessary."""
        if self._llm_service is None and self.enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_anthropic_service()
                self.logger.info("LLM service initialized for personal data validation")
            except LLMServiceError as e:
                self.logger.warning(
                    f"Failed to initialize LLM service: {e}. Continuing without LLM validation."
                )
                self.enable_llm_validation = False
        return self._llm_service

    def _get_context_size(self) -> int | None:
        """Get the context size in characters based on the configured level.

        Returns:
            Number of characters to include before and after each match,
            or None for full content (no truncation)
        """
        size_mapping = {"small": 50, "medium": 100, "large": 200, "full": None}
        return size_mapping.get(self.evidence_context_size.lower(), 50)

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[WctSchema[Any]]:
        """Return the input schemas supported by this analyser."""
        return SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[WctSchema[Any]]:
        """Return the output schemas supported by this analyser."""
        return SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Process data to find personal data patterns."""
        Analyser.validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content

        # Extract and process content based on input schema format
        # Personal data analysis requires granular tracking for compliance purposes
        # Note: data is always dict[str, Any] from message.content

        if input_schema.name == "source_code":
            # Handle source code format - delegate completely to handler
            findings = SourceCodeSchemaInputHandler().analyze_source_code_data(data)
        elif "data" in data and isinstance(data["data"], list):
            # DESIGN DECISION: Analyze each data array item independently
            #
            # For personal data compliance (GDPR, CCPA), we need granular tracking
            # of where specific personal data types are found. This enables:
            # - Precise data mapping for compliance documentation
            # - Granular consent management
            # - Targeted data deletion/modification
            # - Detailed audit trails for regulatory requirements
            #
            # Each item in the data array represents a distinct content piece
            # that should be analyzed and tracked separately for compliance.

            data_array = data["data"]
            all_findings = []

            for item in data_array:
                content = item.get("content", "")
                item_metadata = item.get("metadata", {})

                # Analyze each content piece independently for compliance tracking
                item_findings = self._analyze_content(content, item_metadata)
                all_findings.extend(item_findings)

            findings = all_findings
        else:
            # Handle direct content format (legacy or simplified input)
            content = data.get("content", "")
            direct_metadata = data.get("metadata", {})
            findings = self._analyze_content(content, direct_metadata)

        # Apply LLM validation to filter false positives
        validated_findings = self._validate_findings_with_llm(findings)

        # Create result data with validated findings
        result_data: dict[str, Any] = {
            "findings": [
                {
                    "type": finding.type,
                    "risk_level": finding.risk_level,
                    "special_category": finding.special_category,
                    "matched_pattern": finding.matched_pattern,
                    "evidence": finding.evidence,
                    "metadata": finding.metadata,
                }
                for finding in validated_findings
            ],
            "summary": {
                "total_findings": len(validated_findings),
                "high_risk_count": len(
                    [f for f in validated_findings if f.risk_level == "high"]
                ),
                "special_category_count": len(
                    [f for f in validated_findings if f.special_category == "Y"]
                ),
            },
        }

        # Add validation statistics if LLM validation was used
        if self.enable_llm_validation and len(findings) > 0:
            original_count = len(findings)
            validated_count = len(validated_findings)
            false_positives_removed = original_count - validated_count

            result_data["validation_summary"] = {
                "llm_validation_enabled": True,
                "original_findings_count": original_count,
                "validated_findings_count": validated_count,
                "false_positives_removed": false_positives_removed,
                "validation_mode": self.llm_validation_mode,
            }

            self.logger.info(
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

        self.logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(findings)}"
        )

        # Return new Message with analysis results
        return output_message

    def _analyze_content(
        self, content: str, metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze content for personal data patterns."""
        findings = []

        for category_name, category_data in self.patterns.items():
            for pattern in category_data["patterns"]:
                if pattern.lower() in content.lower():
                    # Extract evidence - find all occurrences of the pattern in the content
                    evidence_matches = self._extract_evidence(content, pattern)

                    # Pass metadata as-is since source is guaranteed by schema
                    finding_metadata = metadata.copy() if metadata else {}

                    finding = PersonalDataFinding(
                        type=category_name,
                        risk_level=category_data["risk_level"],
                        special_category=category_data["special_category"],
                        matched_pattern=pattern,
                        evidence=evidence_matches,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings

    def _extract_evidence(self, content: str, pattern: str) -> list[str]:
        """Extract evidence snippets where the pattern was found.

        Args:
            content: The full content to search in
            pattern: The pattern that was matched

        Returns:
            List of unique evidence snippets showing context around matches
        """
        evidence_set = set()  # Use set to avoid duplicates
        content_lower = content.lower()
        pattern_lower = pattern.lower()

        # Find all occurrences of the pattern
        start_pos = 0
        while True:
            match_pos = content_lower.find(pattern_lower, start_pos)
            if match_pos == -1:
                break

            # Extract context around the match (configurable characters before and after)
            context_size = self._get_context_size()

            if context_size is None:
                # 'full' option: include entire content without truncation
                evidence_snippet = content.strip()
            else:
                # Standard context window extraction
                context_start = max(0, match_pos - context_size)
                context_end = min(len(content), match_pos + len(pattern) + context_size)

                # Extract the evidence with context
                evidence_snippet = content[context_start:context_end].strip()

                # Add ellipsis if we truncated the context
                if context_start > 0:
                    evidence_snippet = "..." + evidence_snippet
                if context_end < len(content):
                    evidence_snippet = evidence_snippet + "..."

            # Add to set to automatically deduplicate
            evidence_set.add(evidence_snippet)

            # Move past this match to find the next occurrence
            start_pos = match_pos + 1

            # For 'full' context, only include one snippet since it contains everything
            # For other contexts, limit to maximum evidence snippets to avoid overwhelming output
            if context_size is None and len(evidence_set) >= 1:
                break
            elif (
                context_size is not None
                and len(evidence_set) >= self.maximum_evidence_count
            ):
                break

        # Convert set back to list and maintain consistent ordering
        return sorted(list(evidence_set))

    def _validate_findings_with_llm(
        self, findings: list[PersonalDataFinding]
    ) -> list[PersonalDataFinding]:
        """Validate findings using LLM to filter false positives.

        Args:
            findings: List of findings from pattern matching

        Returns:
            List of validated findings with false positives removed
        """
        if not self.enable_llm_validation or not findings:
            self.logger.debug("LLM validation disabled or no findings to validate")
            return findings

        if not self.llm_service:
            self.logger.warning("LLM service not available, skipping validation")
            return findings

        self.logger.info(f"Starting LLM validation of {len(findings)} findings")
        validated_findings = []

        # Process findings in batches for efficiency
        for i in range(0, len(findings), self.llm_batch_size):
            batch = findings[i : i + self.llm_batch_size]
            batch_results = self._validate_findings_batch(batch)
            validated_findings.extend(batch_results)

        self.logger.debug(
            f"LLM validation completed: {len(findings)} → {len(validated_findings)} findings"
        )
        return validated_findings

    def _validate_findings_batch(
        self, findings_batch: list[PersonalDataFinding]
    ) -> list[PersonalDataFinding]:
        """Validate a batch of findings using LLM.

        Args:
            findings_batch: Batch of findings to validate

        Returns:
            List of validated findings from this batch
        """
        try:
            # Check if LLM service is available
            if not self.llm_service:
                self.logger.warning("LLM service not available for batch validation")
                return findings_batch

            # Convert findings to format expected by validation prompt
            findings_for_prompt = []
            for finding in findings_batch:
                findings_for_prompt.append(
                    {
                        "type": finding.type,
                        "risk_level": finding.risk_level,
                        "special_category": finding.special_category,
                        "matched_pattern": finding.matched_pattern,
                        "evidence": finding.evidence,
                        "metadata": finding.metadata,
                    }
                )

            # Generate validation prompt
            prompt = get_batch_validation_prompt(findings_for_prompt)

            # Get LLM validation response
            self.logger.debug(f"Validating batch of {len(findings_batch)} findings")
            response = self.llm_service.analyze_text("", prompt)

            # Extract and parse JSON response
            clean_json = extract_json_from_response(response)
            validation_results = json.loads(clean_json)

            # Filter findings based on validation results
            validated_findings = []
            for i, result in enumerate(validation_results):
                if i >= len(findings_batch):
                    self.logger.warning(
                        f"Validation result index {i} exceeds batch size {len(findings_batch)}"
                    )
                    continue

                finding = findings_batch[i]
                validation_result = result.get("validation_result")
                confidence = result.get("confidence", 0.0)
                reasoning = result.get("reasoning", "No reasoning provided")
                action = result.get("recommended_action", "keep")

                # Log validation decision
                self.logger.debug(
                    f"Finding '{finding.type}' ({finding.matched_pattern}): "
                    f"{validation_result} (confidence: {confidence:.2f}) - {reasoning}"
                )

                # Keep findings that are validated as true positives
                if (
                    validation_result == ValidationResult.TRUE_POSITIVE
                    and action == RecommendedAction.KEEP
                ):
                    validated_findings.append(finding)
                elif validation_result == ValidationResult.FALSE_POSITIVE:
                    self.logger.info(
                        f"Removed false positive: {finding.type} - {finding.matched_pattern} "
                        f"(confidence: {confidence:.2f}) - {reasoning}"
                    )
                else:
                    # Handle edge cases - if uncertain, keep for safety
                    self.logger.warning(
                        f"Uncertain validation result for {finding.type}, keeping for safety: {reasoning}"
                    )
                    validated_findings.append(finding)

            return validated_findings

        except Exception as e:
            self.logger.error(f"LLM validation failed for batch: {e}")
            self.logger.warning(
                "Returning unvalidated findings due to LLM validation error"
            )
            return findings_batch
