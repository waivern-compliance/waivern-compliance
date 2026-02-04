"""Tests for GDPRDataSubjectClassifierFactory.

This test module uses the CONTRACT TESTING PATTERN by inheriting from
ComponentFactoryContractTests to ensure GDPRDataSubjectClassifierFactory
correctly implements the ComponentFactory interface.

Contract tests (inherited automatically):
1. test_create_returns_component_instance
2. test_get_component_name_returns_non_empty_string
3. test_get_input_schemas_returns_list_of_schemas
4. test_get_output_schemas_returns_list_of_schemas
5. test_can_create_returns_bool_for_valid_config
6. test_get_service_dependencies_returns_dict

Factory-specific tests (added in this module):
- LLM service availability check when validation enabled
- Service dependency declarations
- Invalid configuration handling
"""

from unittest.mock import Mock

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory
from waivern_llm.v2 import LLMService

from waivern_gdpr_data_subject_classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.factory import (
    GDPRDataSubjectClassifierFactory,
)


class TestGDPRDataSubjectClassifierFactory(
    ComponentFactoryContractTests[GDPRDataSubjectClassifier]
):
    """Test GDPRDataSubjectClassifierFactory with contract compliance + factory-specific tests.

    Inherits 6 contract tests automatically from ComponentFactoryContractTests.
    Adds factory-specific tests for LLM service injection behaviour.
    """

    # -------------------------------------------------------------------------
    # Required fixtures for contract tests
    # -------------------------------------------------------------------------

    @pytest.fixture
    def factory(self) -> ComponentFactory[GDPRDataSubjectClassifier]:
        """Provide factory instance with mocked LLM service.

        This fixture is required by ComponentFactoryContractTests.
        """
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))
        return GDPRDataSubjectClassifierFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for factory.create().

        This fixture is required by ComponentFactoryContractTests.
        Configuration includes LLM validation enabled to test full flow.
        """
        return {
            "ruleset": "local/gdpr_data_subject_classification/1.0.0",
            "llm_validation": {
                "enable_llm_validation": True,
                "llm_batch_size": 10,
            },
        }

    # -------------------------------------------------------------------------
    # Factory-specific tests
    # -------------------------------------------------------------------------

    def test_can_create_returns_false_when_llm_required_but_unavailable(self) -> None:
        """Test graceful degradation when LLM validation enabled but service unavailable."""
        # Arrange: Factory with EMPTY container (no LLM service registered)
        empty_container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(empty_container)

        config: ComponentConfig = {
            "ruleset": "local/gdpr_data_subject_classification/1.0.0",
            "llm_validation": {
                "enable_llm_validation": True,  # LLM required
                "llm_batch_size": 10,
            },
        }

        # Act
        result = factory.can_create(config)

        # Assert: Cannot create when LLM required but unavailable
        assert result is False

    def test_get_service_dependencies_declares_llm_service(self) -> None:
        """Test that factory declares LLMService dependency."""
        # Arrange: Factory with no container (not needed for this check)
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        # Act
        dependencies = factory.get_service_dependencies()

        # Assert: LLM service declared
        assert "llm_service" in dependencies
        assert dependencies["llm_service"] is LLMService

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """Test that can_create returns False when ruleset doesn't exist."""
        # Arrange: Factory with valid container but config pointing to nonexistent ruleset
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        config: ComponentConfig = {
            "ruleset": "local/nonexistent_ruleset/1.0.0",  # Doesn't exist
        }

        # Act
        result = factory.can_create(config)

        # Assert: Cannot create with nonexistent ruleset
        assert result is False
