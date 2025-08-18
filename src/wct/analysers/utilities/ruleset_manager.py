"""Ruleset management utility for analysers."""

import logging

from wct.rulesets import RulesetLoader
from wct.rulesets.types import Rule

logger = logging.getLogger(__name__)


class RulesetManager:
    """Singleton utility for loading and caching rulesets."""

    _instance: "RulesetManager | None" = None
    _patterns_cache: dict[str, tuple[Rule, ...]] = {}

    def __new__(cls) -> "RulesetManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_rules(cls, ruleset_name: str) -> tuple[Rule, ...]:
        """Get rules from ruleset, using cache when possible.

        Args:
            ruleset_name: Name of the ruleset to load

        Returns:
            Tuple of Rule objects loaded from the ruleset

        """
        if ruleset_name not in cls._patterns_cache:
            cls._patterns_cache[ruleset_name] = RulesetLoader.load_ruleset(ruleset_name)
            logger.info(f"Loaded ruleset: {ruleset_name}")

        return cls._patterns_cache[ruleset_name]

    def clear_cache(self) -> None:
        """Clear the patterns cache.

        Useful for testing or when rulesets are updated.
        """
        self.__class__._patterns_cache.clear()
        logger.debug("Pattern cache cleared")
