"""WCT Plugins - backward compatibility module.

This module re-exports all plugin classes for backward compatibility.
The actual implementations are in the plugins package.
"""

from __future__ import annotations

# Import from base for compatibility
import abc
import re
from typing import Any

from typing_extensions import Self


class Plugin(abc.ABC):
    """Analysis processor that accepts schema-compliant data and produces results.

    Plugins are the workers of WCF. They accept input data in WCF-defined
    schema(s), run it against a specific analysis process, and then produce
    the analysis results in the WCF-defined result schema.

    Plugins behave like pure functions - they accept data in pre-defined
    input schemas and return results in pre-defined result schemas.
    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Get the name of the plugin.

        This is used to identify the plugin in the system.
        """

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this plugin from a dictionary of properties.

        The `properties` dictionary is the configuration for the plugin
        as specified in the runbook configuration file.
        """

    @abc.abstractmethod
    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process input data and return analysis results.

        This is the core method where the analysis happens. The plugin
        receives data in its expected input schema and returns results
        in its defined output schema.

        Args:
            data: Input data conforming to the plugin's input schema

        Returns:
            Analysis results conforming to the plugin's output schema

        Raises:
            PluginError: If processing fails
        """

    @abc.abstractmethod
    def get_input_schema(self) -> str:
        """Return the name of the input schema this plugin expects.

        Returns:
            The schema name that this plugin's process() method expects
        """

    @abc.abstractmethod
    def get_output_schema(self) -> str:
        """Return the name of the output schema this plugin produces.

        Returns:
            The schema name that this plugin's process() method returns
        """

    @abc.abstractmethod
    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate that input data conforms to the expected schema.

        Args:
            data: Input data to validate

        Returns:
            True if data is valid

        Raises:
            PluginInputError: If input data is invalid
        """


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginInputError(PluginError):
    """Raised when plugin input data is invalid."""

    pass


class PluginProcessingError(PluginError):
    """Raised when plugin processing fails."""

    pass


class ContentAnalysisPlugin(Plugin):
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
    def get_name(cls) -> str:
        return "content_analysis"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        sensitivity_level = properties.get("sensitivity_level", "medium")
        return cls(sensitivity_level=sensitivity_level)

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analyze file content for sensitive information."""
        content = data.get("content", "")
        file_path = data.get("file_path", "unknown")

        findings = []

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches:
                findings.append(
                    {
                        "type": pattern_name,
                        "count": len(matches),
                        "severity": self._get_severity(pattern_name),
                    }
                )

        risk_score = self._calculate_risk_score(findings)

        return {
            "file_path": file_path,
            "findings": findings,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
        }

    def get_input_schema(self) -> str:
        return "file_content"

    def get_output_schema(self) -> str:
        return "content_analysis_result"

    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate that input data contains required fields."""
        if "content" not in data:
            raise PluginInputError("Missing required field: content")

        if not isinstance(data["content"], str):
            raise PluginInputError("Field 'content' must be a string")

        return True

    def _get_severity(self, pattern_name: str) -> str:
        """Get severity level for different pattern types."""
        severity_map = {
            "email": "low",
            "potential_password": "high",
            "api_key": "critical",
        }
        return severity_map.get(pattern_name, "medium")

    def _calculate_risk_score(self, findings: list) -> int:
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
