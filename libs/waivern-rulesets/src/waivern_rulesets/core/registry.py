"""Ruleset registry for managing registered ruleset classes."""

import logging
import threading
from importlib.metadata import entry_points
from typing import Any, ClassVar, TypedDict, get_args

from waivern_core import Rule

from waivern_rulesets.core.base import AbstractRuleset
from waivern_rulesets.core.exceptions import RulesetNotFoundError

logger = logging.getLogger(__name__)


def extract_rule_type(ruleset_class: type[AbstractRuleset[Any]]) -> type[Rule]:
    """Extract the Rule type from a ruleset class's generic parameter.

    Uses Python's __orig_bases__ to find the generic parameter from the
    class hierarchy (e.g., YAMLRuleset[PersonalDataIndicatorRule]).

    Args:
        ruleset_class: A ruleset class that inherits from AbstractRuleset[T]

    Returns:
        The Rule subclass used as the generic parameter

    Raises:
        ValueError: If the rule type cannot be extracted from the class

    """
    for base in getattr(ruleset_class, "__orig_bases__", ()):
        args = get_args(base)
        if args and isinstance(args[0], type) and issubclass(args[0], Rule):
            return args[0]

    raise ValueError(
        f"Cannot extract rule type from {ruleset_class.__name__}. "
        "Class must inherit from AbstractRuleset[T] where T is a Rule subclass."
    )


class RulesetRegistryState(TypedDict):
    """State snapshot for RulesetRegistry.

    Used for test isolation - captures and restores registry state
    to prevent test pollution.
    """

    registry: dict[tuple[str, str], type[AbstractRuleset[Any]]]
    type_mapping: dict[tuple[str, str], type[Rule]]


class RulesetRegistry:
    """Type-aware singleton registry for ruleset classes with explicit registration."""

    _lock: ClassVar[threading.Lock] = threading.Lock()
    _instance: "RulesetRegistry | None" = None
    _registry: dict[tuple[str, str], type[AbstractRuleset[Any]]]
    _type_mapping: dict[tuple[str, str], type[Rule]]

    def __new__(cls, *args: Any, **kwargs: Any) -> "RulesetRegistry":  # noqa: ANN401  # Singleton pattern requires flexible constructor arguments
        """Create or return the singleton instance of RulesetRegistry.

        Uses double-checked locking pattern for thread-safe lazy initialization.
        This ensures only one instance of the registry exists throughout
        the application lifecycle, even under concurrent access.

        Returns:
            The singleton RulesetRegistry instance

        """
        if cls._instance is None:
            with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._registry = {}
                    cls._instance._type_mapping = {}
        return cls._instance

    def register[T: Rule](
        self, ruleset_class: type[AbstractRuleset[T]], rule_type: type[T]
    ) -> None:
        """Register a ruleset class with its rule type.

        Extracts name and version from the ruleset class's ClassVars:
        - ruleset_name: ClassVar[str]
        - ruleset_version: ClassVar[str]

        Registration is idempotent - duplicate registrations are silently ignored.
        This is safer for module imports that may run multiple times.

        Args:
            ruleset_class: The ruleset class to register (must have ruleset_name
                and ruleset_version ClassVars)
            rule_type: The specific rule type this ruleset returns

        Raises:
            ValueError: If ruleset_class is missing required ClassVars

        """
        # Extract name and version from ClassVars
        name = getattr(ruleset_class, "ruleset_name", None)
        version = getattr(ruleset_class, "ruleset_version", None)

        if name is None:
            raise ValueError(
                f"Ruleset class {ruleset_class.__name__} must define "
                "'ruleset_name' ClassVar"
            )
        if version is None:
            raise ValueError(
                f"Ruleset class {ruleset_class.__name__} must define "
                "'ruleset_version' ClassVar"
            )

        key = (name, version)
        if key in self._registry:
            # Idempotent: silently ignore duplicate registration
            # This is safer for module imports that may run multiple times
            return
        self._registry[key] = ruleset_class
        self._type_mapping[key] = rule_type

    def get_ruleset_class[T: Rule](
        self, name: str, version: str, expected_rule_type: type[T]
    ) -> type[AbstractRuleset[T]]:
        """Get a registered ruleset class with type validation.

        Args:
            name: The name of the ruleset to retrieve
            version: The version of the ruleset to retrieve
            expected_rule_type: The expected rule type for validation

        Returns:
            The ruleset class with proper typing

        Raises:
            RulesetNotFoundError: If the ruleset name+version is not registered
            TypeError: If the expected type doesn't match the registered type

        """
        key = (name, version)
        if key not in self._registry:
            available = self.get_available_versions(name)
            if available:
                raise RulesetNotFoundError(
                    f"Ruleset '{name}' version '{version}' not registered. "
                    f"Available versions: {', '.join(available)}"
                )
            raise RulesetNotFoundError(
                f"Ruleset '{name}' not registered (no versions available)"
            )

        # Runtime type validation
        actual_rule_type = self._type_mapping[key]
        if actual_rule_type != expected_rule_type:
            raise TypeError(
                f"Ruleset '{name}' returns {actual_rule_type.__name__}, "
                f"but {expected_rule_type.__name__} was expected"
            )

        # Type checker now knows this returns Ruleset[T]
        # The registry stores the exact type we validated above
        ruleset_class = self._registry[key]
        return ruleset_class

    def clear(self) -> None:
        """Clear all registered rulesets."""
        self._registry.clear()
        self._type_mapping.clear()

    def is_empty(self) -> bool:
        """Check if the registry has no registered rulesets.

        Returns:
            True if no rulesets are registered, False otherwise.

        """
        return len(self._registry) == 0

    def is_registered(self, name: str, version: str) -> bool:
        """Check if a ruleset is registered under the given name and version.

        Args:
            name: The name to check.
            version: The version to check.

        Returns:
            True if a ruleset is registered for this name+version, False otherwise.

        """
        return (name, version) in self._registry

    def get_available_versions(self, name: str) -> tuple[str, ...]:
        """Get all registered versions for a ruleset name.

        Args:
            name: The ruleset name to query.

        Returns:
            Tuple of version strings registered for this name (may be empty).

        """
        return tuple(version for (n, version) in self._registry.keys() if n == name)

    def list_registered(self) -> list[tuple[str, str, type[Rule]]]:
        """List all registered rulesets with their metadata.

        Returns:
            List of (name, version, rule_type) tuples for all registered rulesets,
            sorted alphabetically by name then version.

        """
        result = [
            (name, version, self._type_mapping[(name, version)])
            for name, version in self._registry.keys()
        ]
        return sorted(result, key=lambda x: (x[0], x[1]))

    def discover_from_entry_points(self, group: str = "waivern.rulesets") -> None:
        """Discover and register rulesets from entry points.

        Loads all entry points in the specified group, extracts the rule type
        from each ruleset class's generic parameter, and registers them.

        Args:
            group: The entry point group to discover from.
                   Defaults to "waivern.rulesets".

        """
        for ep in entry_points(group=group):
            try:
                ruleset_class = ep.load()
                rule_type = extract_rule_type(ruleset_class)
                self.register(ruleset_class, rule_type)
                logger.debug(
                    "Discovered ruleset '%s' from entry point '%s'",
                    getattr(ruleset_class, "ruleset_name", "unknown"),
                    ep.name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to load ruleset from entry point '%s': %s", ep.name, e
                )

    @classmethod
    def snapshot_state(cls) -> RulesetRegistryState:
        """Capture current RulesetRegistry state for later restoration.

        This is primarily used for test isolation - save state before tests,
        restore after tests to prevent global state pollution.

        Returns:
            State dictionary containing all mutable registry state

        """
        instance = cls()
        return {
            "registry": instance._registry.copy(),
            "type_mapping": instance._type_mapping.copy(),
        }

    @classmethod
    def restore_state(cls, state: RulesetRegistryState) -> None:
        """Restore RulesetRegistry state from a previously captured snapshot.

        This is primarily used for test isolation - restore state after tests
        to ensure tests don't pollute global state.

        Args:
            state: State dictionary from snapshot_state()

        """
        instance = cls()
        instance._registry = state["registry"].copy()
        instance._type_mapping = state["type_mapping"].copy()
