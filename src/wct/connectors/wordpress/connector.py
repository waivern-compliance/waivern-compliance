from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from typing_extensions import Self, override

from wct.connectors.base import Connector, ConnectorConfigError


class WordpressConnector(Connector[dict[str, Any]]):
    """Extracts data from a WordPress site and transforms it to WCF schema format.

    This connector reads data from a WordPress site and transforms it into the WCF schema format.
    """

    @classmethod
    @override
    def get_name(cls) -> str:
        """The name of the connector."""

        return "wordpress"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        try:
            config = WordpressConnectorConfig.model_validate(properties)
        except ValidationError as e:
            raise ConnectorConfigError(
                f"Invalid connector configuration for {cls.get_name()}",
                properties,
                e,
            ) from e

        if not config.config_file.is_file():
            raise ConnectorConfigError(
                f"The directory {config.root} does not contain a valid WordPress project:"
                f" the config file {config.config_file} was not found."
            )

        missing_core_files = sorted(
            (core_file for core_file in config.core_files if not core_file.is_file()),
            key=lambda file: file.name,
        )

        if missing_core_files:
            raise ConnectorConfigError(
                f"The directory {config.root} does not contain a valid Wordpress project:"
                f" the core files {missing_core_files} were not found."
            )

        return cls()

    @override
    def extract(self) -> dict[str, Any]:
        """Extract data from the WordPress site and return in WCF schema format."""
        return {}

    @override
    def get_output_schema(self) -> type[dict[str, Any]]:
        """Return the schema this connector produces."""
        return dict[str, Any]


class WordpressConnectorConfig(BaseModel):
    root: Path
    config_file_name: str = "wp-config.php"
    core_file_names: tuple[str, ...] = (
        "wp-load.php",
        "wp-login.php",
        "wp-admin",
    )
    db_table_prefix: str = "wp_"
    db_core_tables: tuple[str, ...] = (
        "users",
        "usermeta",
        "posts",
        "postmeta",
        "comments",
        "commentmeta",
        "options",
        "terms",
        "termmeta",
    )

    @property
    def config_file(self) -> Path:
        return self.root / self.config_file_name

    @property
    def core_files(self) -> tuple[Path, ...]:
        return tuple(
            self.root / core_file_name for core_file_name in self.core_file_names
        )
