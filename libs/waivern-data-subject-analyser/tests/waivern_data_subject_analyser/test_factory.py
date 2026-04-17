"""Tests for DataSubjectAnalyserFactory."""

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer

from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.factory import DataSubjectAnalyserFactory


class TestDataSubjectAnalyserFactory(
    ComponentFactoryContractTests[DataSubjectAnalyser]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[DataSubjectAnalyser]:
        return DataSubjectAnalyserFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "pattern_matching": {"ruleset": "local/data_subject_indicator/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        factory = DataSubjectAnalyserFactory(ServiceContainer())

        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

        assert factory.can_create(config_with_nonexistent_ruleset) is False
