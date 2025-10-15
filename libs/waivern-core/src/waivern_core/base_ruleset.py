"""Base ruleset abstraction for Waivern Compliance Framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRuleset(ABC):
    """Abstract base class for rulesets.

    Rulesets define collections of rules for compliance analysis.
    All rulesets must implement this interface to be compatible with
    the Waivern Compliance Framework.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the canonical name of this ruleset.

        Returns:
            The fixed, canonical name for this ruleset type

        """

    @property
    @abstractmethod
    def version(self) -> str:
        """Get the version of this ruleset.

        Returns:
            Version string in semantic versioning format (e.g., "1.0.0")

        """

    @abstractmethod
    def get_rules(self) -> tuple[Any, ...]:
        """Get the rules defined by this ruleset.

        Returns:
            Immutable tuple of rule objects

        """


class RulesetError(Exception):
    """Base exception for ruleset-related errors."""

    pass
