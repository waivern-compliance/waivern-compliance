from __future__ import annotations

import abc
from collections.abc import Callable, Iterator
from typing import Any, TypeVar

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


def select_finding_types(
    finding_types: tuple[type[Finding], ...],
) -> Callable[
    [Callable[[_Ruleset, Finding], Iterator[ReportItem]]],
    Callable[[_Ruleset, Finding], Iterator[ReportItem]],
]:
    """A decorator for rulesets that selects the finding types they support.

    The decorator returns a new `run` method that only returns report items
    if the finding type is in the `finding_types` parameter; otherwise, it returns
    an empty iterator.

    Usage:
    ```python
    class MyRuleset(Ruleset):
        @select_finding_types(MyFinding, OtherFinding)
        # Any other finding type will return an empty iterator
        def run(self, finding: MyFinding | OtherFinding) -> Iterator[ReportItem]:
            ...
    ```
    """

    def decorator(
        run: Callable[[_Ruleset, Finding], Iterator[ReportItem]],
    ) -> Callable[[_Ruleset, Finding], Iterator[ReportItem]]:
        def new_run(
            self: _Ruleset,
            finding: Finding,
        ) -> Iterator[ReportItem]:
            if isinstance(finding, finding_types):
                return run(self, finding)
            return iter(())

        return new_run

    return decorator


_Ruleset = TypeVar("_Ruleset", bound=Ruleset)
