"""Tests for DataSubjectAnalyserFactory.

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
from waivern_core.services import ServiceContainer
from waivern_rulesets import AbstractRuleset
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule

from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.factory import DataSubjectAnalyserFactory

_VALID_RULESET_URI = "local/test_data_subject/1.0.0"

RULE_EMPLOYEE = DataSubjectIndicatorRule(
    name="Test Employee",
    description="Employee indicator",
    subject_category="test_employee",
    indicator_type="primary",
    confidence_weight=45,
    patterns=("test_employee_kw",),
)

SYNTHETIC_RULES = (RULE_EMPLOYEE,)


def _mock_get_ruleset(
    uri: str, rule_type: type[DataSubjectIndicatorRule]
) -> AbstractRuleset[DataSubjectIndicatorRule]:
    """Return a mock ruleset for the valid URI; raise for unknown URIs."""
    if uri == _VALID_RULESET_URI:
        mock_ruleset = MagicMock(spec=AbstractRuleset)
        mock_ruleset.get_rules.return_value = SYNTHETIC_RULES
        return mock_ruleset
    raise ValueError(f"Unknown ruleset URI: {uri}")


def _mock_get_rules(
    uri: str, rule_type: type[DataSubjectIndicatorRule]
) -> tuple[DataSubjectIndicatorRule, ...]:
    """Return synthetic rules for the valid URI; raise for unknown URIs."""
    if uri == _VALID_RULESET_URI:
        return SYNTHETIC_RULES
    raise ValueError(f"Unknown ruleset URI: {uri}")


class TestDataSubjectAnalyserFactory(
    ComponentFactoryContractTests[DataSubjectAnalyser]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject mock RulesetManager so factory tests don't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_ruleset", _mock_get_ruleset)
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    @pytest.fixture
    def factory(self) -> ComponentFactory[DataSubjectAnalyser]:
        return DataSubjectAnalyserFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "pattern_matching": {"ruleset": _VALID_RULESET_URI},
            "llm_validation": {"enable_llm_validation": False},
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """A missing ruleset surfaces through can_create(), not create()."""
        factory = DataSubjectAnalyserFactory(ServiceContainer())

        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

        assert factory.can_create(config_with_nonexistent_ruleset) is False
