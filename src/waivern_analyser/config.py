from collections import Counter
from pathlib import Path

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from waivern_analyser._plugins import PluginRegistry
from waivern_analyser._plugins import load_plugins as _load_plugins


class InvalidConfigFileError(ValueError):
    """Raised when the config file is invalid."""


class InvalidYamlConfigFileError(InvalidConfigFileError):
    """Raised when the config file is invalid YAML."""


class InvalidConfigFileSchemaError(InvalidConfigFileError):
    """Raised when the config file is invalid schema."""


class Config(BaseModel):
    """Configuration for the Waivern analyser."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    select_plugins: tuple[str, ...] | None = None
    exclude_plugins: tuple[str, ...] | None = None

    @field_validator("select_plugins", "exclude_plugins", mode="after")
    def validate_unique_plugins(
        cls,
        v: tuple[str, ...] | None,
        info: ValidationInfo,
    ) -> tuple[str, ...] | None:
        if v is not None:
            counter = Counter(v)
            if repeated := sorted(
                plugin for plugin, count in counter.items() if count > 1
            ):
                raise ValueError(
                    f"The following plugins are repeated in {info.field_name!r}:"
                    f" {sorted(repeated)}."
                    " Please remove the duplicates."
                )

        return v

    @model_validator(mode="after")
    def validate_select_and_exclude_plugins(self) -> Self:
        if self.select_plugins and self.exclude_plugins:
            raise ValueError(
                "`select_plugins` and `exclude_plugins` are mutually exclusive"
            )
        return self

    @classmethod
    def default(cls) -> Self:
        return cls()

    @classmethod
    def from_file(cls, path: Path) -> Self:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidYamlConfigFileError(
                f"Error loading YAML config file {path}: {e}"
            ) from e
        except Exception as e:
            raise InvalidConfigFileError(
                f"Error loading config file {path}: {e}"
            ) from e

        if data is None:
            return cls.default()

        if not isinstance(data, dict):
            raise InvalidConfigFileSchemaError(
                f"Config file {path} must be a mapping, but got {type(data)}"
            )

        try:
            return cls(**data)
        except ValidationError as e:
            raise InvalidConfigFileSchemaError(
                f"Error validating config file {path}: {e}"
            ) from e
        except Exception as e:
            raise InvalidConfigFileSchemaError(
                f"Error parsing config file {path}: {e}"
            ) from e

    def load_plugins(self) -> PluginRegistry:
        # The type-ignore comments are necessary because `_load_plugins`
        # does not accept both `select` and `exclude` at the same time.
        # And we are not passing both, because the `validate_select_and_exclude_plugins`
        # validator ensures that at least one of them is `None`.
        # But of course, the type-checker does not know that, so we need to
        # suppress the type-checker warnings.
        return _load_plugins(
            select=self.select_plugins,  # type: ignore
            exclude=self.exclude_plugins,  # type: ignore
        )  # type: ignore
