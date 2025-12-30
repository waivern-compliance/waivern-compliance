"""Ruleset management utility for analysers."""

import logging
from dataclasses import dataclass
from typing import Any, override

from waivern_core import BaseRule, RulesetError
from waivern_rulesets import RulesetLoader

logger = logging.getLogger(__name__)


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
                f"Expected format: provider/name/version (e.g., 'local/personal_data/1.0.0')"
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


class RulesetManager:
    """Utility for loading rulesets with URI support, type safety, and caching.

    Supports URI format: {provider}/{name}/{version}

    Currently supported providers:
        - local: Loads from bundled waivern-rulesets package

    """

    _cache: dict[str, tuple[Any, ...]] = {}

    # Supported providers - extend this as new providers are added
    _SUPPORTED_PROVIDERS = {"local"}

    @classmethod
    def get_rules[T: BaseRule](
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> tuple[T, ...]:
        """Get rules from ruleset using URI with type safety and caching.

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation

        Returns:
            Tuple of rule objects loaded from the ruleset

        Raises:
            RulesetURIParseError: If URI format is invalid
            UnsupportedProviderError: If provider is not supported

        """
        # Parse the URI
        uri = RulesetURI.parse(ruleset_uri)

        # Validate provider
        if uri.provider not in cls._SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                f"Unsupported ruleset provider: '{uri.provider}'. "
                f"Supported providers: {', '.join(sorted(cls._SUPPORTED_PROVIDERS))}"
            )

        # Use full URI as cache key to distinguish versions
        cache_key = f"{ruleset_uri}:{rule_type.__name__}"

        if cache_key not in cls._cache:
            logger.debug(f"Loading ruleset: {ruleset_uri} (type: {rule_type.__name__})")
            # For 'local' provider, use RulesetLoader with just the name
            rules = RulesetLoader.load_ruleset(uri.name, rule_type)
            cls._cache[cache_key] = rules
        else:
            logger.debug(
                f"Using cached ruleset: {ruleset_uri} (type: {rule_type.__name__})"
            )

        return cls._cache[cache_key]  # type: ignore[return-value]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the ruleset cache."""
        cls._cache.clear()
        logger.debug("Ruleset cache cleared")
