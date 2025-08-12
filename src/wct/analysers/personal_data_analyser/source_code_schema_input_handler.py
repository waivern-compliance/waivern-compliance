"""Source code schema input handler for personal data detection in source code analysis results."""

from typing import Any

from wct.rulesets import RulesetLoader

from .types import PersonalDataFinding


class SourceCodeSchemaInputHandler:
    """Handler for processing source code analysis schema input to detect personal data patterns.

    This handler is responsible for all source code analysis logic including loading
    the appropriate rulesets for personal data detection in source code.
    """

    def __init__(self):
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load personal data patterns (now includes merged SQL and code patterns)
        self.personal_data_patterns = RulesetLoader.load_ruleset("personal_data")

    def analyse_source_code_data(
        self, data: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze source code analysis data for personal data collection patterns.

        This method examines source code analysis results to identify patterns that
        indicate personal data collection, processing, or storage.

        Args:
            data: Source code analysis data from SourceCodeConnector

        Returns:
            List of personal data findings from source code analysis

        """
        findings = []

        # Analyze each file in the source code analysis
        for file_data in data.get("data", []):
            file_path = file_data.get("file_path", "unknown")
            language = file_data.get("language", "unknown")

            # Create base metadata for this file
            file_metadata = {
                "source": f"source_code:{file_path}",
                "file_path": file_path,
                "language": language,
                "analysis_type": "source_code_patterns",
            }

            # Analyze data collection indicators
            data_collection_findings = self._analyse_data_collection_indicators(
                file_data.get("data_collection_indicators", []), file_metadata
            )
            findings.extend(data_collection_findings)

            # Analyze function patterns for personal data handling
            function_findings = self._analyse_function_patterns(
                file_data.get("functions", []), file_metadata
            )
            findings.extend(function_findings)

            # Analyze class patterns for personal data models
            class_findings = self._analyse_class_patterns(
                file_data.get("classes", []), file_metadata
            )
            findings.extend(class_findings)

            # Analyze database interactions for personal data queries
            db_findings = self._analyse_database_interactions(
                file_data.get("database_interactions", []), file_metadata
            )
            findings.extend(db_findings)

            # Analyze third-party integrations for data sharing
            third_party_findings = self._analyse_third_party_integrations(
                file_data.get("third_party_integrations", []), file_metadata
            )
            findings.extend(third_party_findings)

        return findings

    def _analyse_data_collection_indicators(
        self, indicators: list[dict[str, Any]], base_metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze data collection indicators for personal data patterns."""
        findings = []

        for indicator in indicators:
            indicator_type = indicator.get("type", "")
            field_name = indicator.get("field_name", "")
            line = indicator.get("line", 0)
            potential_pii = indicator.get("potential_pii", False)

            if not potential_pii:
                continue

            # Map field names to personal data types
            personal_data_type = self._classify_field_as_personal_data(field_name)
            if not personal_data_type:
                continue

            # Create metadata for this finding
            finding_metadata = base_metadata.copy()
            finding_metadata.update(
                {
                    "line_number": line,
                    "collection_type": indicator_type,
                    "field_name": field_name,
                    "context": indicator.get("context", ""),
                }
            )

            # Get risk information from patterns
            risk_info = self._get_personal_data_risk_info(personal_data_type)

            evidence = [f"Line {line}: {indicator_type} field '{field_name}'"]
            if indicator.get("context"):
                evidence.append(f"Context: {indicator['context']}")

            finding = PersonalDataFinding(
                type=personal_data_type,
                risk_level=risk_info["risk_level"],
                special_category=risk_info["special_category"],
                matched_pattern=f"source_code_field:{field_name}",
                evidence=evidence,
                metadata=finding_metadata,
            )
            findings.append(finding)

        return findings

    def _analyse_function_patterns(
        self, functions: list[dict[str, Any]], base_metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze function patterns for personal data handling."""
        findings = []

        for function in functions:
            func_name = function.get("name", "")
            line_start = function.get("line_start", 0)
            parameters = function.get("parameters", [])

            # Check function name patterns that suggest personal data handling
            personal_data_type = self._classify_function_as_personal_data(func_name)
            if personal_data_type:
                finding_metadata = base_metadata.copy()
                finding_metadata.update(
                    {
                        "line_number": line_start,
                        "function_name": func_name,
                        "analysis_pattern": "function_name",
                    }
                )

                risk_info = self._get_personal_data_risk_info(personal_data_type)
                evidence = [
                    f"Line {line_start}: Function '{func_name}' suggests {personal_data_type} handling"
                ]

                finding = PersonalDataFinding(
                    type=personal_data_type,
                    risk_level=risk_info["risk_level"],
                    special_category=risk_info["special_category"],
                    matched_pattern=f"source_code_function:{func_name}",
                    evidence=evidence,
                    metadata=finding_metadata,
                )
                findings.append(finding)

            # Check parameter names for personal data patterns
            for param in parameters:
                param_name = param.get("name", "")
                personal_data_type = self._classify_field_as_personal_data(param_name)
                if personal_data_type:
                    finding_metadata = base_metadata.copy()
                    finding_metadata.update(
                        {
                            "line_number": line_start,
                            "function_name": func_name,
                            "parameter_name": param_name,
                            "analysis_pattern": "parameter_name",
                        }
                    )

                    risk_info = self._get_personal_data_risk_info(personal_data_type)
                    evidence = [
                        f"Line {line_start}: Parameter '{param_name}' in function '{func_name}'"
                    ]

                    finding = PersonalDataFinding(
                        type=personal_data_type,
                        risk_level=risk_info["risk_level"],
                        special_category=risk_info["special_category"],
                        matched_pattern=f"source_code_parameter:{param_name}",
                        evidence=evidence,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings

    def _analyse_class_patterns(
        self, classes: list[dict[str, Any]], base_metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze class patterns for personal data models."""
        findings = []

        for class_data in classes:
            class_name = class_data.get("name", "")
            line_start = class_data.get("line_start", 0)
            properties = class_data.get("properties", [])

            # Check class name patterns
            personal_data_type = self._classify_class_as_personal_data(class_name)
            if personal_data_type:
                finding_metadata = base_metadata.copy()
                finding_metadata.update(
                    {
                        "line_number": line_start,
                        "class_name": class_name,
                        "analysis_pattern": "class_name",
                    }
                )

                risk_info = self._get_personal_data_risk_info(personal_data_type)
                evidence = [
                    f"Line {line_start}: Class '{class_name}' suggests {personal_data_type} model"
                ]

                finding = PersonalDataFinding(
                    type=personal_data_type,
                    risk_level=risk_info["risk_level"],
                    special_category=risk_info["special_category"],
                    matched_pattern=f"source_code_class:{class_name}",
                    evidence=evidence,
                    metadata=finding_metadata,
                )
                findings.append(finding)

            # Check property names for personal data patterns
            for prop in properties:
                prop_name = prop.get("name", "")
                personal_data_type = self._classify_field_as_personal_data(prop_name)
                if personal_data_type:
                    finding_metadata = base_metadata.copy()
                    finding_metadata.update(
                        {
                            "line_number": line_start,
                            "class_name": class_name,
                            "property_name": prop_name,
                            "analysis_pattern": "property_name",
                        }
                    )

                    risk_info = self._get_personal_data_risk_info(personal_data_type)
                    evidence = [
                        f"Line {line_start}: Property '{prop_name}' in class '{class_name}'"
                    ]

                    finding = PersonalDataFinding(
                        type=personal_data_type,
                        risk_level=risk_info["risk_level"],
                        special_category=risk_info["special_category"],
                        matched_pattern=f"source_code_property:{prop_name}",
                        evidence=evidence,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings

    def _analyse_database_interactions(
        self, db_interactions: list[dict[str, Any]], base_metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze database interactions for personal data queries."""
        findings = []

        for interaction in db_interactions:
            line = interaction.get("line", 0)
            sql_fragment = interaction.get("sql_fragment", "")
            contains_user_input = interaction.get("contains_user_input", False)

            if not sql_fragment:
                continue

            # Look for personal data table/column patterns in SQL
            personal_data_patterns = self._find_personal_data_in_sql(sql_fragment)

            for pattern_match in personal_data_patterns:
                finding_metadata = base_metadata.copy()
                finding_metadata.update(
                    {
                        "line_number": line,
                        "sql_fragment": sql_fragment[:200],  # Limit length
                        "contains_user_input": contains_user_input,
                        "analysis_pattern": "sql_query",
                    }
                )

                risk_info = self._get_personal_data_risk_info(pattern_match["type"])
                evidence = [
                    f"Line {line}: SQL query with {pattern_match['type']} pattern: {pattern_match['match']}"
                ]

                finding = PersonalDataFinding(
                    type=pattern_match["type"],
                    risk_level=risk_info["risk_level"],
                    special_category=risk_info["special_category"],
                    matched_pattern=f"source_code_sql:{pattern_match['match']}",
                    evidence=evidence,
                    metadata=finding_metadata,
                )
                findings.append(finding)

        return findings

    def _analyse_third_party_integrations(
        self, integrations: list[dict[str, Any]], base_metadata: dict[str, Any]
    ) -> list[PersonalDataFinding]:
        """Analyze third-party integrations for personal data sharing."""
        findings = []

        for integration in integrations:
            service_name = integration.get("service_name", "")
            line = integration.get("line", 0)
            contains_personal_data = integration.get("contains_personal_data", False)

            if not contains_personal_data:
                continue

            # Classify third-party service for personal data risk
            service_risk = self._classify_third_party_service_risk(service_name)

            finding_metadata = base_metadata.copy()
            finding_metadata.update(
                {
                    "line_number": line,
                    "service_name": service_name,
                    "integration_type": integration.get("type", ""),
                    "endpoint": integration.get("endpoint", ""),
                    "analysis_pattern": "third_party_integration",
                }
            )

            evidence = [
                f"Line {line}: Third-party integration with {service_name} containing personal data"
            ]

            finding = PersonalDataFinding(
                type="third_party_sharing",
                risk_level=service_risk["risk_level"],
                special_category="N",  # Third-party sharing itself is not special category
                matched_pattern=f"source_code_integration:{service_name}",
                evidence=evidence,
                metadata=finding_metadata,
            )
            findings.append(finding)

        return findings

    def _classify_field_as_personal_data(self, field_name: str) -> str | None:
        """Classify a field name as a personal data category.

        Now uses the enhanced personal_data patterns directly instead of field pattern types.
        """
        field_lower = field_name.lower().strip("$_")

        # Use personal_data patterns directly
        for rule in self.personal_data_patterns:
            if any(pattern in field_lower for pattern in rule.patterns):
                return rule.name  # Return the rule name directly

        return None

    def _classify_function_as_personal_data(self, func_name: str) -> str | None:
        """Classify a function name as handling personal data."""
        func_lower = func_name.lower()

        # Use merged personal data patterns which now include function patterns
        for rule in self.personal_data_patterns:
            if any(pattern in func_lower for pattern in rule.patterns):
                return rule.name

        return None

    def _classify_class_as_personal_data(self, class_name: str) -> str | None:
        """Classify a class name as a personal data model."""
        class_lower = class_name.lower()

        # Use merged personal data patterns which now include model patterns
        for rule in self.personal_data_patterns:
            if any(pattern in class_lower for pattern in rule.patterns):
                return rule.name

        return None

    def _find_personal_data_in_sql(self, sql: str) -> list[dict[str, str]]:
        """Find personal data patterns in SQL queries."""
        matches = []
        sql_lower = sql.lower()

        # Use merged personal data patterns which now include SQL patterns
        for rule in self.personal_data_patterns:
            for pattern in rule.patterns:
                if pattern in sql_lower:
                    matches.append({"match": pattern, "type": rule.name})

        return matches

    def _classify_third_party_service_risk(self, service_name: str) -> dict[str, str]:
        """Classify third-party service for personal data sharing risk."""
        # For now, return medium risk for all third-party services
        # TODO: Add third-party service risk patterns to rulesets if needed
        return {"risk_level": "medium"}

    def _get_personal_data_risk_info(self, data_type: str) -> dict[str, str]:
        """Get risk information for a personal data type/category.

        Now uses personal_data patterns directly since data_type is the category name.
        """
        # data_type is now the category name from personal_data patterns
        for rule in self.personal_data_patterns:
            if rule.name == data_type:
                return {
                    "risk_level": rule.risk_level,
                    "special_category": rule.metadata.get("special_category", "N"),
                }

        # All patterns (SQL, functions, models) are now merged into personal_data_patterns
        # No separate code rules to check

        # Default fallback
        return {"risk_level": "medium", "special_category": "N"}
