import abc
from collections.abc import Sequence
from dataclasses import dataclass

from waivern_connectors_core.output_schema import ConnectorOutputSchema


@dataclass(frozen=True, slots=True)
class ConnectorInputSchema:
    pass


class Connector(abc.ABC):
    @abc.abstractmethod
    def run(self, input: ConnectorInputSchema) -> ConnectorOutputSchema: ...


@dataclass(frozen=True, slots=True)
class ConnectorCollection:
    connectors: Sequence[Connector]
