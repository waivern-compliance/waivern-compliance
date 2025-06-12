import abc
from dataclasses import dataclass
from typing import TypeAlias

from waivern_analyser.connectors import ConnectorOutputSchema

RulesetInputSchema: TypeAlias = ConnectorOutputSchema


@dataclass(frozen=True, slots=True)
class RulesetOutputSchema:
    pass


class Ruleset(abc.ABC):
    @abc.abstractmethod
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema: ...
