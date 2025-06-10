import abc
from collections.abc import Iterable

from waivern_connectors_core.output_schema import ConnectorOutputSchema
from waivern_connectors_core.source import Source


class Connector(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str: ...

    @classmethod
    @abc.abstractmethod
    def get_source_types(cls) -> Iterable[type[Source]]: ...

    @abc.abstractmethod
    def run(self, source: Source) -> ConnectorOutputSchema: ...
