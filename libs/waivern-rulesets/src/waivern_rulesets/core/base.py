"""Abstract base class for rulesets."""

import abc
import logging
import sys
from pathlib import Path
from typing import Any, ClassVar, override

import yaml
from waivern_core import BaseRuleset, Rule, RulesetData

logger = logging.getLogger(__name__)


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


class YAMLRuleset[RuleType: Rule](AbstractRuleset[RuleType]):
    """Base class for YAML-backed rulesets.

    Eliminates boilerplate for YAML loading by providing default implementations
    of name, version, and get_rules(). Subclasses need only define ClassVars.

    Required ClassVars (defined by subclass, not inherited):
        ruleset_name: Canonical name for the ruleset
        ruleset_version: Semantic version string
        _data_class: The RulesetData subclass for parsing YAML

    The YAML file is expected at:
        {subclass_module_dir}/data/{version}/{name}.yaml

    For rulesets that need additional data beyond rules (e.g., risk_modifiers),
    use _load_data() to access the full RulesetData object.
    """

    # Note: _data_class is NOT declared here to avoid ClassVar invariance issues.
    # Subclasses must define: _data_class: ClassVar[type[SomeRulesetData]] = SomeRulesetData
    _data_class: ClassVar[type[RulesetData[Any]]]  # Type hint only, no default

    def __init__(self) -> None:
        """Initialise the YAML-backed ruleset."""
        self._rules_cache: tuple[RuleType, ...] | None = None
        self._data_cache: RulesetData[RuleType] | None = None
        logger.debug(f"Initialised {self.ruleset_name} ruleset v{self.ruleset_version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return self.ruleset_name

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return self.ruleset_version

    def _get_data_file_path(self) -> Path:
        """Get the path to the YAML data file.

        Uses the concrete subclass's module location to find the data directory.
        This allows each ruleset package to have its own data/ directory.
        """
        module = sys.modules[self.__class__.__module__]
        module_file = module.__file__
        if module_file is None:
            msg = f"Cannot determine file path for module {self.__class__.__module__}"
            raise RuntimeError(msg)
        return (
            Path(module_file).parent
            / "data"
            / self.ruleset_version
            / f"{self.ruleset_name}.yaml"
        )

    def _load_data(self) -> RulesetData[RuleType]:
        """Load and cache the ruleset data from YAML.

        Returns:
            The parsed and validated RulesetData object.

        Note:
            For rulesets with additional properties beyond rules (e.g., risk_modifiers),
            subclasses can call this method and cast to their specific data type.

        """
        if self._data_cache is None:
            yaml_file = self._get_data_file_path()
            with yaml_file.open("r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
            self._data_cache = self._data_class.model_validate(raw_data)
            logger.debug(f"Loaded {len(self._data_cache.rules)} rules from {self.name}")
        return self._data_cache

    @override
    def get_rules(self) -> tuple[RuleType, ...]:
        """Get the rules defined by this ruleset.

        Returns:
            Immutable tuple of rules loaded from the YAML file.

        """
        if self._rules_cache is None:
            self._rules_cache = tuple(self._load_data().rules)
        return self._rules_cache
