import abc
from collections.abc import Iterable
from dataclasses import dataclass

from waivern_analyser.sources import Source


@dataclass(frozen=True, slots=True)
class ConnectorOutputSchema:
    pass


class Connector(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str: ...

    @classmethod
    @abc.abstractmethod
    def get_source_types(cls) -> Iterable[type[Source]]: ...

    @abc.abstractmethod
    def run(self, source: Source) -> ConnectorOutputSchema: ...
