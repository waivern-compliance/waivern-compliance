from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from typing_extensions import Self

from waivern_analyser.connectors import (
    Connection,
    Connector,
    NotConnectedWithReason,
    UnsupportedSourceType,
)
from waivern_analyser.sources import DirectorySource, FileSource, Source


@dataclass(frozen=True, slots=True)
class WordpressProjectConnector(Connector):
    """A connector for wordpress projects."""

    config: WordpressProjectConnectorConfig

    @classmethod
    def get_name(cls) -> str:
        return "wordpress-project-connector"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(config=WordpressProjectConnectorConfig.model_validate(properties))

    def connect(
        self, source: Source
    ) -> Connection | NoWordpressProject | UnsupportedSourceType:
        match source:
            case DirectorySource(path=path):
                return WordpressProjectConnection.from_directory(path)
            case FileSource(path=path):
                return WordpressProjectConnection.from_file(path)
            case _:
                return UnsupportedSourceType(connector=self, source=source)


class WordpressProjectConnectorConfig(BaseModel):
    """A configuration for a wordpress project connector."""

    config_file: str = "wp-config.php"
    core_files: tuple[str, ...] = ("wp-load.php", "wp-login.php", "wp-admin")
    table_prefix: str = "wp_"
    core_tables: tuple[str, ...] = (
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


@dataclass(frozen=True, slots=True)
class WordpressProjectConnection(Connection):
    """A connection to a wordpress project."""

    path: Path

    @classmethod
    def from_file(cls, file: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject(
            reason_=f"The file {file} is not a valid Wordpress configuration file."
        )

    @classmethod
    def from_directory(cls, directory: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject(
            reason_=f"The directory {directory} does not contain a valid Wordpress project."
        )


class NoWordpressProject(NotConnectedWithReason):
    """A `NotConnected` instance indicating that no Wordpress projects were found at the given path."""
