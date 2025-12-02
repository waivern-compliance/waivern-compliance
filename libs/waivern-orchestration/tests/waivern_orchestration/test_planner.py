"""Tests for the Planner class."""

import pytest
from waivern_core.schemas import Schema

from waivern_orchestration import (
    ComponentNotFoundError,
    CycleDetectedError,
    MissingArtifactError,
    SchemaCompatibilityError,
)
from waivern_orchestration.planner import ExecutionPlan, Planner

from .test_helpers import (
    create_mock_analyser_factory,
    create_mock_connector_factory,
    create_mock_registry,
)


class TestPlannerHappyPath:
    """Tests for successful planning scenarios."""

    def test_plan_valid_source_artifact(self) -> None:
        """Planner can plan a runbook with a source artifact."""
        output_schema = Schema("standard_input", "1.0.0")
        connector_factory = create_mock_connector_factory("filesystem", [output_schema])

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "artifacts": {
                "data_source": {
                    "source": {
                        "type": "filesystem",
                        "properties": {"path": "/tmp"},
                    }
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        assert isinstance(plan, ExecutionPlan)
        assert plan.runbook.name == "Test Runbook"
        assert "data_source" in plan.runbook.artifacts
        assert plan.dag is not None
        assert "data_source" in plan.artifact_schemas
        input_schema, result_output_schema = plan.artifact_schemas["data_source"]
        assert input_schema is None
        assert result_output_schema.name == "standard_input"

    def test_plan_valid_derived_artifact_with_transform(self) -> None:
        """Planner can plan derived artifact with transform (source → analyser chain)."""
        connector_output = Schema("standard_input", "1.0.0")
        analyser_input = Schema("standard_input", "1.0.0")
        analyser_output = Schema("personal_data_finding", "1.0.0")

        connector_factory = create_mock_connector_factory(
            "filesystem", [connector_output]
        )
        analyser_factory = create_mock_analyser_factory(
            "personal_data_analyser", [analyser_input], [analyser_output]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory},
            analyser_factories={"personal_data_analyser": analyser_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test Runbook",
            "description": "Source to derived chain",
            "artifacts": {
                "data_source": {
                    "source": {"type": "filesystem", "properties": {"path": "/tmp"}}
                },
                "findings": {
                    "inputs": "data_source",
                    "transform": {
                        "type": "personal_data_analyser",
                        "properties": {},
                    },
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        assert isinstance(plan, ExecutionPlan)
        assert "data_source" in plan.artifact_schemas
        assert "findings" in plan.artifact_schemas

        source_input, source_output = plan.artifact_schemas["data_source"]
        assert source_input is None
        assert source_output.name == "standard_input"

        derived_input, derived_output = plan.artifact_schemas["findings"]
        assert derived_input is not None
        assert derived_input.name == "standard_input"
        assert derived_output.name == "personal_data_finding"

    def test_plan_derived_artifact_without_transform_passthrough(self) -> None:
        """Derived artifact without transform passes schema through (no analyser)."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Passthrough test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "passthrough": {
                    "inputs": "source",
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, source_output = plan.artifact_schemas["source"]
        pass_input, pass_output = plan.artifact_schemas["passthrough"]

        assert source_output.name == "standard_input"
        assert pass_input is not None
        assert pass_input.name == "standard_input"
        assert pass_output.name == "standard_input"

    def test_plan_fan_in_compatible_schemas(self) -> None:
        """Fan-in works when all inputs have same schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Fan-in test",
            "artifacts": {
                "source_a": {
                    "source": {"type": "filesystem", "properties": {"path": "/a"}}
                },
                "source_b": {
                    "source": {"type": "filesystem", "properties": {"path": "/b"}}
                },
                "merged": {
                    "inputs": ["source_a", "source_b"],
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        merged_input, merged_output = plan.artifact_schemas["merged"]
        assert merged_input is not None
        assert merged_input.name == "standard_input"
        assert merged_output.name == "standard_input"

    def test_plan_explicit_output_schema_override(self) -> None:
        """Explicit output_schema on derived artifact overrides analyser's inferred schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        analyser_factory = create_mock_analyser_factory(
            "personal_data_analyser",
            [Schema("standard_input", "1.0.0")],
            [Schema("personal_data_finding", "1.0.0")],
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory},
            analyser_factories={"personal_data_analyser": analyser_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "findings": {
                    "inputs": "source",
                    "transform": {
                        "type": "personal_data_analyser",
                        "properties": {},
                    },
                    "output_schema": "custom_output/2.0.0",
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["findings"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "2.0.0"

    def test_plan_source_artifact_with_output_schema_override(self) -> None:
        """Source artifact with explicit output_schema uses override instead of connector's schema."""
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
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output/1.0.0",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.name != "standard_input"


class TestSchemaStringParsing:
    """Tests for schema string parsing via output_schema override."""

    def test_parse_schema_string_without_version(self) -> None:
        """Schema string without version defaults to 1.0.0."""
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
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "1.0.0"

    def test_parse_schema_string_with_version(self) -> None:
        """Schema string with version uses explicit version."""
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
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output/2.0.0",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "2.0.0"


class TestPlannerErrors:
    """Tests for error handling scenarios."""

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
                    "transform": {"type": "unknown_analyser", "properties": {}},
                },
            },
        }

        with pytest.raises(ComponentNotFoundError) as exc_info:
            planner.plan_from_dict(runbook_data)

        assert "unknown_analyser" in str(exc_info.value)

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


class TestExecutionPlan:
    """Tests for the ExecutionPlan dataclass."""

    def test_execution_plan_immutable(self) -> None:
        """ExecutionPlan is frozen/immutable."""
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
            "artifacts": {"data": {"source": {"type": "filesystem", "properties": {}}}},
        }
        plan = planner.plan_from_dict(runbook_data)

        with pytest.raises(AttributeError):
            plan.runbook = None  # type: ignore[misc]
