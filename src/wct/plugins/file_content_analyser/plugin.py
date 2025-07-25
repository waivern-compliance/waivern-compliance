"""Content analysis plugin for detecting sensitive information."""

import json
import re
from pathlib import Path
from typing import Any

import jsonschema
from typing_extensions import Self, override

from wct.plugins.base import Plugin, PluginInputError
from wct.schema import WctSchema


class FileContentAnalyser(Plugin[dict[str, Any], dict[str, Any]]):
    """Analyzes file content for potentially sensitive information.

    This plugin looks for patterns that might indicate sensitive data
    like email addresses, potential passwords, API keys, etc.
    """

    def __init__(self, sensitivity_level: str = "medium"):
        self.sensitivity_level = sensitivity_level

        # Define patterns for different types of sensitive data
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "potential_password": re.compile(
                r'(?i)(password|pwd|pass)\s*[:=]\s*[\'"]?([^\'"\s]+)[\'"]?'
            ),
            "api_key": re.compile(
                r'(?i)(api_key|apikey|access_key)\s*[:=]\s*[\'"]?([A-Za-z0-9]{20,})[\'"]?'
            ),
        }

    @classmethod
    @override
    def get_name(cls) -> str:
        return "file_content_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        sensitivity_level = properties.get("sensitivity_level", "medium")
        return cls(sensitivity_level=sensitivity_level)

    @override
    def process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analyze file content for sensitive information."""
        # Extract content from the new schema-aware structure
        schema_content = data.get("content", {})

        # Get the actual text content from the schema structure
        content_array = schema_content.get("content", [])
        if not content_array:
            content = ""
        else:
            # Combine all text content from the array (usually just one item)
            content = "\n".join(item.get("text", "") for item in content_array)

        # Get metadata from both levels
        file_path = data.get("file_path", schema_content.get("source", "unknown"))
        encoding = schema_content.get("contentEncoding", "unknown")
        file_metadata = schema_content.get("metadata", {})

        findings = []

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches:
                findings.append(
                    {
                        "type": pattern_name,
                        "count": len(matches),
                        "severity": self._get_severity(pattern_name),
                        "samples": matches[:3]
                        if self.sensitivity_level == "high"
                        else [],
                    }
                )

        risk_score = self._calculate_risk_score(findings)

        return {
            "source": file_path,
            "encoding": encoding,
            "file_metadata": file_metadata,
            "content_length": len(content),
            "findings": findings,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "analysis_metadata": {
                "sensitivity_level": self.sensitivity_level,
                "patterns_checked": list(self.patterns.keys()),
            },
        }

    @override
    def get_input_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="text", type=dict[str, Any])

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="content_analysis_result", type=dict[str, Any])

    @override
    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate input data against the plugin's input schema."""
        input_schema = self.get_input_schema()

        try:
            # Load the JSON schema file for validation
            schema_content = self._load_json_schema(input_schema.name)

            # Validate top-level structure (from FileConnector)
            if "content" not in data:
                raise PluginInputError("Missing required field: content")

            # Validate the content against the JSON schema
            jsonschema.validate(data["content"], schema_content)

            return True

        except jsonschema.ValidationError as e:
            raise PluginInputError(f"Schema validation failed: {e.message}") from e
        except FileNotFoundError:
            # Fallback to basic validation if schema file not found
            return self._fallback_validation(data)
        except Exception as e:
            raise PluginInputError(f"Validation error: {e}") from e

    def _load_json_schema(self, schema_name: str) -> dict[str, Any]:
        """Load JSON schema from file.

        Args:
            schema_name: Name of the schema to load

        Returns:
            The JSON schema as a dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        # Try multiple potential locations for schema files
        schema_paths = [
            Path("src/wct/schemas") / f"{schema_name}.json",
            Path("./src/wct/schemas") / f"{schema_name}.json",
            Path(__file__).parent.parent.parent / "schemas" / f"{schema_name}.json",
        ]

        for schema_path in schema_paths:
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    return json.load(f)

        raise FileNotFoundError(
            f"Schema file for '{schema_name}' not found in any of: {schema_paths}"
        )

    def _fallback_validation(self, data: dict[str, Any]) -> bool:
        """Fallback validation when schema file is not available."""
        # Basic validation similar to the original hardcoded version
        if "content" not in data:
            raise PluginInputError("Missing required field: content")

        schema_content = data["content"]
        if not isinstance(schema_content, dict):
            raise PluginInputError("Field 'content' must be a dictionary")

        # Basic text schema validation
        if schema_content.get("name") != "text":
            raise PluginInputError("Content schema name must be 'text'")

        if "content" not in schema_content:
            raise PluginInputError("Missing 'content' array in text schema")

        content_array = schema_content["content"]
        if not isinstance(content_array, list):
            raise PluginInputError("Schema 'content' field must be an array")

        return True

    def _get_severity(self, pattern_name: str) -> str:
        """Get severity level for different pattern types."""
        severity_map = {
            "email": "low",
            "potential_password": "high",
            "api_key": "critical",
        }
        return severity_map.get(pattern_name, "medium")

    def _calculate_risk_score(self, findings: list[dict[str, Any]]) -> int:
        """Calculate overall risk score based on findings."""
        score = 0
        severity_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}

        for finding in findings:
            severity = finding.get("severity", "medium")
            count = finding.get("count", 0)
            score += severity_scores.get(severity, 3) * count

        return min(score, 100)  # Cap at 100

    def _get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level."""
        if risk_score >= 50:
            return "critical"
        elif risk_score >= 20:
            return "high"
        elif risk_score >= 5:
            return "medium"
        else:
            return "low"
