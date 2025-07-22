"""Base classes and utilities for rulesets."""

import abc
from typing import Any, Dict, Optional


class RulesetError(Exception):
    """Base exception for ruleset-related errors."""

    pass


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

    pass


class RulesetLoader(abc.ABC):
    """Abstract base class for loading rulesets from different sources."""

    @abc.abstractmethod
    def load_ruleset(self, ruleset_name: str) -> Dict[str, Any]:
        """Load a ruleset by name.

        Args:
            ruleset_name: Name of the ruleset to load

        Returns:
            Dictionary containing the ruleset data

        Raises:
            RulesetNotFoundError: If the ruleset cannot be found
        """


class ModuleRulesetLoader(RulesetLoader):
    """Loads rulesets from Python modules in the rulesets package."""

    def load_ruleset(self, ruleset_name: str) -> Dict[str, Any]:
        """Load a ruleset from a Python module.

        Args:
            ruleset_name: Name of the ruleset module (e.g., "personal_data_gdpr")

        Returns:
            Dictionary containing the ruleset data
        """
        try:
            module_path = f"wct.rulesets.{ruleset_name}"
            module = __import__(module_path, fromlist=[ruleset_name])

            # Look for a patterns dictionary in the module
            for attr_name in dir(module):
                if attr_name.endswith("_PATTERNS") and not attr_name.startswith("_"):
                    return getattr(module, attr_name)

            raise RulesetNotFoundError(
                f"No patterns found in ruleset module {ruleset_name}"
            )

        except ImportError as e:
            raise RulesetNotFoundError(
                f"Ruleset module {ruleset_name} not found"
            ) from e


def get_ruleset(
    ruleset_name: str, loader: Optional[RulesetLoader] = None
) -> Dict[str, Any]:
    """Get a ruleset using the specified loader.

    Args:
        ruleset_name: Name of the ruleset to load
        loader: RulesetLoader instance (defaults to ModuleRulesetLoader)

    Returns:
        Dictionary containing the ruleset data
    """
    if loader is None:
        loader = ModuleRulesetLoader()

    return loader.load_ruleset(ruleset_name)
