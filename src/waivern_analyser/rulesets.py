import abc
from dataclasses import dataclass
from typing import Any, TypeAlias

from typing_extensions import Self

from waivern_analyser.connectors import Connection

RulesetInputSchema: TypeAlias = Connection


@dataclass(frozen=True, slots=True)
class RulesetOutputSchema:
    pass


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
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema: ...
