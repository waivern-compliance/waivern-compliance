from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from typing_extensions import Self

from waivern_analyser.connectors import (
    Connection,
    Connector,
    NotConnected,
    UnsupportedSourceType,
)
from waivern_analyser.sources import DirectorySource, FileSource, Source


class WordpressProjectConnector(Connector):
    """A connector for wordpress projects."""

    @classmethod
    def get_name(cls) -> str:
        return "wordpress-project-connector"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls()

    def connect(
        self,
        source: Source,
    ) -> Connection | NoWordpressProject | UnsupportedSourceType:
        match source:
            case DirectorySource(path=path):
                return WordpressProjectConnection.from_directory(path)
            case FileSource(path=path):
                return WordpressProjectConnection.from_file(path)
            case _:
                return UnsupportedSourceType(source_type=type(source))


class WordpressProjectConnectorConfig(BaseModel):
    """A configuration for a wordpress project connector."""


@dataclass(frozen=True, slots=True)
class WordpressProjectConnection(Connection):
    """A connection to a wordpress project."""

    path: Path

    @classmethod
    def from_file(cls, file: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject()

    @classmethod
    def from_directory(cls, directory: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject()


class NoWordpressProject(NotConnected):
    """A `NotConnected` instance indicating that no Wordpress projects were found at the given path."""

    def reason(self) -> str:
        return "No Wordpress project was found at the given path."
