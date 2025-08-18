"""Source code schema input handler for processing purpose detection in source code analysis results."""

from pydantic import BaseModel

from wct.rulesets import RulesetLoader
from wct.rulesets.types import Rule
from wct.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

from .types import ProcessingPurposeFindingMetadata, ProcessingPurposeFindingModel


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

    def __init__(self) -> None:
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load all three rulesets for comprehensive source code analysis
        self._processing_purposes_rules = RulesetLoader.load_ruleset(
            "processing_purposes"
        )
        self._service_integrations_rules = RulesetLoader.load_ruleset(
            "service_integrations"
        )
        self._data_collection_rules = RulesetLoader.load_ruleset(
            "data_collection_patterns"
        )

    def analyse_source_code_data(
        self, data: SourceCodeDataModel
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse source code analysis data for processing purpose patterns.

        This method examines source code analysis results to identify patterns that
        indicate data processing purposes, business logic, and service integrations.

        Args:
            data: Pydantic validated source code analysis data from SourceCodeConnector

        Returns:
            List of strongly typed processing purpose findings from source code analysis

        """
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse each file in the source code analysis
        for file_data in data.data:
            file_findings = self._analyse_single_file(file_data)
            findings.extend(file_findings)

        return findings

    def _analyse_single_file(
        self, file_data: SourceCodeFileDataModel
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse a single source code file and return all processing purpose findings.

        Args:
            file_data: Typed source code file data to analyse

        Returns:
            List of strongly typed processing purpose findings from this file

        """
        findings: list[ProcessingPurposeFindingModel] = []

        # Create base metadata for this file
        file_metadata = self._create_base_file_metadata(
            file_data.file_path, file_data.language
        )

        # Analyse raw content for processing purpose patterns
        processing_purpose_findings = self._analyse_raw_content_processing_purposes(
            file_data.raw_content, file_metadata
        )
        findings.extend(processing_purpose_findings)

        # Structured analysis with service_integrations
        service_integration_findings = self._analyse_structured_service_integrations(
            file_data, file_metadata
        )
        findings.extend(service_integration_findings)

        # Structured analysis with data_collection_patterns
        data_collection_findings = self._analyse_structured_data_collection(
            file_data, file_metadata
        )
        findings.extend(data_collection_findings)

        # Structured analysis with processing_purposes (secondary)
        structured_purpose_findings = self._analyse_structured_processing_purposes(
            file_data, file_metadata
        )
        findings.extend(structured_purpose_findings)

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
            source="source_code",
            file_path=file_path,
            language=language,
            analysis_type="source_code_pattern_matching_analysis",
        )

    def _analyse_raw_content_processing_purposes(
        self,
        raw_content: str,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse raw content for processing purpose patterns using processing_purposes ruleset."""
        findings: list[ProcessingPurposeFindingModel] = []
        lines = raw_content.split("\n")

        # Use processing purpose patterns from ruleset
        for rule in self._processing_purposes_rules:
            rule_findings = self._analyse_rule_against_lines(rule, lines, file_metadata)
            findings.extend(rule_findings)

        return findings

    def _analyse_rule_against_lines(
        self,
        rule: Rule,
        lines: list[str],
        file_metadata: SourceCodeFileMetadata,
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse a single rule against all lines in the content.

        Args:
            rule: Processing purpose rule to match
            lines: Lines of source code to analyse
            file_metadata: Metadata about the source code file

        Returns:
            List of strongly typed findings for this rule

        """
        findings: list[ProcessingPurposeFindingModel] = []

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
    ) -> ProcessingPurposeFindingModel:
        """Create a strongly typed processing purpose finding.

        Args:
            rule: Processing purpose rule that matched
            pattern: Specific pattern that matched
            line: Source code line that matched
            line_num: Line number in the file
            file_metadata: Metadata about the source code file

        Returns:
            Strongly typed ProcessingPurposeFindingModel

        """
        # Create processing purpose finding evidence
        evidence = [
            f"Line {line_num}: {rule.description} - {pattern}",
            f"Code: {line.strip()}",
        ]

        # Create extra metadata fields
        extra_metadata = {
            "file_path": file_metadata.file_path,
            "line_number": line_num,
            "language": file_metadata.language,
            "analysis_type": file_metadata.analysis_type,
            "service_category": rule.metadata.get("service_category"),
            "description": rule.description,
            "pattern": pattern,
        }

        # Create strongly typed finding using Pydantic model
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.metadata.get("purpose_category", ""),
            risk_level=rule.risk_level,
            compliance_relevance=rule.metadata.get("compliance_relevance", ["GDPR"])
            if isinstance(rule.metadata.get("compliance_relevance", ["GDPR"]), list)
            else ["GDPR"],
            matched_pattern=pattern,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
                **extra_metadata,
            ),
        )

    def _analyse_structured_service_integrations(
        self, file_data: SourceCodeFileDataModel, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse structured code elements for service integration patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse imports for service integrations
        for import_item in file_data.imports:
            findings.extend(
                self._check_patterns_against_text(
                    self._service_integrations_rules,
                    import_item.module,
                    f"Import: {import_item.module}",
                    file_metadata,
                    "import_analysis",
                )
            )

        # Analyse function names
        for function in file_data.functions:
            findings.extend(
                self._check_patterns_against_text(
                    self._service_integrations_rules,
                    function.name,
                    f"Function: {function.name}",
                    file_metadata,
                    "function_name_analysis",
                )
            )

        # Analyse class names
        for class_item in file_data.classes:
            findings.extend(
                self._check_patterns_against_text(
                    self._service_integrations_rules,
                    class_item.name,
                    f"Class: {class_item.name}",
                    file_metadata,
                    "class_name_analysis",
                )
            )

        return findings

    def _analyse_structured_data_collection(
        self, file_data: SourceCodeFileDataModel, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse structured code elements for data collection patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse function names for data collection patterns
        for function in file_data.functions:
            findings.extend(
                self._check_patterns_against_text(
                    self._data_collection_rules,
                    function.name,
                    f"Function: {function.name}",
                    file_metadata,
                    "data_collection_function_analysis",
                )
            )

        # Analyse raw content for SQL patterns (hybrid approach)
        findings.extend(
            self._analyse_sql_patterns_in_content(file_data.raw_content, file_metadata)
        )

        return findings

    def _analyse_structured_processing_purposes(
        self, file_data: SourceCodeFileDataModel, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse structured code elements for processing purpose patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse function names for business purposes
        for function in file_data.functions:
            findings.extend(
                self._check_patterns_against_text(
                    self._processing_purposes_rules,
                    function.name,
                    f"Function: {function.name}",
                    file_metadata,
                    "function_name_analysis",
                )
            )

        # Analyse class names for business purposes
        for class_item in file_data.classes:
            findings.extend(
                self._check_patterns_against_text(
                    self._processing_purposes_rules,
                    class_item.name,
                    f"Class: {class_item.name}",
                    file_metadata,
                    "class_name_analysis",
                )
            )

        return findings

    def _check_patterns_against_text(
        self,
        rules: tuple[Rule, ...],
        text: str,
        evidence_prefix: str,
        file_metadata: SourceCodeFileMetadata,
        analysis_type: str,
    ) -> list[ProcessingPurposeFindingModel]:
        """Check ruleset patterns against a text string."""
        findings: list[ProcessingPurposeFindingModel] = []
        text_lower = text.lower()

        for rule in rules:
            for pattern in rule.patterns:
                if pattern.lower() in text_lower:
                    finding = self._create_structured_finding(
                        rule,
                        pattern,
                        evidence_prefix,
                        file_metadata,
                        analysis_type,
                    )
                    findings.append(finding)
                    break  # Avoid duplicate matches for same rule

        return findings

    def _analyse_sql_patterns_in_content(
        self, raw_content: str, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse raw content for SQL patterns from data collection ruleset."""
        findings: list[ProcessingPurposeFindingModel] = []
        lines = raw_content.split("\n")

        # Only check SQL-related rules from data collection
        sql_rules = [
            rule
            for rule in self._data_collection_rules
            if "sql" in rule.name.lower() or "database" in rule.name.lower()
        ]

        for rule in sql_rules:
            rule_findings = self._analyse_rule_against_lines(rule, lines, file_metadata)
            findings.extend(rule_findings)

        return findings

    def _create_structured_finding(
        self,
        rule: Rule,
        pattern: str,
        evidence_prefix: str,
        file_metadata: SourceCodeFileMetadata,
        analysis_type: str,
    ) -> ProcessingPurposeFindingModel:
        """Create a structured analysis finding."""
        # Extract matched text from evidence prefix (e.g., "Function: getUserByEmail" -> "getUserByEmail")
        matched_text = evidence_prefix.split(": ")[-1]
        evidence = [
            f"{evidence_prefix}: {rule.description} - {pattern}",
            f"Matched: {matched_text}",
        ]

        extra_metadata = {
            "file_path": file_metadata.file_path,
            "language": file_metadata.language,
            "analysis_type": analysis_type,
            "service_category": rule.metadata.get("service_category"),
            "description": rule.description,
            "pattern": pattern,
        }

        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.metadata.get("purpose_category", ""),
            risk_level=rule.risk_level,
            compliance_relevance=rule.metadata.get("compliance_relevance", ["GDPR"])
            if isinstance(rule.metadata.get("compliance_relevance", ["GDPR"]), list)
            else ["GDPR"],
            matched_pattern=pattern,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
                **extra_metadata,
            ),
        )
