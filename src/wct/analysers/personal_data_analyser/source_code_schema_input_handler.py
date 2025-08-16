"""Source code schema input handler for personal data detection in source code analysis results."""

import re

from pydantic import BaseModel

from wct.rulesets import RulesetLoader
from wct.schemas import (
    SourceCodeClassModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFunctionModel,
)

from .types import PersonalDataFinding


class SourceCodeFileMetadata(BaseModel):
    """Metadata for a source code file being analyzed."""

    source: str
    file_path: str
    language: str
    analysis_type: str


class SourceCodeFindingMetadata(BaseModel):
    """Metadata for a personal data finding in source code."""

    source: str
    file_path: str
    language: str
    analysis_type: str
    line_number: int

    # Optional fields that can be present depending on the finding type
    collection_type: str | None = None
    field_name: str | None = None
    pattern_matched: str | None = None
    rule_name: str | None = None
    data_source: str | None = None
    function_name: str | None = None
    parameter_name: str | None = None
    analysis_pattern: str | None = None
    class_name: str | None = None
    property_name: str | None = None
    sql_fragment: str | None = None
    sql_type: str | None = None
    service_name: str | None = None
    service_category: str | None = None
    detected_context: str | None = None


class SourceCodeSchemaInputHandler:
    """Handler for processing source code analysis schema input to detect personal data patterns.

    This handler is responsible for all source code analysis logic including loading
    the appropriate rulesets for personal data detection in source code.
    """

    # Private constants for configuration values
    _RULESET_NAME = "personal_data"
    _DEFAULT_SPECIAL_CATEGORY = "N"
    _DEFAULT_RISK_LEVEL = "medium"
    _SQL_FRAGMENT_MAX_LENGTH = 200
    _SQL_EVIDENCE_DISPLAY_MAX_LENGTH = 100

    # Analysis pattern types
    _ANALYSIS_TYPE_SOURCE_CODE = "source_code_pattern_matching_analysis"
    _PATTERN_FUNCTION_NAME = "function_name"
    _PATTERN_PARAMETER_NAME = "parameter_name"
    _PATTERN_CLASS_NAME = "class_name"
    _PATTERN_PROPERTY_NAME = "property_name"
    _PATTERN_SQL_QUERY = "sql_query"
    _PATTERN_THIRD_PARTY = "third_party_integration"

    # Data type constants
    _TYPE_THIRD_PARTY_SHARING = "third_party_sharing"

    # Matched pattern prefixes
    _PREFIX_SOURCE_CODE_FIELD = "source_code_field"
    _PREFIX_SOURCE_CODE_FUNCTION = "source_code_function"
    _PREFIX_SOURCE_CODE_PARAMETER = "source_code_parameter"
    _PREFIX_SOURCE_CODE_CLASS = "source_code_class"
    _PREFIX_SOURCE_CODE_PROPERTY = "source_code_property"
    _PREFIX_SOURCE_CODE_SQL = "source_code_sql"
    _PREFIX_SOURCE_CODE_INTEGRATION = "source_code_integration"

    def __init__(self) -> None:
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load personal data patterns for field name classification
        self.personal_data_patterns = RulesetLoader.load_ruleset(self._RULESET_NAME)

        # Load data collection patterns for raw content analysis
        self.data_collection_patterns = RulesetLoader.load_ruleset(
            "data_collection_patterns"
        )

        # Load third-party service patterns for service detection
        self.third_party_service_patterns = RulesetLoader.load_ruleset(
            "third_party_services"
        )

    def analyse_source_code_data(
        self, data: SourceCodeDataModel
    ) -> list[PersonalDataFinding]:
        """Analyse source code analysis data for personal data collection patterns.

        This method examines source code analysis results to identify patterns that
        indicate personal data collection, processing, or storage.

        Args:
            data: Pydantic validated source code analysis data from SourceCodeConnector

        Returns:
            List of personal data findings from source code analysis

        """
        findings: list[PersonalDataFinding] = []

        # Analyse each file in the source code analysis
        for file_data in data.data:
            file_findings = self._analyse_single_file(file_data)
            findings.extend(file_findings)

        return findings

    def _analyse_single_file(
        self, file_data: SourceCodeFileDataModel
    ) -> list[PersonalDataFinding]:
        """Analyse a single source code file and return all personal data findings.

        Args:
            file_data: Typed source code file data to analyse

        Returns:
            List of personal data findings from this file

        """
        findings: list[PersonalDataFinding] = []

        # Create base metadata for this file
        file_metadata = self._create_base_file_metadata(
            file_data.file_path, file_data.language
        )

        # Analyse raw content for data collection patterns (NEW: pattern matching approach)
        raw_content_findings = self._analyse_raw_content_data_collection_patterns(
            file_data.raw_content, file_metadata
        )
        findings.extend(raw_content_findings)

        # Analyse function patterns for personal data handling (EXISTING: keep as-is)
        function_findings = self._analyse_function_patterns(
            file_data.functions, file_metadata
        )
        findings.extend(function_findings)

        # Analyse class patterns for personal data models (EXISTING: keep as-is)
        class_findings = self._analyse_class_patterns(file_data.classes, file_metadata)
        findings.extend(class_findings)

        # Analyse raw content for database/SQL patterns (NEW: pattern matching approach)
        sql_findings = self._analyse_raw_content_sql_patterns(
            file_data.raw_content, file_metadata
        )
        findings.extend(sql_findings)

        # Analyse raw content for third-party service patterns (NEW: pattern matching approach)
        third_party_findings = self._analyse_raw_content_third_party_patterns(
            file_data.raw_content, file_metadata
        )
        findings.extend(third_party_findings)

        return findings

    def _create_base_file_metadata(
        self, file_path: str, language: str
    ) -> SourceCodeFileMetadata:
        """Create base metadata for a source code file.

        Args:
            file_path: Path to the source code file
            language: Programming language of the file

        Returns:
            Strongly-typed metadata for the file

        """
        return SourceCodeFileMetadata(
            source=f"source_code:{file_path}",
            file_path=file_path,
            language=language,
            analysis_type=self._ANALYSIS_TYPE_SOURCE_CODE,
        )

    def _create_finding_metadata(
        self,
        file_metadata: SourceCodeFileMetadata,
        line_number: int,
        **additional_fields: str | int | bool | None,
    ) -> SourceCodeFindingMetadata:
        """Create metadata for a personal data finding.

        Args:
            file_metadata: File metadata to extend
            line_number: Line number where the finding was detected
            **additional_fields: Additional metadata fields to include

        Returns:
            Strongly-typed metadata for the finding

        """
        # Convert file metadata to dict and add line number and additional fields
        metadata_dict = file_metadata.model_dump()
        metadata_dict["line_number"] = line_number
        metadata_dict.update(additional_fields)

        return SourceCodeFindingMetadata(**metadata_dict)

    def _create_personal_data_finding(
        self,
        data_type: str,
        matched_pattern: str,
        evidence: list[str],
        metadata: SourceCodeFindingMetadata,
    ) -> PersonalDataFinding:
        """Create a PersonalDataFinding with risk information.

        Args:
            data_type: Type of personal data detected
            matched_pattern: Pattern that was matched
            evidence: Evidence snippets for the finding
            metadata: Strongly-typed metadata for the finding

        Returns:
            Configured PersonalDataFinding object

        """
        risk_info = self._get_personal_data_risk_info(data_type)
        return PersonalDataFinding(
            type=data_type,
            risk_level=risk_info["risk_level"],
            special_category=risk_info["special_category"],
            matched_pattern=matched_pattern,
            evidence=evidence,
            metadata=metadata.model_dump(),  # Convert to dict for PersonalDataFinding
        )

    def _analyse_raw_content_data_collection_patterns(
        self,
        raw_content: str,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[PersonalDataFinding]:
        """Analyse raw content for data collection patterns using data_collection_patterns ruleset."""
        findings: list[PersonalDataFinding] = []
        lines = raw_content.split("\n")

        # Use data collection patterns from ruleset
        for rule in self.data_collection_patterns:
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()

                # Check if any patterns from this rule match the line
                for pattern in rule.patterns:
                    if pattern.lower() in line_lower:
                        # Try to extract field name from common patterns
                        field_name = self._extract_field_name_from_line(line, pattern)

                        # Skip if we can't extract a meaningful field name
                        if not field_name:
                            continue

                        # Check if field name suggests personal data
                        personal_data_type = self._classify_field_as_personal_data(
                            field_name
                        )
                        if not personal_data_type:
                            continue

                        finding_metadata = self._create_finding_metadata(
                            file_metadata,
                            line_num,
                            collection_type=rule.metadata.get(
                                "collection_type", "unknown"
                            ),
                            field_name=field_name,
                            pattern_matched=pattern,
                            rule_name=rule.name,
                            data_source=rule.metadata.get("data_source", "unknown"),
                        )

                        evidence = [
                            f"Line {line_num}: {rule.description} - field '{field_name}'",
                            f"Pattern matched: {pattern}",
                            f"Code: {line.strip()}",
                        ]

                        finding = self._create_personal_data_finding(
                            personal_data_type,
                            f"{self._PREFIX_SOURCE_CODE_FIELD}:{field_name}",
                            evidence,
                            finding_metadata,
                        )
                        findings.append(finding)

                        # Avoid duplicate matches for the same line
                        break

        return findings

    def _extract_field_name_from_line(self, line: str, pattern: str) -> str | None:
        """Extract field name from a line where data collection was detected.

        This is a generic extractor that looks for common field naming patterns
        regardless of the specific collection mechanism detected by the ruleset.

        Args:
            line: Line of code containing data collection
            pattern: The ruleset pattern that was matched (for context)

        Returns:
            Extracted field name or None if no field name can be extracted

        """
        # Generic approach: look for quoted strings that could be field names
        # This works across PHP superglobals, HTML attributes, JS, etc.
        quoted_strings = re.findall(r"[\'\"]([\w_-]+)[\'\"]", line)

        for field_name in quoted_strings:
            # Return first reasonable field name (letters, numbers, underscores, hyphens)
            if (
                re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", field_name)
                and len(field_name) > 1
            ):
                return field_name

        # Fallback: look for unquoted identifiers after common patterns
        # This catches cases like: obj.fieldName or input.value
        identifier_matches = re.findall(r"[\.\[]\s*([a-zA-Z_][a-zA-Z0-9_]*)", line)
        for field_name in identifier_matches:
            if len(field_name) > 1:
                return field_name

        return None

    def _analyse_function_patterns(
        self,
        functions: list[SourceCodeFunctionModel],
        file_metadata: SourceCodeFileMetadata,
    ) -> list[PersonalDataFinding]:
        """Analyse function patterns for personal data handling."""
        findings: list[PersonalDataFinding] = []

        for function in functions:
            func_name = function.name
            line_start = function.line_start
            parameters = function.parameters

            # Check function name patterns that suggest personal data handling
            personal_data_type = self._classify_function_as_personal_data(func_name)
            if personal_data_type:
                finding_metadata = self._create_finding_metadata(
                    file_metadata,
                    line_start,
                    function_name=func_name,
                    analysis_pattern=self._PATTERN_FUNCTION_NAME,
                )

                evidence = [
                    f"Line {line_start}: Function '{func_name}' suggests {personal_data_type} handling"
                ]

                finding = self._create_personal_data_finding(
                    personal_data_type,
                    f"{self._PREFIX_SOURCE_CODE_FUNCTION}:{func_name}",
                    evidence,
                    finding_metadata,
                )
                findings.append(finding)

            # Check parameter names for personal data patterns
            for param in parameters:
                param_name = param.name
                personal_data_type = self._classify_field_as_personal_data(param_name)
                if personal_data_type:
                    finding_metadata = self._create_finding_metadata(
                        file_metadata,
                        line_start,
                        function_name=func_name,
                        parameter_name=param_name,
                        analysis_pattern=self._PATTERN_PARAMETER_NAME,
                    )

                    evidence = [
                        f"Line {line_start}: Parameter '{param_name}' in function '{func_name}'"
                    ]

                    finding = self._create_personal_data_finding(
                        personal_data_type,
                        f"{self._PREFIX_SOURCE_CODE_PARAMETER}:{param_name}",
                        evidence,
                        finding_metadata,
                    )
                    findings.append(finding)

        return findings

    def _analyse_class_patterns(
        self, classes: list[SourceCodeClassModel], file_metadata: SourceCodeFileMetadata
    ) -> list[PersonalDataFinding]:
        """Analyse class patterns for personal data models."""
        findings: list[PersonalDataFinding] = []

        for class_data in classes:
            class_name = class_data.name
            line_start = class_data.line_start
            properties = class_data.properties

            # Check class name patterns
            personal_data_type = self._classify_class_as_personal_data(class_name)
            if personal_data_type:
                finding_metadata = self._create_finding_metadata(
                    file_metadata,
                    line_start,
                    class_name=class_name,
                    analysis_pattern=self._PATTERN_CLASS_NAME,
                )

                evidence = [
                    f"Line {line_start}: Class '{class_name}' suggests {personal_data_type} model"
                ]

                finding = self._create_personal_data_finding(
                    personal_data_type,
                    f"{self._PREFIX_SOURCE_CODE_CLASS}:{class_name}",
                    evidence,
                    finding_metadata,
                )
                findings.append(finding)

            # Check property names for personal data patterns
            for prop in properties:
                prop_name = prop.name
                personal_data_type = self._classify_field_as_personal_data(prop_name)
                if personal_data_type:
                    finding_metadata = self._create_finding_metadata(
                        file_metadata,
                        line_start,
                        class_name=class_name,
                        property_name=prop_name,
                        analysis_pattern=self._PATTERN_PROPERTY_NAME,
                    )

                    evidence = [
                        f"Line {line_start}: Property '{prop_name}' in class '{class_name}'"
                    ]

                    finding = self._create_personal_data_finding(
                        personal_data_type,
                        f"{self._PREFIX_SOURCE_CODE_PROPERTY}:{prop_name}",
                        evidence,
                        finding_metadata,
                    )
                    findings.append(finding)

        return findings

    def _analyse_raw_content_sql_patterns(
        self,
        raw_content: str,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[PersonalDataFinding]:
        """Analyse raw content for SQL queries with personal data patterns."""
        findings: list[PersonalDataFinding] = []
        lines = raw_content.split("\n")

        # SQL patterns to detect queries
        sql_patterns = [
            r'(SELECT\s+.*?FROM\s+\w+.*?)[\s;"\']',
            r'(INSERT\s+INTO\s+\w+.*?)[\s;"\']',
            r'(UPDATE\s+\w+\s+SET.*?)[\s;"\']',
            r'(DELETE\s+FROM\s+\w+.*?)[\s;"\']',
        ]

        for line_num, line in enumerate(lines, 1):
            for sql_pattern in sql_patterns:
                matches = re.finditer(sql_pattern, line, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    sql_fragment = match.group(1)

                    # Look for personal data patterns in the SQL
                    personal_data_patterns = self._find_personal_data_in_sql(
                        sql_fragment
                    )

                    for pattern_match in personal_data_patterns:
                        finding_metadata = self._create_finding_metadata(
                            file_metadata,
                            line_num,
                            sql_fragment=sql_fragment[: self._SQL_FRAGMENT_MAX_LENGTH],
                            analysis_pattern=self._PATTERN_SQL_QUERY,
                            sql_type=sql_fragment.split()[
                                0
                            ].upper(),  # SELECT, INSERT, etc.
                        )

                        evidence = [
                            f"Line {line_num}: SQL query with {pattern_match['type']} pattern",
                            f"SQL: {sql_fragment[: self._SQL_EVIDENCE_DISPLAY_MAX_LENGTH]}..."
                            if len(sql_fragment) > self._SQL_EVIDENCE_DISPLAY_MAX_LENGTH
                            else f"SQL: {sql_fragment}",
                            f"Pattern match: {pattern_match['match']}",
                        ]

                        finding = self._create_personal_data_finding(
                            pattern_match["type"],
                            f"{self._PREFIX_SOURCE_CODE_SQL}:{pattern_match['match']}",
                            evidence,
                            finding_metadata,
                        )
                        findings.append(finding)

        return findings

    def _analyse_raw_content_third_party_patterns(
        self,
        raw_content: str,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[PersonalDataFinding]:
        """Analyse raw content for third-party service integrations using third_party_services ruleset."""
        findings: list[PersonalDataFinding] = []
        lines = raw_content.split("\n")

        # Use third-party service patterns from ruleset
        for rule in self.third_party_service_patterns:
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()

                # Check if any patterns from this rule match the line
                for pattern in rule.patterns:
                    if pattern.lower() in line_lower:
                        # Look for context suggesting personal data usage
                        personal_data_context = (
                            self._detect_personal_data_context_in_line(line_lower)
                        )

                        # Only report if there's evidence of personal data involvement
                        if not personal_data_context:
                            continue

                        finding_metadata = self._create_finding_metadata(
                            file_metadata,
                            line_num,
                            service_name=pattern,
                            service_category=rule.metadata.get(
                                "service_category", "unknown"
                            ),
                            analysis_pattern=self._PATTERN_THIRD_PARTY,
                            detected_context=personal_data_context,
                            rule_name=rule.name,
                        )

                        evidence = [
                            f"Line {line_num}: {rule.description} - {pattern}",
                            f"Personal data context: {personal_data_context}",
                            f"Code: {line.strip()}",
                        ]

                        finding = PersonalDataFinding(
                            type=self._TYPE_THIRD_PARTY_SHARING,
                            risk_level=rule.risk_level,
                            special_category=self._DEFAULT_SPECIAL_CATEGORY,
                            matched_pattern=f"{self._PREFIX_SOURCE_CODE_INTEGRATION}:{pattern}",
                            evidence=evidence,
                            metadata=finding_metadata.model_dump(),
                        )
                        findings.append(finding)

                        # Avoid duplicate matches for the same line/rule
                        break

        return findings

    def _detect_personal_data_context_in_line(self, line: str) -> str | None:
        """Detect if a line contains context suggesting personal data usage using personal_data ruleset.

        Args:
            line: Line of code to analyze (should be lowercase)

        Returns:
            Description of personal data context found, or None if no context detected

        """
        # Use personal data patterns to detect context
        for rule in self.personal_data_patterns:
            for pattern in rule.patterns:
                if pattern.lower() in line:
                    return f"{rule.name} ({pattern})"

        return None

    def _classify_field_as_personal_data(self, field_name: str) -> str | None:
        """Classify a field name as a personal data category.

        Now uses the enhanced personal_data patterns directly instead of field pattern types.
        """
        processed_name = field_name.lower().strip("$_")
        return self._classify_name_as_personal_data(processed_name)

    def _classify_function_as_personal_data(self, func_name: str) -> str | None:
        """Classify a function name as handling personal data."""
        processed_name = func_name.lower()
        return self._classify_name_as_personal_data(processed_name)

    def _classify_class_as_personal_data(self, class_name: str) -> str | None:
        """Classify a class name as a personal data model."""
        processed_name = class_name.lower()
        return self._classify_name_as_personal_data(processed_name)

    def _classify_name_as_personal_data(self, processed_name: str) -> str | None:
        """Core classification logic for personal data patterns.

        Args:
            processed_name: Preprocessed and normalised name to classify

        Returns:
            Personal data type if matched, None otherwise

        """
        if not processed_name:
            return None

        # Use personal_data patterns directly
        for rule in self.personal_data_patterns:
            if any(pattern in processed_name for pattern in rule.patterns):
                return rule.name

        return None

    def _find_personal_data_in_sql(self, sql: str) -> list[dict[str, str]]:
        """Find personal data patterns in SQL queries."""
        matches: list[dict[str, str]] = []
        sql_lower = sql.lower()

        # Use merged personal data patterns which now include SQL patterns
        for rule in self.personal_data_patterns:
            for pattern in rule.patterns:
                if pattern in sql_lower:
                    matches.append({"match": pattern, "type": rule.name})

        return matches

    def _get_personal_data_risk_info(self, data_type: str) -> dict[str, str]:
        """Get risk information for a personal data type/category.

        Now uses personal_data patterns directly since data_type is the category name.

        Args:
            data_type: The personal data type to get risk information for

        Returns:
            Dictionary containing risk_level and special_category information

        """
        if not data_type:
            return self._get_default_risk_info()

        # data_type is now the category name from personal_data patterns
        for rule in self.personal_data_patterns:
            if rule.name == data_type:
                return {
                    "risk_level": rule.risk_level,
                    "special_category": rule.metadata.get(
                        "special_category", self._DEFAULT_SPECIAL_CATEGORY
                    ),
                }

        # Default fallback
        return self._get_default_risk_info()

    def _get_default_risk_info(self) -> dict[str, str]:
        """Get default risk information for unclassified personal data types.

        Returns:
            Dictionary with default risk level and special category

        """
        return {
            "risk_level": self._DEFAULT_RISK_LEVEL,
            "special_category": self._DEFAULT_SPECIAL_CATEGORY,
        }
