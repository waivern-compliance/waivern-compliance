"""Base classes and utilities for rulesets."""

import abc
import logging
from typing import Any

from wct.rulesets.types import Rule

logger = logging.getLogger(__name__)


class Ruleset(abc.ABC):
    """Base class for all rulesets with logging support.

    This provides a common interface for rulesets and automatic
    logger initialisation following WCT logging conventions.

    Each ruleset must define its canonical name via the name property.
    """

    def __init__(self) -> None:
        """Initialise the ruleset."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Get the canonical name of this ruleset.

        Returns:
            The fixed, canonical name for this ruleset type

        """

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Get the version of this ruleset.

        Returns:
            Version string in semantic versioning format (e.g., "1.0.0")

        """

    @abc.abstractmethod
    def get_rules(self) -> tuple[Rule, ...]:
        """Get the rules defined by this ruleset.

        Returns:
            Immutable tuple of Rule objects

        """


class RulesetError(Exception):
    """Base exception for ruleset-related errors."""

    pass


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

    pass


class RulesetAlreadyRegisteredError(RulesetError):
    """Raised when attempting to register a ruleset that already exists."""

    pass


class RulesetRegistry:
    """Singleton registry for ruleset classes with explicit registration."""

    _instance: "RulesetRegistry | None" = None
    _registry: dict[str, type[Ruleset]]

    def __new__(cls, *args: Any, **kwargs: Any) -> "RulesetRegistry":
        """Create or return the singleton instance of RulesetRegistry.

        This ensures only one instance of the registry exists throughout
        the application lifecycle.

        Returns:
            The singleton RulesetRegistry instance

        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
        return cls._instance

    def register(self, name: str, ruleset_class: type[Ruleset]) -> None:
        """Register a ruleset class with a name.

        Args:
            name: The name to register the ruleset under
            ruleset_class: The ruleset class to register

        Raises:
            RulesetAlreadyRegisteredError: If a ruleset with this name already exists

        """
        if name in self._registry:
            raise RulesetAlreadyRegisteredError(
                f"Ruleset '{name}' is already registered"
            )
        self._registry[name] = ruleset_class

    def get_ruleset_class(self, name: str) -> type[Ruleset]:
        """Get a registered ruleset class by name."""
        if name not in self._registry:
            raise RulesetNotFoundError(f"Ruleset {name} not registered")
        return self._registry[name]


class RulesetLoader:
    """Loads rulesets using singleton registry with explicit registration."""

    @classmethod
    def load_ruleset(cls, ruleset_name: str) -> tuple[Rule, ...]:
        """Load a ruleset using the singleton registry.

        Args:
            ruleset_name: Name of the ruleset (e.g., "personal_data")

        Returns:
            Immutable tuple of Rule objects

        """
        registry = RulesetRegistry()
        ruleset_class = registry.get_ruleset_class(ruleset_name)
        ruleset_instance = ruleset_class()
        return ruleset_instance.get_rules()
