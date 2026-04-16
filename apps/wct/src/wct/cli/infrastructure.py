"""Shared CLI infrastructure setup."""

from __future__ import annotations

import logging

from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_core.services import ComponentRegistry, ServiceContainer, ServiceDescriptor

from wct.exporters.json_exporter import JsonExporter
from wct.exporters.registry import ExporterRegistry

logger = logging.getLogger(__name__)


def initialise_exporters() -> None:
    """Initialise and register all exporters.

    Registers framework-agnostic exporters. Framework-specific exporters
    (e.g., GdprExporter) are registered when their configuration becomes available.
    """
    ExporterRegistry.register(JsonExporter())
    logger.debug("Registered JsonExporter")


def build_service_container() -> ServiceContainer:
    """Build a ServiceContainer with required services.

    Creates and configures a ServiceContainer with:
    - ArtifactStore (singleton) - shared between executor and exporter

    LLM dispatch is wired separately by the executor via ``LLMDispatcherFactory``;
    processors themselves have no LLM service dependencies.

    Returns:
        Configured ServiceContainer.

    """
    container = ServiceContainer()

    # Register ArtifactStore as singleton (shared between executor and exporter)
    container.register(
        ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
    )

    logger.debug("ServiceContainer configured with ArtifactStore service")
    return container


def setup_infrastructure() -> ComponentRegistry:
    """Set up infrastructure for runbook execution.

    Returns:
        Configured ComponentRegistry with services.

    """
    initialise_exporters()
    container = build_service_container()
    registry = ComponentRegistry(container)
    logger.debug("Infrastructure setup complete")
    return registry
