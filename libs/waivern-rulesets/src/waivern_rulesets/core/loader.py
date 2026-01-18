"""Ruleset loader for loading rulesets by URI."""

import logging
from typing import TYPE_CHECKING, overload

from waivern_core import Rule

from waivern_rulesets.core.base import AbstractRuleset
from waivern_rulesets.core.exceptions import UnsupportedProviderError
from waivern_rulesets.core.registry import RulesetRegistry
from waivern_rulesets.core.uri import RulesetURI

if TYPE_CHECKING:
    from waivern_rulesets.gdpr_data_subject_classification import (
        GDPRDataSubjectClassificationRule,
    )
    from waivern_rulesets.protocols import DataSubjectClassificationRulesetProtocol

logger = logging.getLogger(__name__)


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

    # Overload for GDPRDataSubjectClassificationRule returns the Protocol
    # which includes get_risk_modifiers() for type-safe access
    @overload
    @classmethod
    def load_ruleset_instance(  # pyright: ignore[reportOverlappingOverload]
        cls, ruleset_uri: str, rule_type: "type[GDPRDataSubjectClassificationRule]"
    ) -> "DataSubjectClassificationRulesetProtocol": ...

    @overload
    @classmethod
    def load_ruleset_instance[T: Rule](
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> AbstractRuleset[T]: ...

    @classmethod
    def load_ruleset_instance[T: Rule](  # pyright: ignore[reportInconsistentOverload]
        cls, ruleset_uri: str, rule_type: type[T]
    ) -> AbstractRuleset[T]:
        """Load a ruleset instance using URI format with provider validation.

        Unlike load_ruleset() which returns only the rules, this method returns
        the full ruleset instance, allowing access to all ruleset methods
        (e.g., get_rules(), get_risk_modifiers(), name, version).

        When called with GDPRDataSubjectClassificationRule, returns a
        DataSubjectClassificationRulesetProtocol which includes the
        get_risk_modifiers() method.

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation and typing

        Returns:
            The ruleset instance with full access to all methods.
            For GDPRDataSubjectClassificationRule, returns
            DataSubjectClassificationRulesetProtocol.

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
            risk_modifiers = ruleset.get_risk_modifiers()  # Type-safe!

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
