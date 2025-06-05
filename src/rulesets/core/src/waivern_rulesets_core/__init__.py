import abc
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RulesetInputSchema:
    pass


@dataclass(frozen=True, slots=True)
class RulesetOutputSchema:
    pass


class Ruleset(abc.ABC):
    @abc.abstractmethod
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema: ...
