"""Tests for Planner error handling.

For successful planning scenarios, see test_planner.py.
"""

import pytest
from waivern_core.schemas import Schema

from waivern_orchestration import (
    ComponentNotFoundError,
    CycleDetectedError,
    MissingArtifactError,
    SchemaCompatibilityError,
)
from waivern_orchestration.planner import Planner

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_processor_factory,
    create_mock_registry,
)

# =============================================================================
# Component Not Found Errors
# =============================================================================


class TestPlannerComponentNotFound:
    """Tests for missing component scenarios."""

    def test_plan_connector_not_found(self) -> None:
        """Unknown connector type raises ComponentNotFoundError."""
        registry = create_mock_registry()  # No connectors
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "data": {"source": {"type": "unknown_connector", "properties": {}}}
            },
        }

        with pytest.raises(ComponentNotFoundError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "unknown_connector" in str(exc_info.value)

    def test_plan_analyser_not_found(self) -> None:
        """Unknown analyser type raises ComponentNotFoundError."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "findings": {
                    "inputs": "source",
                    "process": {"type": "unknown_analyser", "properties": {}},
                },
            },
        }

        with pytest.raises(ComponentNotFoundError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "unknown_analyser" in str(exc_info.value)


# =============================================================================
# Dependency Errors
# =============================================================================


class TestPlannerDependencyErrors:
    """Tests for dependency-related error scenarios."""

    def test_plan_missing_artifact_reference(self) -> None:
        """Invalid inputs reference raises MissingArtifactError."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "derived": {
                    "inputs": "nonexistent_artifact",
                },
            },
        }

        with pytest.raises(MissingArtifactError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "nonexistent_artifact" in str(exc_info.value)

    def test_plan_cycle_detected(self) -> None:
        """Cycle in dependencies raises CycleDetectedError."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "a": {"inputs": "c"},
                "b": {"inputs": "a"},
                "c": {"inputs": "b"},
            },
        }

        with pytest.raises(CycleDetectedError):
            planner.plan_from_dict(runbook_data)


# =============================================================================
# Schema Compatibility Errors
# =============================================================================


class TestPlannerSchemaCompatibilityErrors:
    """Tests for schema compatibility error scenarios."""

    def test_plan_fan_in_incompatible_schemas_different_name(self) -> None:
        """Fan-in with different schema names raises SchemaCompatibilityError."""
        connector_a = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_b = create_mock_connector_factory(
            "database", [Schema("database_schema", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_a, "database": connector_b}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Fan-in incompatible test",
            "artifacts": {
                "source_a": {"source": {"type": "filesystem", "properties": {}}},
                "source_b": {"source": {"type": "database", "properties": {}}},
                "merged": {
                    "inputs": ["source_a", "source_b"],
                },
            },
        }

        with pytest.raises(SchemaCompatibilityError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "merged" in str(exc_info.value)
        assert "standard_input" in str(exc_info.value)
        assert "database_schema" in str(exc_info.value)

    def test_plan_multi_schema_no_matching_combination(self) -> None:
        """Multi-schema inputs not matching any declared combination raises SchemaCompatibilityError."""
        schema_a = Schema("security_evidence", "1.0.0")
        schema_b = Schema("security_document_context", "1.0.0")
        schema_c = Schema("unrelated_schema", "1.0.0")

        connector_a = create_mock_connector_factory("source_code", [schema_a])
        connector_b = create_mock_connector_factory("filesystem", [schema_b])
        # Processor declares [[A, C]] but runbook provides A + B
        processor_factory = create_mock_processor_factory(
            "some_processor",
            [],
            [Schema("output", "1.0.0")],
            input_requirements=[[schema_a, schema_c]],
        )

        registry = create_mock_registry(
            connector_factories={"source_code": connector_a, "filesystem": connector_b},
            processor_factories={"some_processor": processor_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Mismatched multi-schema",
            "artifacts": {
                "source_a": {"source": {"type": "source_code", "properties": {}}},
                "source_b": {"source": {"type": "filesystem", "properties": {}}},
                "derived": {
                    "inputs": ["source_a", "source_b"],
                    "process": {"type": "some_processor", "properties": {}},
                },
            },
        }

        with pytest.raises(SchemaCompatibilityError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "derived" in str(exc_info.value)
        assert "some_processor" in str(exc_info.value)

    def test_plan_multi_schema_without_processor_raises_error(self) -> None:
        """Multi-schema inputs without a processor (pass-through) raises SchemaCompatibilityError."""
        connector_a = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_b = create_mock_connector_factory(
            "database", [Schema("database_schema", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_a, "database": connector_b}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Multi-schema without processor",
            "artifacts": {
                "source_a": {"source": {"type": "filesystem", "properties": {}}},
                "source_b": {"source": {"type": "database", "properties": {}}},
                "merged": {
                    "inputs": ["source_a", "source_b"],
                },
            },
        }

        with pytest.raises(SchemaCompatibilityError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "merged" in str(exc_info.value)
        assert "no processor" in str(exc_info.value).lower()

    def test_plan_fan_in_incompatible_schemas_different_version(self) -> None:
        """Fan-in with same schema name but different versions raises SchemaCompatibilityError."""
        connector_v1 = create_mock_connector_factory(
            "filesystem_v1", [Schema("standard_input", "1.0.0")]
        )
        connector_v2 = create_mock_connector_factory(
            "filesystem_v2", [Schema("standard_input", "2.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={
                "filesystem_v1": connector_v1,
                "filesystem_v2": connector_v2,
            }
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Fan-in version mismatch test",
            "artifacts": {
                "source_v1": {"source": {"type": "filesystem_v1", "properties": {}}},
                "source_v2": {"source": {"type": "filesystem_v2", "properties": {}}},
                "merged": {
                    "inputs": ["source_v1", "source_v2"],
                },
            },
        }

        with pytest.raises(SchemaCompatibilityError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "merged" in str(exc_info.value)
        assert "1.0.0" in str(exc_info.value)
        assert "2.0.0" in str(exc_info.value)
