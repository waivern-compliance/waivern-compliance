"""Configuration for FilesystemConnector."""

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

    # Validate the Path object
    if not path_obj.exists():
        raise ValueError(f"Path does not exist: {path_obj}")
    if not (path_obj.is_file() or path_obj.is_dir()):
        raise ValueError(f"Path must be a file or directory: {path_obj}")

    return path_obj


class FilesystemConnectorConfig(BaseModel):
    """Configuration for FilesystemConnector with Pydantic validation.

    This provides strong typing and validation for filesystem connector
    configuration parameters with sensible defaults.
    """

    path: Annotated[Path, BeforeValidator(_validate_path_required)] = Field(
        description="File or directory path to read from"
    )
    chunk_size: int = Field(
        default=8192,
        description="Size of chunks to read at a time",
        gt=0,
    )
    encoding: str = Field(
        default="utf-8",
        description="Text encoding to use when reading files",
    )
    errors: str = Field(
        default="strict",
        description="How to handle encoding errors (strict, replace, ignore)",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to exclude from processing",
    )
    max_files: int = Field(
        default=1000,
        description="Maximum number of files to process",
        gt=0,
    )

    model_config = ConfigDict(
        # Allow extra fields for future extensibility
        extra="forbid",
        # Validate assignment to catch errors early
        validate_assignment=True,
    )

    @field_validator("errors")
    @classmethod
    def validate_error_handling(cls, v: str) -> str:
        """Validate error handling strategy."""
        allowed = ["strict", "replace", "ignore"]
        if v not in allowed:
            raise ValueError(f"errors must be one of {allowed}, got: {v}")
        return v

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration

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
                f"Invalid filesystem connector configuration: {e}"
            ) from e
        except ValueError as e:
            raise ConnectorConfigError(
                f"Invalid filesystem connector configuration: {e}"
            ) from e
