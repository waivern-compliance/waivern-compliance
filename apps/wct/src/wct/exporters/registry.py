"""Registry for exporters."""

from typing import TypedDict

from wct.exporters.protocol import Exporter


class ExporterRegistryState(TypedDict):
    """State snapshot for ExporterRegistry.

    Used for test isolation - captures and restores registry state
    to prevent test pollution.
    """

    exporters: dict[str, Exporter]


class ExporterRegistry:
    """Registry for exporters."""

    _exporters: dict[str, Exporter] = {}

    @classmethod
    def register(cls, exporter: Exporter) -> None:
        """Register an exporter.

        Args:
            exporter: Exporter instance to register.

        """
        cls._exporters[exporter.name] = exporter

    @classmethod
    def get(cls, name: str) -> Exporter:
        """Get exporter by name.

        Args:
            name: Name of the exporter to retrieve.

        Returns:
            Registered exporter instance.

        Raises:
            ValueError: If exporter not found.

        """
        if name not in cls._exporters:
            available = list(cls._exporters.keys())
            msg = f"Unknown exporter '{name}'. Available: {available}"
            raise ValueError(msg)
        return cls._exporters[name]

    @classmethod
    def list_exporters(cls) -> list[str]:
        """List available exporter names.

        Returns:
            List of registered exporter names.

        """
        return list(cls._exporters.keys())

    @classmethod
    def snapshot_state(cls) -> ExporterRegistryState:
        """Capture current ExporterRegistry state for later restoration.

        This is primarily used for test isolation - save state before tests,
        restore after tests to prevent global state pollution.

        Returns:
            State dictionary containing all mutable registry state.

        """
        return {"exporters": cls._exporters.copy()}

    @classmethod
    def restore_state(cls, state: ExporterRegistryState) -> None:
        """Restore ExporterRegistry state from a previously captured snapshot.

        This is primarily used for test isolation - restore state after tests
        to ensure tests don't pollute global state.

        Args:
            state: State dictionary from snapshot_state().

        """
        cls._exporters = state["exporters"].copy()
