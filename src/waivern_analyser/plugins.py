import abc
from collections.abc import Iterable

from waivern_analyser.connectors import Connector
from waivern_analyser.rulesets import Ruleset
from waivern_analyser.sources import Source


class Plugin(abc.ABC):
    """Base class for all plugins."""

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Get the name of the plugin.

        This is used to identify the plugin in the system.
        """

    @classmethod
    @abc.abstractmethod
    def get_sources(cls) -> Iterable[type[Source]]:
        """Get the new types of sources that this plugin defines."""

    @classmethod
    @abc.abstractmethod
    def get_connectors(cls) -> Iterable[type[Connector]]:
        """Get the new types of connectors that this plugin defines."""

    @classmethod
    @abc.abstractmethod
    def get_rulesets(cls) -> Iterable[type[Ruleset]]:
        """Get the new types of rulesets that this plugin defines."""
