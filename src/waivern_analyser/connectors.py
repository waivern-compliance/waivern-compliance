from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from typing_extensions import Self

from waivern_analyser.sources import Source


class Connector(abc.ABC):
    """A connector is responsible for connecting to a source.

    A connector is responsible for opening a connection to a source.
    The connector can decide to not connect to the source (for instance,
    if the source is not supported by the connector).
    """

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """The name of the connector."""

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this connector from a dictionary of properties.

        The `properties` dictionary is the configuration for the connector
        as specified in the analyser configuration file.
        """

    @abc.abstractmethod
    def connect(self, source: Source) -> Connection | NotConnected:
        """Connect to the source.

        If the connector decides to not connect to the source, it should
        return a `NotConnected` instance.
        """


@dataclass(frozen=True, slots=True)
class Connection:
    """A connection to a source.

    A connection is responsible for managing the stream of data from a source.
    """

    @abc.abstractmethod
    def iter_findings(self) -> Iterator[Finding]:
        """Iterate over the findings in the connection."""


class Finding(abc.ABC):
    """A finding from a source.

    A finding is a single issue found in a source.
    """


class NotConnected(abc.ABC):
    """The connector decided to not connect to the source.

    This is a success case, and the user should be notified about the reason.

    This differs from the `ConnectorError` error case because it indicates
    that the connector decided to not connect to the source, instead of
    attempting but failing to connect.
    """

    @abc.abstractmethod
    def reason(self) -> str:
        """The reason why the connector decided to not connect."""


@dataclass(frozen=True, slots=True)
class NotConnectedWithReason(NotConnected):
    """The connector decided to not connect to the source with a reason."""

    reason_: str

    def reason(self) -> str:
        return self.reason_


@dataclass(frozen=True, slots=True)
class UnsupportedSourceType(NotConnected):
    """The connector does not support the source.

    This is a success case, and the user should be notified about the reason.
    """

    connector: Connector
    source: Source

    def reason(self) -> str:
        return f"The connector {self.connector} does not support the source type {self.source}."


class ConnectorError(Exception):
    """An error occurred while connecting to a source.

    This differs from the `NotConnected` success case because it indicates
    that the connector failed to connect to the source, and the user should
    be notified about the error.
    """
