"""Tests for CryptoQualityAnalyserFactory.

Inherits contract tests from ``ComponentFactoryContractTests`` and adds
factory-specific validation checks (ruleset availability).

Uses monkeypatched RulesetManager to decouple from production rulesets.
"""

from unittest.mock import MagicMock

import pytest
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.errors import ProcessorConfigError
from waivern_core.services import ServiceContainer
from waivern_rulesets import AbstractRuleset
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRule

from waivern_crypto_quality_analyser import CryptoQualityAnalyser
from waivern_crypto_quality_analyser.factory import CryptoQualityAnalyserFactory

_VALID_RULESET_URI = "local/test_crypto_quality/1.0.0"

RULE_STRONG = CryptoQualityIndicatorRule(
    name="Test Strong Algo",
    description="Strong algorithm detection",
    category="strong_algo",
    algorithm="test_strong",
    quality_rating="strong",
    patterns=("test_strong_pattern",),
)

SYNTHETIC_RULES = (RULE_STRONG,)


def _mock_get_ruleset(
    uri: str, rule_type: type[CryptoQualityIndicatorRule]
) -> AbstractRuleset[CryptoQualityIndicatorRule]:
    """Return a mock ruleset for the valid URI; raise for unknown URIs."""
    if uri == _VALID_RULESET_URI:
        mock_ruleset = MagicMock(spec=AbstractRuleset)
        mock_ruleset.get_rules.return_value = SYNTHETIC_RULES
        return mock_ruleset
    raise ValueError(f"Unknown ruleset URI: {uri}")


def _mock_get_rules(
    uri: str, rule_type: type[CryptoQualityIndicatorRule]
) -> tuple[CryptoQualityIndicatorRule, ...]:
    """Return synthetic rules for the valid URI; raise for unknown URIs."""
    if uri == _VALID_RULESET_URI:
        return SYNTHETIC_RULES
    raise ValueError(f"Unknown ruleset URI: {uri}")


class TestCryptoQualityAnalyserFactory(
    ComponentFactoryContractTests[CryptoQualityAnalyser]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject mock RulesetManager so factory tests don't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_ruleset", _mock_get_ruleset)
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    @pytest.fixture
    def factory(self) -> ComponentFactory[CryptoQualityAnalyser]:
        """Provide a factory wired with an empty ServiceContainer."""
        return CryptoQualityAnalyserFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide a valid runbook configuration for create()/can_create()."""
        return {
            "pattern_matching": {
                "ruleset": _VALID_RULESET_URI,
                "evidence_context_size": "medium",
                "maximum_evidence_count": 5,
            },
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """A missing ruleset surfaces through can_create(), not create()."""
        factory = CryptoQualityAnalyserFactory(ServiceContainer())

        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
        }

        assert factory.can_create(config_with_nonexistent_ruleset) is False

    def test_create_raises_processor_config_error_for_invalid_config(self) -> None:
        """create() surfaces the translated config error, not a generic ValueError."""
        factory = CryptoQualityAnalyserFactory(ServiceContainer())

        with pytest.raises(
            ProcessorConfigError, match="Invalid CryptoQualityAnalyserConfig"
        ):
            factory.create({"unknown_field": "value"})
