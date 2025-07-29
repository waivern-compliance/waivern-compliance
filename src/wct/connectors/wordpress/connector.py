"""WordPress connector for the Waivern Compliance Tool."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from typing_extensions import Self, override

from wct.connectors.base import Connector, ConnectorConfigError
from wct.message import Message
from wct.schema import WctSchema

SUPPORTED_OUTPUT_SCHEMAS = {
    "wordpress_site": WctSchema(name="wordpress_site", type=dict[str, Any]),
}


class WordpressConnector(Connector):
    """Extracts data from a WordPress site and transforms it to WCF schema format.

    This connector reads data from a WordPress site and transforms it into the WCF schema format.
    """

    def __init__(self) -> None:
        """Initialize the WordPress connector with logging support."""
        super().__init__()  # Initialize logger from base class

    @classmethod
    @override
    def get_name(cls) -> str:
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
    def extract(
        self, output_schema: WctSchema[dict[str, Any]] | None = None
    ) -> Message:
        """Extract data from the WordPress site and return in WCF schema format.

        Args:
            output_schema: WCT schema for data validation

        Returns:
            Message containing extracted data in WCF schema format
        """
        # Check if a supported schema is provided
        if output_schema and output_schema.name not in SUPPORTED_OUTPUT_SCHEMAS:
            raise ConnectorConfigError(
                f"Unsupported output schema: {output_schema.name}. Supported schemas: {list(SUPPORTED_OUTPUT_SCHEMAS.keys())}"
            )

        if not output_schema:
            raise ConnectorConfigError(
                "No schema provided for data extraction. Please specify a valid WCT schema."
            )

        # Extract WordPress data (placeholder implementation)
        extracted_data = self._transform_for_wordpress_schema(output_schema)

        # Create and validate message
        message = Message(
            id="WordPress site data",
            content=extracted_data,
            schema=output_schema,
        )

        message.validate()

        return message

    def _transform_for_wordpress_schema(
        self, schema: WctSchema[dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform WordPress data for the 'wordpress_site' schema.

        Args:
            schema: The wordpress_site schema

        Returns:
            WordPress schema compliant content
        """
        return schema.type(
            name=schema.name,
            description="WordPress site data",
            source="WordPress installation",
            site_info={
                "config_detected": True,
                "core_files_present": True,
            },
            metadata={
                "tables_prefix": "wp_",
                "core_tables": [
                    "users",
                    "usermeta",
                    "posts",
                    "postmeta",
                    "comments",
                    "commentmeta",
                    "options",
                    "terms",
                    "termmeta",
                ],
            },
        )


class WordpressConnectorConfig(BaseModel):
    """Configuration for the WordPress connector."""

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
        """Get the path to the WordPress config file."""
        return self.root / self.config_file_name

    @property
    def core_files(self) -> tuple[Path, ...]:
        """Get the paths to the WordPress core files."""
        return tuple(
            self.root / core_file_name for core_file_name in self.core_file_names
        )
