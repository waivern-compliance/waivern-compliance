from pathlib import Path
from typing import Annotated

import yaml
from annotated_types import MinLen
from pydantic import ValidationError
from typing_extensions import Self

from waivern_analyser.config.base import Config
from waivern_analyser.config.connector_config import ConnectorConfig
from waivern_analyser.config.plugins_config import PluginsConfig
from waivern_analyser.config.ruleset_config import RulesetConfig
from waivern_analyser.config.source_config import SourceConfig


class InvalidConfigFileError(ValueError):
    """Raised when the config file is invalid."""


class InvalidYamlConfigFileError(InvalidConfigFileError):
    """Raised when the config file is invalid YAML."""


class InvalidConfigFileSchemaError(InvalidConfigFileError):
    """Raised when the config file is invalid schema."""


class AnalyserConfig(Config):
    """Configuration for the Waivern analyser."""

    plugins: PluginsConfig = PluginsConfig()
    sources: Annotated[tuple[SourceConfig, ...], MinLen(1)]
    connectors: Annotated[tuple[ConnectorConfig, ...], MinLen(1)]
    rulesets: Annotated[tuple[RulesetConfig, ...], MinLen(1)]

    select_plugins: tuple[str, ...] | None = None
    exclude_plugins: tuple[str, ...] | None = None

    @classmethod
    def from_yaml_file(cls, path: Path) -> Self:
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
