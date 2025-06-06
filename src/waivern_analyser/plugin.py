import abc
from collections.abc import Iterable, Iterator

from waivern_connectors_core import Connector
from waivern_rulesets_core import Ruleset


class Plugin(abc.ABC):
    @classmethod
    def get_connectors(cls) -> Iterable[Connector] | Iterator[Connector]:
        return ()

    @classmethod
    def get_rulesets(cls) -> Iterable[Ruleset] | Iterator[Ruleset]:
        return ()
