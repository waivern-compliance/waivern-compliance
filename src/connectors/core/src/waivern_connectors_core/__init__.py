import abc
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectorInputSchema:
    pass


@dataclass(frozen=True, slots=True)
class ConnectorOutputSchema:
    pass


class Connector(abc.ABC):
    @abc.abstractmethod
    def run(self, input: ConnectorInputSchema) -> ConnectorOutputSchema: ...
