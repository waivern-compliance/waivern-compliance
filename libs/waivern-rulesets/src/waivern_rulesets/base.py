"""Abstract base class for rulesets."""

import abc
from typing import ClassVar, override

from waivern_core import BaseRuleset, Rule


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
