"""Base classes and utilities for rulesets."""

import abc
import logging
import threading
from dataclasses import dataclass
from typing import Any, ClassVar, TypedDict, override

from waivern_core import BaseRuleset, Rule, RulesetError

logger = logging.getLogger(__name__)


# =============================================================================
# Ruleset URI Types
# =============================================================================


class RulesetURIParseError(RulesetError):
    """Raised when a ruleset URI cannot be parsed."""

    pass


class UnsupportedProviderError(RulesetError):
    """Raised when a ruleset provider is not supported."""

    pass


@dataclass(frozen=True)
class RulesetURI:
    """Parsed ruleset URI with provider, name, and version components.

    URI format: {provider}/{name}/{version}

    Examples:
        - local/personal_data/1.0.0
        - local/processing_purposes/2.1.0

    Providers:
        - local: Bundled rulesets from waivern-rulesets package
        - (future): Remote providers for third-party rulesets

    """

    # Number of expected URI parts: provider/name/version
    _EXPECTED_PARTS = 3

    provider: str
    name: str
    version: str

    @classmethod
    def parse(cls, uri: str) -> "RulesetURI":
        """Parse a ruleset URI string into components.

        Args:
            uri: URI in format {provider}/{name}/{version}

        Returns:
            RulesetURI with parsed components

        Raises:
            RulesetURIParseError: If URI format is invalid

        """
        parts = uri.split("/")

        if len(parts) != cls._EXPECTED_PARTS:
            raise RulesetURIParseError(
                f"Invalid ruleset URI format: '{uri}'. "
                f"Expected format: provider/name/version "
                f"(e.g., 'local/personal_data/1.0.0')"
            )

        provider, name, version = parts

        if not provider or not name or not version:
            raise RulesetURIParseError(
                f"Invalid ruleset URI format: '{uri}'. "
                f"Provider, name, and version cannot be empty."
            )

        return cls(provider=provider, name=name, version=version)

    @override
    def __str__(self) -> str:
        """Return the URI string representation."""
        return f"{self.provider}/{self.name}/{self.version}"


class AbstractRuleset[RuleType: Rule](BaseRuleset):
    """WCT-specific ruleset implementation with Pydantic rule types.

    This extends the framework-level BaseRuleset with WCT-specific features:
    - Strongly typed rules using Pydantic Rule models
    - Type-safe generic parameter for specific rule types
    - Logging support following WCT conventions

    Each ruleset must define:
    - ruleset_name: ClassVar[str] - canonical name for registry
    - ruleset_version: ClassVar[str] - semantic version string
    - name property - returns ruleset_name (for instance access)
    - version property - returns ruleset_version (for instance access)
    """

    # ClassVars for registry registration (accessible at class level)
    ruleset_name: ClassVar[str]
    ruleset_version: ClassVar[str]

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


class RulesetLoader:
    """Loads rulesets using URI format with provider support.

    Supports URI format: {provider}/{name}/{version}

    Currently supported providers:
        - local: Loads from bundled waivern-rulesets package

    """

    # Supported providers - extend this as new providers are added
    _SUPPORTED_PROVIDERS = {"local"}

    @classmethod
    def load_ruleset[T: Rule](
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> tuple[T, ...]:
        """Load a ruleset using URI format with provider validation.

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation and typing

        Returns:
            Immutable tuple of T objects where T is the specific rule type

        Raises:
            RulesetURIParseError: If URI format is invalid
            UnsupportedProviderError: If provider is not supported
            RulesetNotFoundError: If ruleset is not registered

        Example:
            rules = RulesetLoader.load_ruleset(
                "local/processing_purposes/1.0.0",
                ProcessingPurposeRule
            )

        """
        # Parse the URI
        uri = RulesetURI.parse(ruleset_uri)

        # Validate provider
        if uri.provider not in cls._SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                f"Unsupported ruleset provider: '{uri.provider}'. "
                f"Supported providers: {', '.join(sorted(cls._SUPPORTED_PROVIDERS))}"
            )

        # For 'local' provider, use the registry with the ruleset name
        logger.debug(f"Loading ruleset: {ruleset_uri} (type: {rule_type.__name__})")
        ruleset_instance = cls.load_ruleset_instance(ruleset_uri, rule_type)
        return ruleset_instance.get_rules()

    @classmethod
    def load_ruleset_instance[T: Rule](
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> AbstractRuleset[T]:
        """Load a ruleset instance using URI format with provider validation.

        Unlike load_ruleset() which returns only the rules, this method returns
        the full ruleset instance, allowing access to all ruleset methods
        (e.g., get_rules(), get_risk_modifiers(), name, version).

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation and typing

        Returns:
            The ruleset instance with full access to all methods

        Raises:
            RulesetURIParseError: If URI format is invalid
            UnsupportedProviderError: If provider is not supported
            RulesetNotFoundError: If ruleset is not registered

        Example:
            ruleset = RulesetLoader.load_ruleset_instance(
                "local/gdpr_data_subject_classification/1.0.0",
                GDPRDataSubjectClassificationRule
            )
            rules = ruleset.get_rules()
            risk_modifiers = ruleset.get_risk_modifiers()

        """
        # Parse the URI
        uri = RulesetURI.parse(ruleset_uri)

        # Validate provider
        if uri.provider not in cls._SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                f"Unsupported ruleset provider: '{uri.provider}'. "
                f"Supported providers: {', '.join(sorted(cls._SUPPORTED_PROVIDERS))}"
            )

        # For 'local' provider, use the registry with the ruleset name and version
        registry = RulesetRegistry()
        ruleset_class = registry.get_ruleset_class(uri.name, uri.version, rule_type)
        return ruleset_class()
