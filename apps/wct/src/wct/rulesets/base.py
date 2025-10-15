"""Base classes and utilities for rulesets."""

import abc
import logging
from typing import Any, override

from waivern_core import BaseRuleset, RulesetError

from wct.rulesets.types import BaseRule

logger = logging.getLogger(__name__)


class AbstractRuleset[RuleType: BaseRule](BaseRuleset):
    """WCT-specific ruleset implementation with Pydantic rule types.

    This extends the framework-level BaseRuleset with WCT-specific features:
    - Strongly typed rules using Pydantic BaseRule models
    - Type-safe generic parameter for specific rule types
    - Logging support following WCT conventions

    Each ruleset must define its canonical name via the name property.
    """

    @property
    @abc.abstractmethod
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset.

        Returns:
            The fixed, canonical name for this ruleset type

        """

    @property
    @abc.abstractmethod
    @override
    def version(self) -> str:
        """Get the version of this ruleset.

        Returns:
            Version string in semantic versioning format (e.g., "1.0.0")

        """

    @abc.abstractmethod
    @override
    def get_rules(self) -> tuple[RuleType, ...]:
        """Get the rules defined by this ruleset.

        Returns:
            Immutable tuple of RuleType objects

        """


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

    pass


class RulesetAlreadyRegisteredError(RulesetError):
    """Raised when attempting to register a ruleset that already exists."""

    pass


class RulesetRegistry:
    """Type-aware singleton registry for ruleset classes with explicit registration."""

    _instance: "RulesetRegistry | None" = None
    _registry: dict[str, type[AbstractRuleset[Any]]]
    _type_mapping: dict[str, type[BaseRule]]

    def __new__(cls, *args: Any, **kwargs: Any) -> "RulesetRegistry":  # noqa: ANN401  # Singleton pattern requires flexible constructor arguments
        """Create or return the singleton instance of RulesetRegistry.

        This ensures only one instance of the registry exists throughout
        the application lifecycle.

        Returns:
            The singleton RulesetRegistry instance

        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
            cls._instance._type_mapping = {}
        return cls._instance

    def register[T: BaseRule](
        self, name: str, ruleset_class: type[AbstractRuleset[T]], rule_type: type[T]
    ) -> None:
        """Register a ruleset class with its rule type.

        Args:
            name: The name to register the ruleset under
            ruleset_class: The ruleset class to register
            rule_type: The specific rule type this ruleset returns

        Raises:
            RulesetAlreadyRegisteredError: If a ruleset with this name already exists

        """
        if name in self._registry:
            raise RulesetAlreadyRegisteredError(
                f"Ruleset '{name}' is already registered"
            )
        self._registry[name] = ruleset_class
        self._type_mapping[name] = rule_type

    def get_ruleset_class[T: BaseRule](
        self, name: str, expected_rule_type: type[T]
    ) -> type[AbstractRuleset[T]]:
        """Get a registered ruleset class with type validation.

        Args:
            name: The name of the ruleset to retrieve
            expected_rule_type: The expected rule type for validation

        Returns:
            The ruleset class with proper typing

        Raises:
            RulesetNotFoundError: If the ruleset is not registered
            TypeError: If the expected type doesn't match the registered type

        """
        if name not in self._registry:
            raise RulesetNotFoundError(f"Ruleset {name} not registered")

        # Runtime type validation
        actual_rule_type = self._type_mapping[name]
        if actual_rule_type != expected_rule_type:
            raise TypeError(
                f"Ruleset '{name}' returns {actual_rule_type.__name__}, "
                f"but {expected_rule_type.__name__} was expected"
            )

        # Type checker now knows this returns Ruleset[T]
        # The registry stores the exact type we validated above
        ruleset_class = self._registry[name]
        return ruleset_class

    def clear(self) -> None:
        """Clear all registered rulesets."""
        self._registry.clear()
        self._type_mapping.clear()


class RulesetLoader:
    """Loads rulesets using singleton registry with explicit registration."""

    @classmethod
    def load_ruleset[T: BaseRule](
        cls, ruleset_name: str, rule_type: type[T]
    ) -> tuple[T, ...]:
        """Load a ruleset using the singleton registry with proper typing.

        Args:
            ruleset_name: Name of the ruleset (e.g., "processing_purposes")
            rule_type: The expected rule type for validation and typing

        Returns:
            Immutable tuple of T objects where T is the specific rule type

        Example:
            rules = RulesetLoader.load_ruleset("processing_purposes", ProcessingPurposeRule)

        """
        registry = RulesetRegistry()
        ruleset_class = registry.get_ruleset_class(ruleset_name, rule_type)
        ruleset_instance = ruleset_class()
        return ruleset_instance.get_rules()
