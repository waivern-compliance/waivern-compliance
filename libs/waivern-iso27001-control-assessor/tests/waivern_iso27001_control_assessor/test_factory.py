"""Tests for ISO27001AssessorFactory and ISO27001Assessor contract compliance."""

from unittest.mock import Mock

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory
from waivern_core.testing import AnalyserContractTests, ComponentFactoryContractTests
from waivern_llm import LLMService

from waivern_iso27001_control_assessor import (
    ISO27001Assessor,
    ISO27001AssessorFactory,
)


class TestISO27001AssessorContract(AnalyserContractTests[ISO27001Assessor]):
    """Contract tests for ISO27001Assessor class-level declarations."""

    @pytest.fixture
    def processor_class(self) -> type[ISO27001Assessor]:
        return ISO27001Assessor


class TestISO27001AssessorFactoryContract(
    ComponentFactoryContractTests[ISO27001Assessor],
):
    """Contract tests for ISO27001AssessorFactory."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[ISO27001Assessor]:
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))
        return ISO27001AssessorFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "domain_ruleset": "local/iso27001_domains/1.0.0",
            "control_ref": "A.5.1",
        }


class TestISO27001AssessorFactory:
    """Factory-specific behaviour tests."""

    def test_can_create_returns_false_when_llm_unavailable(self):
        """can_create() returns False when LLM service is not in container."""
        container = ServiceContainer()
        factory = ISO27001AssessorFactory(container)

        result = factory.can_create(
            {
                "domain_ruleset": "local/iso27001_domains/1.0.0",
                "control_ref": "A.5.1",
            }
        )

        assert result is False

    def test_can_create_returns_false_for_missing_control_ref(self):
        """can_create() returns False when control_ref is missing from config."""
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))

        factory = ISO27001AssessorFactory(container)

        result = factory.can_create(
            {
                "domain_ruleset": "local/iso27001_domains/1.0.0",
            }
        )

        assert result is False

    def test_get_service_dependencies_declares_llm_service(self):
        """Factory declares LLMService as a required dependency."""
        container = ServiceContainer()
        factory = ISO27001AssessorFactory(container)

        deps = factory.get_service_dependencies()

        assert "llm_service" in deps
        assert deps["llm_service"] is LLMService
