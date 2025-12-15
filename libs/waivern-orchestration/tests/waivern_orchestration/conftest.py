"""Shared pytest fixtures for waivern-orchestration tests."""

from typing import Any

import pytest
from waivern_core.component_factory import ComponentFactory
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_processor_factory,
    create_mock_registry,
)

# =============================================================================
# Component Factory Fixtures
# =============================================================================


@pytest.fixture
def filesystem_connector_factory() -> ComponentFactory[Any]:
    """Factory for filesystem connector producing standard_input schema."""
    return create_mock_connector_factory(
        "filesystem", [Schema("standard_input", "1.0.0")]
    )


@pytest.fixture
def analyser_processor_factory() -> ComponentFactory[Any]:
    """Factory for analyser processor: standard_input -> finding."""
    return create_mock_processor_factory(
        "analyser",
        [Schema("standard_input", "1.0.0")],
        [Schema("finding", "1.0.0")],
    )


@pytest.fixture
def summariser_processor_factory() -> ComponentFactory[Any]:
    """Factory for summariser processor: finding -> summary."""
    return create_mock_processor_factory(
        "summariser",
        [Schema("finding", "1.0.0")],
        [Schema("summary", "1.0.0")],
    )


# =============================================================================
# Registry Fixtures
# =============================================================================


@pytest.fixture
def basic_registry(
    filesystem_connector_factory: ComponentFactory[Any],
    analyser_processor_factory: ComponentFactory[Any],
) -> ComponentRegistry:
    """Registry with filesystem connector and analyser processor."""
    return create_mock_registry(
        connector_factories={"filesystem": filesystem_connector_factory},
        processor_factories={"analyser": analyser_processor_factory},
    )


@pytest.fixture
def registry_with_summariser(
    filesystem_connector_factory: ComponentFactory[Any],
    analyser_processor_factory: ComponentFactory[Any],
    summariser_processor_factory: ComponentFactory[Any],
) -> ComponentRegistry:
    """Registry with filesystem, analyser, and summariser."""
    return create_mock_registry(
        connector_factories={"filesystem": filesystem_connector_factory},
        processor_factories={
            "analyser": analyser_processor_factory,
            "summariser": summariser_processor_factory,
        },
    )
