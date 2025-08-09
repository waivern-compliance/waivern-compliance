"""Base classes and utilities for rulesets."""

import abc
from typing import Any

from wct.logging import get_ruleset_logger
from wct.rulesets.types import Rule


class Ruleset(abc.ABC):
    """Base class for all rulesets with logging support.

    This provides a common interface for rulesets and automatic
    logger initialisation following WCT logging conventions.
    """

    def __init__(self, ruleset_name: str) -> None:
        """Initialize the ruleset with a configured logger.

        Args:
            ruleset_name: The name of the ruleset for logging purposes
        """
        self.ruleset_name = ruleset_name
        self.logger = get_ruleset_logger(ruleset_name)

    @abc.abstractmethod
    def get_rules(self) -> list[Rule]:
        """Get the rules defined by this ruleset.

        Returns:
            List of Rule objects
        """


class RulesetError(Exception):
    """Base exception for ruleset-related errors."""

    pass


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

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
        """Register a ruleset class with a name."""
        self._registry[name] = ruleset_class

    def get_ruleset_class(self, name: str) -> type[Ruleset]:
        """Get a registered ruleset class by name."""
        if name not in self._registry:
            raise RulesetNotFoundError(f"Ruleset {name} not registered")
        return self._registry[name]


class RulesetLoader:
    """Loads rulesets using singleton registry with explicit registration."""

    @classmethod
    def load_ruleset(cls, ruleset_name: str) -> list[Rule]:
        """Load a ruleset using the singleton registry.

        Args:
            ruleset_name: Name of the ruleset (e.g., "personal_data")

        Returns:
            List of Rule objects
        """
        registry = RulesetRegistry()
        ruleset_class = registry.get_ruleset_class(ruleset_name)
        ruleset_instance = ruleset_class(ruleset_name)
        return ruleset_instance.get_rules()
