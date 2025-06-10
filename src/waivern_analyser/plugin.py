import abc
from collections.abc import Iterable

from waivern_connectors_core.connector import Connector
from waivern_rulesets_core import Ruleset


class Plugin(abc.ABC):
    @classmethod
    def get_connectors(cls) -> Iterable[Connector]:
        return ()

    @classmethod
    def get_rulesets(cls) -> Iterable[Ruleset]:
        return ()
