"""Configuration for SourceCodeConnector."""

from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)
from typing_extensions import Self

from wct.connectors.base import ConnectorConfigError

# Common file patterns to exclude from source code analysis
_DEFAULT_EXCLUDE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    "*.class",
    "*.o",
    "*.so",
    "*.dll",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".DS_Store",
    "*.log",
    "*.tmp",
    "*.bak",
    "*.swp",
    "*.swo",
]


def _validate_path_required(v: str | Path | None) -> Path:
    """Validate that path is provided and convert to Path object."""
    if v is None:
        raise ValueError("path property is required")

    # Convert string to Path if needed
    if isinstance(v, str):
        if not v.strip():
            raise ValueError("path property is required")
        path_obj = Path(v.strip())
    else:
        # v must be a Path object at this point due to type annotation
        path_obj = v

    # Validate the Path object exists
    if not path_obj.exists():
        raise ValueError(f"Path does not exist: {path_obj}")

    return path_obj


class SourceCodeConnectorConfig(BaseModel):
    """Configuration for SourceCodeConnector with Pydantic validation.

    This provides strong typing and validation for source code connector
    configuration parameters with sensible defaults.
    """

    path: Annotated[Path, BeforeValidator(lambda v: _validate_path_required(v))] = (
        Field(description="Path to source code file or directory")
    )
    language: str | None = Field(
        default=None,
        description="Programming language (auto-detected if None)",
    )
    file_patterns: list[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns for file inclusion",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Skip files larger than this size in bytes",
        gt=0,
    )
    max_files: int = Field(
        default=4000,
        description="Maximum number of files to process",
        gt=0,
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_EXCLUDE_PATTERNS),
        description="Glob patterns to exclude from processing. Defaults to common exclusions (*.pyc, __pycache__, etc.). Specify custom patterns to override defaults, or empty list [] to disable all exclusions",
    )

    model_config = ConfigDict(
        # Allow extra fields for future extensibility
        extra="forbid",
        # Validate assignment to catch errors early
        validate_assignment=True,
    )

    @field_validator("language")
    @classmethod
    def validate_language_if_provided(cls, v: str | None) -> str | None:
        """Validate language if provided (optional validation for supported languages)."""
        if v is not None:
            # Optionally validate against supported languages if we have a list
            # For now, just ensure it's not empty if provided
            if not v.strip():
                raise ValueError("Language must be a non-empty string if provided")
            return v.strip().lower()
        return v

    @field_validator("file_patterns")
    @classmethod
    def validate_file_patterns_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that file patterns list is not empty."""
        if not v:
            raise ValueError("file_patterns must not be empty")
        return v

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration containing:
                - path (str): Required. Path to source code file or directory.
                - language (str, optional): Programming language.
                - file_patterns (list[str], optional): File inclusion patterns.
                - max_file_size (int, optional): Maximum file size to process.
                - max_files (int, optional): Maximum number of files to process.
                - exclude_patterns (list[str], optional): Glob patterns to exclude.

        Returns:
            Validated configuration object

        Raises:
            ConnectorConfigError: If validation fails or required properties are missing

        """
        try:
            return cls.model_validate(properties)
        except ValidationError as e:
            # Extract specific error messages for better user experience
            for error in e.errors():
                if error["loc"] == ("path",):
                    msg = error.get("msg", "")
                    if "path property is required" in msg:
                        raise ConnectorConfigError("path property is required") from e
                    elif error["type"] == "missing":
                        raise ConnectorConfigError("path property is required") from e
            # Fall back to general error message
            raise ConnectorConfigError(
                f"Invalid source code connector configuration: {e}"
            ) from e
        except ValueError as e:
            raise ConnectorConfigError(
                f"Invalid source code connector configuration: {e}"
            ) from e
