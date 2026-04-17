"""Tests for ProcessingPurposeAnalyserFactory."""

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer

from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser
from waivern_processing_purpose_analyser.factory import (
    ProcessingPurposeAnalyserFactory,
)


class TestProcessingPurposeAnalyserFactory(
    ComponentFactoryContractTests[ProcessingPurposeAnalyser]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[ProcessingPurposeAnalyser]:
        return ProcessingPurposeAnalyserFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "pattern_matching": {
                "ruleset": "local/processing_purposes/1.0.0",
                "evidence_context_size": "medium",
                "maximum_evidence_count": 5,
            },
            "llm_validation": {
                "enable_llm_validation": True,
                "llm_validation_mode": "standard",
            },
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        factory = ProcessingPurposeAnalyserFactory(ServiceContainer())

        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

        assert factory.can_create(config_with_nonexistent_ruleset) is False
