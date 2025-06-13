from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typing_extensions import Self

from waivern_analyser.config.base import Config
from waivern_analyser.connectors import (
    Connection,
    Connector,
    NotConnectedWithReason,
    UnsupportedSourceType,
)
from waivern_analyser.rulesets import Finding
from waivern_analyser.sources import DirectorySource, FileSource, Source


@dataclass(frozen=True, slots=True)
class WordpressProjectConnector(Connector):
    """A connector for wordpress projects."""

    config: WordpressProjectConfig

    @classmethod
    def get_name(cls) -> str:
        return "wordpress"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(config=WordpressProjectConfig.model_validate(properties))

    def connect(
        self, source: Source
    ) -> Connection | NoWordpressProject | UnsupportedSourceType:
        match source:
            case DirectorySource(path=path):
                return WordpressProjectConnection.from_directory(path, self.config)
            case FileSource(path=path):
                return WordpressProjectConnection.from_file(path, self.config)
            case _:
                return UnsupportedSourceType(connector=self, source=source)


@dataclass(frozen=True, slots=True)
class WordpressProjectConnection(Connection):
    """A connection to a wordpress project."""

    root: Path
    config: WordpressProjectConfig

    @classmethod
    def from_file(
        cls,
        file: Path,
        config: WordpressProjectConfig,
    ) -> Self | NoWordpressProject:
        return cls.from_directory(file.parent, config)

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        config: WordpressProjectConfig,
    ) -> Self | NoWordpressProject:
        config_file = directory / config.config_file
        if not config_file.is_file():
            return NoWordpressProject(
                reason_=(
                    f"The directory {directory} does not contain a valid Wordpress project:"
                    f" the config file {config_file} was not found."
                )
            )

        core_files = tuple(directory / core_file for core_file in config.core_files)
        if not all(core_file.exists() for core_file in core_files):
            return NoWordpressProject(
                reason_=(
                    f"The directory {directory} does not contain a valid Wordpress project:"
                    f" the core files {core_files} were not found."
                )
            )

        return cls(root=directory, config=config)


class WordpressProjectConfig(Config):
    """A configuration for a wordpress project connector."""

    config_file: str = "wp-config.php"
    core_files: tuple[str, ...] = ("wp-load.php", "wp-login.php", "wp-admin")
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


class NoWordpressProject(NotConnectedWithReason):
    """A `NotConnected` instance indicating that no Wordpress projects were found at the given path."""


class WordpressFinding(Finding):
    pass
