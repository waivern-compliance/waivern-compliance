"""Source code schema input handler for personal data detection in source code analysis results."""

from typing import Any

from wct.rulesets import RulesetLoader
from wct.schemas import (
    SourceCodeClassModel,
    SourceCodeDatabaseInteractionModel,
    SourceCodeDataCollectionIndicatorModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFunctionModel,
    SourceCodeThirdPartyIntegrationModel,
)

from .types import PersonalDataFinding


class SourceCodeSchemaInputHandler:
    """Handler for processing source code analysis schema input to detect personal data patterns.

    This handler is responsible for all source code analysis logic including loading
    the appropriate rulesets for personal data detection in source code.
    """

    # Private constants for configuration values
    _RULESET_NAME = "personal_data"
    _UNKNOWN_VALUE = "unknown"
    _DEFAULT_LINE_NUMBER = 0
    _DEFAULT_SPECIAL_CATEGORY = "N"
    _DEFAULT_RISK_LEVEL = "medium"
    _SQL_FRAGMENT_MAX_LENGTH = 200

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
        # Load personal data patterns (now includes merged SQL and code patterns)
        self.personal_data_patterns = RulesetLoader.load_ruleset(self._RULESET_NAME)

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

        # Analyse data collection indicators
        data_collection_findings = self._analyse_data_collection_indicators(
            file_data.data_collection_indicators, file_metadata
        )
        findings.extend(data_collection_findings)

        # Analyse function patterns for personal data handling
        function_findings = self._analyse_function_patterns(
            file_data.functions, file_metadata
        )
        findings.extend(function_findings)

        # Analyse class patterns for personal data models
        class_findings = self._analyse_class_patterns(file_data.classes, file_metadata)
        findings.extend(class_findings)

        # Analyse database interactions for personal data queries
        db_findings = self._analyse_database_interactions(
            file_data.database_interactions, file_metadata
        )
        findings.extend(db_findings)

        # Analyse third-party integrations for data sharing
        third_party_findings = self._analyse_third_party_integrations(
            file_data.third_party_integrations, file_metadata
        )
        findings.extend(third_party_findings)

        return findings

    def _create_base_file_metadata(
        self, file_path: str, language: str
    ) -> dict[str, Any]:
        """Create base metadata for a source code file.

        Args:
            file_path: Path to the source code file
            language: Programming language of the file

        Returns:
            Dictionary containing base metadata for the file

        """
        return {
            "source": f"source_code:{file_path}",
            "file_path": file_path,
            "language": language,
            # For information/debugging purposes, not really used anywhere
            "analysis_type": self._ANALYSIS_TYPE_SOURCE_CODE,
        }

    def _create_finding_metadata(
        self,
        base_metadata: dict[str, Any],
        line_number: int,
        **additional_fields: str | int | bool,
    ) -> dict[str, Any]:
        """Create metadata for a personal data finding.

        Args:
            base_metadata: Base metadata to extend
            line_number: Line number where the finding was detected
            **additional_fields: Additional metadata fields to include

        Returns:
            Complete metadata dictionary for the finding

        """
        finding_metadata = base_metadata.copy()
        finding_metadata["line_number"] = line_number
        finding_metadata.update(additional_fields)
        return finding_metadata

    def _create_personal_data_finding(
        self,
        data_type: str,
        matched_pattern: str,
        evidence: list[str],
        metadata: dict[str, Any],
    ) -> PersonalDataFinding:
        """Create a PersonalDataFinding with risk information.

        Args:
            data_type: Type of personal data detected
            matched_pattern: Pattern that was matched
            evidence: Evidence snippets for the finding
            metadata: Metadata for the finding

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
            metadata=metadata,
        )

    def _analyse_data_collection_indicators(
        self,
        indicators: list[SourceCodeDataCollectionIndicatorModel],
        base_metadata: dict[str, Any],
    ) -> list[PersonalDataFinding]:
        """Analyse data collection indicators for personal data patterns."""
        findings: list[PersonalDataFinding] = []

        for indicator in indicators:
            indicator_type = indicator.type
            field_name = indicator.field_name or ""
            line = indicator.line
            potential_pii = indicator.potential_pii

            if not potential_pii:
                continue

            # Map field names to personal data types
            personal_data_type = self._classify_field_as_personal_data(field_name)
            if not personal_data_type:
                continue

            # Create metadata for this finding
            finding_metadata = self._create_finding_metadata(
                base_metadata,
                line,
                collection_type=indicator_type,
                field_name=field_name,
                context=indicator.context or "",
            )

            evidence = [f"Line {line}: {indicator_type} field '{field_name}'"]
            if indicator.context:
                evidence.append(f"Context: {indicator.context}")

            finding = self._create_personal_data_finding(
                personal_data_type,
                f"{self._PREFIX_SOURCE_CODE_FIELD}:{field_name}",
                evidence,
                finding_metadata,
            )
            findings.append(finding)

        return findings

    def _analyse_function_patterns(
        self, functions: list[SourceCodeFunctionModel], base_metadata: dict[str, Any]
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
                    base_metadata,
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
                        base_metadata,
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
        self, classes: list[SourceCodeClassModel], base_metadata: dict[str, Any]
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
                    base_metadata,
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
                        base_metadata,
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

    def _analyse_database_interactions(
        self,
        db_interactions: list[SourceCodeDatabaseInteractionModel],
        base_metadata: dict[str, Any],
    ) -> list[PersonalDataFinding]:
        """Analyse database interactions for personal data queries."""
        findings: list[PersonalDataFinding] = []

        for interaction in db_interactions:
            line = interaction.line
            sql_fragment = interaction.sql_fragment or ""
            contains_user_input = interaction.contains_user_input

            if not sql_fragment:
                continue

            # Look for personal data table/column patterns in SQL
            personal_data_patterns = self._find_personal_data_in_sql(sql_fragment)

            for pattern_match in personal_data_patterns:
                finding_metadata = self._create_finding_metadata(
                    base_metadata,
                    line,
                    sql_fragment=sql_fragment[: self._SQL_FRAGMENT_MAX_LENGTH],
                    contains_user_input=contains_user_input,
                    analysis_pattern=self._PATTERN_SQL_QUERY,
                )

                evidence = [
                    f"Line {line}: SQL query with {pattern_match['type']} pattern: {pattern_match['match']}"
                ]

                finding = self._create_personal_data_finding(
                    pattern_match["type"],
                    f"{self._PREFIX_SOURCE_CODE_SQL}:{pattern_match['match']}",
                    evidence,
                    finding_metadata,
                )
                findings.append(finding)

        return findings

    def _analyse_third_party_integrations(
        self,
        integrations: list[SourceCodeThirdPartyIntegrationModel],
        base_metadata: dict[str, Any],
    ) -> list[PersonalDataFinding]:
        """Analyse third-party integrations for personal data sharing."""
        findings: list[PersonalDataFinding] = []

        for integration in integrations:
            service_name = integration.service_name
            line = integration.line
            contains_personal_data = integration.contains_personal_data

            if not contains_personal_data:
                continue

            # Classify third-party service for personal data risk
            service_risk = self._classify_third_party_service_risk(service_name)

            finding_metadata = self._create_finding_metadata(
                base_metadata,
                line,
                service_name=service_name,
                integration_type=integration.type,
                endpoint=integration.endpoint or "",
                analysis_pattern=self._PATTERN_THIRD_PARTY,
            )

            evidence = [
                f"Line {line}: Third-party integration with {service_name} containing personal data"
            ]

            finding = PersonalDataFinding(
                type=self._TYPE_THIRD_PARTY_SHARING,
                risk_level=service_risk["risk_level"],
                special_category=self._DEFAULT_SPECIAL_CATEGORY,
                matched_pattern=f"{self._PREFIX_SOURCE_CODE_INTEGRATION}:{service_name}",
                evidence=evidence,
                metadata=finding_metadata,
            )
            findings.append(finding)

        return findings

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

    def _classify_third_party_service_risk(self, service_name: str) -> dict[str, str]:
        """Classify third-party service for personal data sharing risk.

        Args:
            service_name: Name of the third-party service

        Returns:
            Dictionary containing risk level for the service

        """
        # For now, return medium risk for all third-party services
        # TODO: Add third-party service risk patterns to rulesets if needed
        return {"risk_level": self._DEFAULT_RISK_LEVEL}

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
