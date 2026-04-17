"""Tests for PersonalDataAnalyserFactory.

Inherits contract tests from ``ComponentFactoryContractTests`` and adds
factory-specific validation checks (ruleset availability).
"""

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer

from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.factory import PersonalDataAnalyserFactory


class TestPersonalDataAnalyserFactory(
    ComponentFactoryContractTests[PersonalDataAnalyser]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[PersonalDataAnalyser]:
        """Provide a factory wired with an empty ServiceContainer."""
        return PersonalDataAnalyserFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide a valid runbook configuration for create()/can_create()."""
        return {
            "pattern_matching": {
                "ruleset": "local/personal_data_indicator/1.0.0",
                "evidence_context_size": "medium",
                "maximum_evidence_count": 5,
            },
            "llm_validation": {
                "enable_llm_validation": True,
                "llm_validation_mode": "standard",
            },
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """A missing ruleset surfaces through can_create(), not create()."""
        factory = PersonalDataAnalyserFactory(ServiceContainer())

        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

        assert factory.can_create(config_with_nonexistent_ruleset) is False
