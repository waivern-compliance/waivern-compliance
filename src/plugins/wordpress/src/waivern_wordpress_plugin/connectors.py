from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from annotated_types import MinLen
from pydantic import BaseModel
from typing_extensions import Self, assert_never

from waivern_analyser.connectors import (
    Connection,
    Connector,
    NotConnected,
    UnsupportedSourceType,
)
from waivern_analyser.sources import PathsSource, Source


class WordpressProjectConnector(Connector):
    def get_name(self) -> str:
        return "wordpress-project-connector"

    def connect(
        self,
        source: Source,
    ) -> Connection | NoWordpressProject | UnsupportedSourceType:
        match source:
            case PathsSource(paths=paths):
                return WordpressMultipleProjectsConnection.from_paths(paths=paths)
            case _:
                return UnsupportedSourceType(source_type=type(source))


class WordpressProjectConnectorConfig(BaseModel):
    """A configuration for a wordpress project connector."""


@dataclass(frozen=True, slots=True)
class WordpressMultipleProjectsConnection(Connection):
    """A connection to multiple wordpress projects."""

    connections: Annotated[
        tuple[WordpressProjectConnection, ...],
        MinLen(1),
    ]

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> Self | NoWordpressProject:
        connections: list[WordpressProjectConnection] = []

        for path in paths:
            match WordpressProjectConnection.from_path(path):
                case WordpressProjectConnection() as connection:
                    connections.append(connection)
                case NoWordpressProject():
                    continue
                case never:
                    assert_never(never)

        if not connections:
            return NoWordpressProject()

        return cls(connections=tuple(connections))


@dataclass(frozen=True, slots=True)
class WordpressProjectConnection(Connection):
    """A connection to a wordpress project."""

    path: Path

    @classmethod
    def from_path(cls, path: Path) -> Self | NoWordpressProject:
        if not (path.is_dir() and (path / "wp-config.php").exists()):
            return NoWordpressProject()

        return cls(path=path)

    @classmethod
    def _from_directory(cls, directory: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject()

    @classmethod
    def _from_file(cls, file: Path) -> Self | NoWordpressProject:
        # TODO: Implement
        return NoWordpressProject()


class NoWordpressProject(NotConnected):
    """A `NotConnected` instance indicating that no Wordpress projects were found at the given path."""

    def reason(self) -> str:
        return "No Wordpress project was found at the given path."
