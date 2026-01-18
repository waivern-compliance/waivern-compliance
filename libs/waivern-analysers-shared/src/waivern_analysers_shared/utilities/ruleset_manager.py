"""Ruleset management utility for analysers."""

import logging
from typing import Any

from waivern_core import Rule
from waivern_rulesets import (
    AbstractRuleset,
    RulesetLoader,
    RulesetURI,
    RulesetURIParseError,
    UnsupportedProviderError,
)

# Re-export for backward compatibility
__all__ = [
    "RulesetManager",
    "RulesetURI",
    "RulesetURIParseError",
    "UnsupportedProviderError",
]

logger = logging.getLogger(__name__)


class RulesetManager:
    """Caching layer for RulesetLoader with type safety.

    Provides caching on top of RulesetLoader to avoid reloading
    the same ruleset multiple times during analysis. Caches full
    ruleset instances, allowing access to all ruleset methods.

    Supports URI format: {provider}/{name}/{version}

    Currently supported providers:
        - local: Loads from bundled waivern-rulesets package

    """

    _cache: dict[str, AbstractRuleset[Any]] = {}

    @classmethod
    def get_ruleset[T: Rule](
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> AbstractRuleset[T]:
        """Get a cached ruleset instance using URI with type safety.

        Returns the full ruleset instance, allowing access to all methods
        (e.g., get_rules(), get_risk_modifiers(), name, version).

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation

        Returns:
            Cached ruleset instance with full access to all methods

        Raises:
            RulesetURIParseError: If URI format is invalid
            UnsupportedProviderError: If provider is not supported

        """
        cache_key = f"{ruleset_uri}:{rule_type.__name__}"

        if cache_key not in cls._cache:
            logger.debug(f"Loading ruleset: {ruleset_uri} (type: {rule_type.__name__})")
            ruleset = RulesetLoader.load_ruleset_instance(ruleset_uri, rule_type)
            cls._cache[cache_key] = ruleset
        else:
            logger.debug(
                f"Using cached ruleset: {ruleset_uri} (type: {rule_type.__name__})"
            )

        return cls._cache[cache_key]  # type: ignore[return-value]

    @classmethod
    def get_rules[T: Rule](cls, ruleset_uri: str, rule_type: type[T]) -> tuple[T, ...]:
        """Get rules from ruleset using URI with type safety and caching.

        This is a convenience method that returns just the rules.
        Use get_ruleset() if you need access to other ruleset methods.

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
        return cls.get_ruleset(ruleset_uri, rule_type).get_rules()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the ruleset cache."""
        cls._cache.clear()
        logger.debug("Ruleset cache cleared")
