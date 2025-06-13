import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typing_extensions import Self


class Source(abc.ABC):
    """A source of information to be consumed by connectors."""

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """The name of this source."""

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this source from a dictionary of properties.

        The `properties` dictionary is the configuration for the source
        as specified in the analyser configuration file.
        """


@dataclass(frozen=True, slots=True)
class FileSource(Source):
    """A source of information from a file."""

    path: Path

    @classmethod
    def get_name(cls) -> str:
        return "file"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(path=properties["path"])


@dataclass(frozen=True, slots=True)
class DirectorySource(Source):
    """A source of information from a directory."""

    path: Path

    @classmethod
    def get_name(cls) -> str:
        return "dir"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(path=properties["path"])
