"""Source code schema input handler for processing purpose detection in source code analysis results."""

from typing import Any

from pydantic import BaseModel

from wct.rulesets import RulesetLoader
from wct.rulesets.types import Rule
from wct.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)


class SourceCodeFileMetadata(BaseModel):
    """Metadata for a source code file being analyzed."""

    source: str
    file_path: str
    language: str
    analysis_type: str


class SourceCodeSchemaInputHandler:
    """Handler for processing source code analysis schema input to detect processing purpose patterns.

    This handler is responsible for all source code analysis logic including loading
    the appropriate rulesets for processing purpose detection in source code.
    """

    # Private constants for configuration values
    _RULESET_NAME = "processing_purposes"
    _DEFAULT_PURPOSE_CATEGORY = "OPERATIONAL"
    _SOURCE_TYPE = "source_code"
    _LINE_PREFIX = "Line"
    _CODE_PREFIX = "Code:"

    # Analysis pattern types
    _ANALYSIS_TYPE_SOURCE_CODE = "source_code_pattern_matching_analysis"

    def __init__(self) -> None:
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load processing purposes patterns (includes merged third-party services)
        self.processing_purpose_patterns = RulesetLoader.load_ruleset(
            self._RULESET_NAME
        )

    def analyse_source_code_data(
        self, data: SourceCodeDataModel
    ) -> list[dict[str, Any]]:
        """Analyse source code analysis data for processing purpose patterns.

        This method examines source code analysis results to identify patterns that
        indicate data processing purposes, business logic, and service integrations.

        Args:
            data: Pydantic validated source code analysis data from SourceCodeConnector

        Returns:
            List of processing purpose findings from source code analysis

        """
        findings: list[dict[str, Any]] = []

        # Analyse each file in the source code analysis
        for file_data in data.data:
            file_findings = self._analyse_single_file(file_data)
            findings.extend(file_findings)

        return findings

    def _analyse_single_file(
        self, file_data: SourceCodeFileDataModel
    ) -> list[dict[str, Any]]:
        """Analyse a single source code file and return all processing purpose findings.

        Args:
            file_data: Typed source code file data to analyse

        Returns:
            List of processing purpose findings from this file

        """
        findings: list[dict[str, Any]] = []

        # Create base metadata for this file
        file_metadata = self._create_base_file_metadata(
            file_data.file_path, file_data.language
        )

        # Analyse raw content for processing purpose patterns
        processing_purpose_findings = self._analyse_raw_content_processing_purposes(
            file_data.raw_content, file_metadata
        )
        findings.extend(processing_purpose_findings)

        return findings

    def _create_base_file_metadata(
        self, file_path: str, language: str
    ) -> SourceCodeFileMetadata:
        """Create base metadata for a source code file.

        Args:
            file_path: Path to the source code file
            language: Programming language of the file

        Returns:
            SourceCodeFileMetadata with base information

        """
        return SourceCodeFileMetadata(
            source=self._SOURCE_TYPE,
            file_path=file_path,
            language=language,
            analysis_type=self._ANALYSIS_TYPE_SOURCE_CODE,
        )

    def _analyse_raw_content_processing_purposes(
        self,
        raw_content: str,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[dict[str, Any]]:
        """Analyse raw content for processing purpose patterns using processing_purposes ruleset."""
        findings: list[dict[str, Any]] = []
        lines = raw_content.split("\n")

        # Use processing purpose patterns from ruleset
        for rule in self.processing_purpose_patterns:
            rule_findings = self._analyse_rule_against_lines(rule, lines, file_metadata)
            findings.extend(rule_findings)

        return findings

    def _analyse_rule_against_lines(
        self,
        rule: Rule,
        lines: list[str],
        file_metadata: SourceCodeFileMetadata,
    ) -> list[dict[str, Any]]:
        """Analyse a single rule against all lines in the content.

        Args:
            rule: Processing purpose rule to match
            lines: Lines of source code to analyse
            file_metadata: Metadata about the source code file

        Returns:
            List of findings for this rule

        """
        findings: list[dict[str, Any]] = []

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()

            # Check if any patterns from this rule match the line
            for pattern in rule.patterns:
                if pattern.lower() in line_lower:
                    finding = self._create_processing_purpose_finding(
                        rule, pattern, line, line_num, file_metadata
                    )
                    findings.append(finding)

                    # Avoid duplicate matches for the same line/rule
                    break

        return findings

    def _create_processing_purpose_finding(
        self,
        rule: Rule,
        pattern: str,
        line: str,
        line_num: int,
        file_metadata: SourceCodeFileMetadata,
    ) -> dict[str, Any]:
        """Create a processing purpose finding dictionary.

        Args:
            rule: Processing purpose rule that matched
            pattern: Specific pattern that matched
            line: Source code line that matched
            line_num: Line number in the file
            file_metadata: Metadata about the source code file

        Returns:
            Processing purpose finding as dictionary

        """
        # Create processing purpose finding (no personal data context needed)
        evidence = [
            f"{self._LINE_PREFIX} {line_num}: {rule.description} - {pattern}",
            f"{self._CODE_PREFIX} {line.strip()}",
        ]

        # Create finding as dict[str, Any] for processing purposes
        return {
            "purpose": rule.name,
            "purpose_category": rule.metadata.get(
                "purpose_category", self._DEFAULT_PURPOSE_CATEGORY
            ),
            "risk_level": rule.risk_level,
            "compliance_relevance": rule.metadata.get("compliance_relevance", []),
            "matched_pattern": pattern,
            "evidence": evidence,
            "metadata": {
                "source": file_metadata.source,
                "file_path": file_metadata.file_path,
                "line_number": line_num,
                "language": file_metadata.language,
                "analysis_type": file_metadata.analysis_type,
                "service_category": rule.metadata.get("service_category"),
                "description": rule.description,
                "pattern": pattern,
            },
        }
