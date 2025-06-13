from __future__ import annotations

import abc
from collections.abc import Iterator
from typing import Any

from typing_extensions import Self

from waivern_analyser.connectors import Finding


class Ruleset(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """The name of this ruleset."""

    @classmethod
    @abc.abstractmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Instantiate this ruleset from a dictionary of properties.

        The `properties` dictionary is the configuration for the ruleset
        as specified in the analyser configuration file.
        """

    @abc.abstractmethod
    def run(self, finding: Finding) -> Iterator[ReportItem]:
        """Run the ruleset on a finding and return the report items."""


class ReportItem(abc.ABC):
    """A report item from a ruleset.

    A report item is a single violation or proof of compliance found by a ruleset.
    """
