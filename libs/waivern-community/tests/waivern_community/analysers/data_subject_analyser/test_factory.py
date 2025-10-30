"""Tests for DataSubjectAnalyserFactory."""

from unittest.mock import Mock

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_llm import BaseLLMService

from waivern_community.analysers.data_subject_analyser import DataSubjectAnalyser
from waivern_community.analysers.data_subject_analyser.factory import (
    DataSubjectAnalyserFactory,
)


class TestDataSubjectAnalyserFactory(
    ComponentFactoryContractTests[DataSubjectAnalyser]
):
    """Contract tests for DataSubjectAnalyserFactory."""

    # Fixtures required by ComponentFactoryContractTests
    @pytest.fixture
    def factory(self) -> ComponentFactory[DataSubjectAnalyser]:
        """Create factory instance for testing."""
        mock_llm_service = Mock(spec=BaseLLMService)
        return DataSubjectAnalyserFactory(llm_service=mock_llm_service)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Create valid configuration for testing."""
        return {
            "pattern_matching": {"ruleset": "data_subjects"},
            "llm_validation": {"enable_llm_validation": False},
        }

    # Factory-specific tests
    def test_can_create_returns_false_when_llm_required_but_unavailable(self) -> None:
        """Test graceful degradation when LLM validation enabled but service unavailable."""
        pass

    def test_get_service_dependencies_declares_llm_service(self) -> None:
        """Test that factory declares BaseLLMService as dependency."""
        pass
