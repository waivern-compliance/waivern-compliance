"""Configuration for SourceCodeAnalyser."""

from typing import Any, Self, override

from pydantic import Field, ValidationError, field_validator
from waivern_core import BaseComponentConfiguration
from waivern_core.errors import AnalyserConfigError

from waivern_source_code_analyser.validators import validate_and_normalise_language


class SourceCodeAnalyserConfig(BaseComponentConfiguration):
    """Configuration for SourceCodeAnalyser with Pydantic validation.

    This provides strong typing and validation for source code analyser
    configuration parameters with sensible defaults. Unlike the connector
    config, this focuses purely on parsing configuration as file discovery
    is handled by FilesystemConnector upstream.
    """

    language: str | None = Field(
        default=None,
        description="Programming language (auto-detected if None)",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Skip files larger than this size in bytes",
        gt=0,
    )

    @field_validator("language")
    @classmethod
    def validate_language_if_provided(cls, v: str | None) -> str | None:
        """Validate language if provided (optional validation for supported languages)."""
        return validate_and_normalise_language(v)

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration containing:
                - language (str, optional): Programming language.
                - max_file_size (int, optional): Maximum file size to process.

        Returns:
            Validated configuration object

        Raises:
            AnalyserConfigError: If validation fails

        """
        try:
            return cls.model_validate(properties)
        except ValidationError as e:
            # Provide clear error messages for validation failures
            raise AnalyserConfigError(
                f"Invalid source code analyser configuration: {e}"
            ) from e
        except ValueError as e:
            raise AnalyserConfigError(
                f"Invalid source code analyser configuration: {e}"
            ) from e
