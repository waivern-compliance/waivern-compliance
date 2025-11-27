"""Tests for the Planner class."""

from unittest.mock import MagicMock, patch

import pytest
from waivern_core.component_factory import ComponentFactory
from waivern_core.schemas import Schema

from waivern_orchestration import (
    ComponentNotFoundError,
    CycleDetectedError,
    MissingArtifactError,
    SchemaCompatibilityError,
)
from waivern_orchestration.planner import ExecutionPlan, Planner


def _create_mock_connector_factory(
    name: str, output_schemas: list[Schema]
) -> MagicMock:
    """Create a mock connector factory with specified output schemas."""
    factory = MagicMock(spec=ComponentFactory)
    factory.get_component_name.return_value = name
    factory.get_output_schemas.return_value = output_schemas
    factory.get_input_schemas.return_value = []
    return factory


def _create_mock_analyser_factory(
    name: str, input_schemas: list[Schema], output_schemas: list[Schema]
) -> MagicMock:
    """Create a mock analyser factory with specified schemas."""
    factory = MagicMock(spec=ComponentFactory)
    factory.get_component_name.return_value = name
    factory.get_input_schemas.return_value = input_schemas
    factory.get_output_schemas.return_value = output_schemas
    return factory


def _create_mock_entry_point(name: str, factory: MagicMock) -> MagicMock:
    """Create a mock entry point that returns the factory class."""
    ep = MagicMock()
    ep.name = name
    # entry_point.load() returns factory class, then () instantiates it
    factory_class = MagicMock(return_value=factory)
    ep.load.return_value = factory_class
    return ep


class TestPlannerHappyPath:
    """Tests for successful planning scenarios."""

    def test_plan_valid_source_artifact(self) -> None:
        """Planner can plan a runbook with a source artifact."""
        # Arrange: Create mock connector factory
        output_schema = Schema("standard_input", "1.0.0")
        connector_factory = _create_mock_connector_factory(
            "filesystem", [output_schema]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        # Mock entry_points to return our mock connector
        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            # Create runbook dict with single source artifact
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

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert
            assert isinstance(plan, ExecutionPlan)
            assert plan.runbook.name == "Test Runbook"
            assert "data_source" in plan.runbook.artifacts
            assert plan.dag is not None
            assert "data_source" in plan.artifact_schemas
            # Source artifact: input=None, output=connector's output schema
            input_schema, result_output_schema = plan.artifact_schemas["data_source"]
            assert input_schema is None
            assert result_output_schema.name == "standard_input"

    def test_plan_valid_derived_artifact_with_transform(self) -> None:
        """Planner can plan derived artifact with transform (source → analyser chain)."""
        # Arrange: Connector outputs standard_input, analyser consumes it and outputs findings
        connector_output = Schema("standard_input", "1.0.0")
        analyser_input = Schema("standard_input", "1.0.0")
        analyser_output = Schema("personal_data_finding", "1.0.0")

        connector_factory = _create_mock_connector_factory(
            "filesystem", [connector_output]
        )
        analyser_factory = _create_mock_analyser_factory(
            "personal_data_analyser", [analyser_input], [analyser_output]
        )

        connector_ep = _create_mock_entry_point("filesystem", connector_factory)
        analyser_ep = _create_mock_entry_point(
            "personal_data_analyser", analyser_factory
        )

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: {
                "waivern.connectors": [connector_ep],
                "waivern.analysers": [analyser_ep],
            }.get(group, [])

            planner = Planner()

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

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert
            assert isinstance(plan, ExecutionPlan)
            assert "data_source" in plan.artifact_schemas
            assert "findings" in plan.artifact_schemas

            # Source: input=None, output=connector's output
            source_input, source_output = plan.artifact_schemas["data_source"]
            assert source_input is None
            assert source_output.name == "standard_input"

            # Derived: input=upstream output, output=analyser's output
            derived_input, derived_output = plan.artifact_schemas["findings"]
            assert derived_input is not None
            assert derived_input.name == "standard_input"
            assert derived_output.name == "personal_data_finding"

    def test_plan_derived_artifact_without_transform_passthrough(self) -> None:
        """Derived artifact without transform passes schema through (no analyser)."""
        # Arrange: Source artifact, derived artifact with no transform
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Passthrough test",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "passthrough": {
                        "inputs": "source",
                        # No transform - should pass schema through
                    },
                },
            }

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: passthrough artifact has same schema as source
            _, source_output = plan.artifact_schemas["source"]
            pass_input, pass_output = plan.artifact_schemas["passthrough"]

            assert source_output.name == "standard_input"
            assert pass_input is not None
            assert pass_input.name == "standard_input"  # Input = upstream output
            assert pass_output.name == "standard_input"  # Output = input (passthrough)

    def test_plan_fan_in_compatible_schemas(self) -> None:
        """Fan-in works when all inputs have same schema."""
        # Arrange: Two source artifacts feeding into one derived artifact
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

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
                        "inputs": ["source_a", "source_b"],  # Fan-in
                        # No transform - passthrough
                    },
                },
            }

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: merged artifact uses first input's schema
            merged_input, merged_output = plan.artifact_schemas["merged"]
            assert merged_input is not None
            assert merged_input.name == "standard_input"
            assert merged_output.name == "standard_input"

    def test_plan_explicit_output_schema_override(self) -> None:
        """Explicit output_schema on derived artifact overrides analyser's inferred schema."""
        # Arrange: Analyser outputs "finding" but artifact overrides to "custom_output"
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        analyser_factory = _create_mock_analyser_factory(
            "personal_data_analyser",
            [Schema("standard_input", "1.0.0")],
            [Schema("personal_data_finding", "1.0.0")],
        )

        connector_ep = _create_mock_entry_point("filesystem", connector_factory)
        analyser_ep = _create_mock_entry_point(
            "personal_data_analyser", analyser_factory
        )

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: {
                "waivern.connectors": [connector_ep],
                "waivern.analysers": [analyser_ep],
            }.get(group, [])

            planner = Planner()

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
                        "output_schema": "custom_output/2.0.0",  # Override analyser
                    },
                },
            }

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: override used, NOT analyser's "personal_data_finding"
            _, output_schema = plan.artifact_schemas["findings"]
            assert output_schema.name == "custom_output"
            assert output_schema.version == "2.0.0"

    def test_plan_source_artifact_with_output_schema_override(self) -> None:
        """Source artifact with explicit output_schema uses override instead of connector's schema."""
        # Arrange: Connector declares "standard_input" but artifact overrides to "custom_output"
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "data": {
                        "source": {"type": "filesystem", "properties": {}},
                        "output_schema": "custom_output/1.0.0",  # Override connector's schema
                    }
                },
            }

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: override used, NOT connector's "standard_input"
            _, output_schema = plan.artifact_schemas["data"]
            assert output_schema.name == "custom_output"
            assert output_schema.name != "standard_input"


class TestSchemaStringParsing:
    """Tests for schema string parsing via output_schema override."""

    def test_parse_schema_string_without_version(self) -> None:
        """Schema string without version defaults to 1.0.0."""
        # Arrange
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            # output_schema without version
            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "data": {
                        "source": {"type": "filesystem", "properties": {}},
                        "output_schema": "custom_output",  # No version specified
                    }
                },
            }

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: should default to version 1.0.0
            _, output_schema = plan.artifact_schemas["data"]
            assert output_schema.name == "custom_output"
            assert output_schema.version == "1.0.0"

    def test_parse_schema_string_with_version(self) -> None:
        """Schema string with version uses explicit version."""
        # Arrange
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            # output_schema with explicit version
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

            # Act
            plan = planner.plan_from_dict(runbook_data)

            # Assert: should use specified version
            _, output_schema = plan.artifact_schemas["data"]
            assert output_schema.name == "custom_output"
            assert output_schema.version == "2.0.0"


class TestPlannerErrors:
    """Tests for error handling scenarios."""

    def test_plan_connector_not_found(self) -> None:
        """Unknown connector type raises ComponentNotFoundError."""
        # Arrange: No connectors registered
        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: []  # No components

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "data": {"source": {"type": "unknown_connector", "properties": {}}}
                },
            }

            # Act & Assert
            with pytest.raises(ComponentNotFoundError) as exc_info:
                planner.plan_from_dict(runbook_data)

            assert "unknown_connector" in str(exc_info.value)

    def test_plan_analyser_not_found(self) -> None:
        """Unknown analyser type raises ComponentNotFoundError."""
        # Arrange: Connector exists but analyser doesn't
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

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

            # Act & Assert
            with pytest.raises(ComponentNotFoundError) as exc_info:
                planner.plan_from_dict(runbook_data)

            assert "unknown_analyser" in str(exc_info.value)

    def test_plan_missing_artifact_reference(self) -> None:
        """Invalid inputs reference raises MissingArtifactError."""
        # Arrange
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "derived": {
                        "inputs": "nonexistent_artifact",  # Invalid reference
                    },
                },
            }

            # Act & Assert
            with pytest.raises(MissingArtifactError) as exc_info:
                planner.plan_from_dict(runbook_data)

            assert "nonexistent_artifact" in str(exc_info.value)

    def test_plan_cycle_detected(self) -> None:
        """Cycle in dependencies raises CycleDetectedError."""
        # Arrange
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()

            # Cycle: a → b → c → a
            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "a": {"inputs": "c"},  # a depends on c
                    "b": {"inputs": "a"},  # b depends on a
                    "c": {"inputs": "b"},  # c depends on b (cycle!)
                },
            }

            # Act & Assert
            with pytest.raises(CycleDetectedError):
                planner.plan_from_dict(runbook_data)

    def test_plan_fan_in_incompatible_schemas_different_name(self) -> None:
        """Fan-in with different schema names raises SchemaCompatibilityError."""
        # Arrange: Two sources with different schema names
        connector_a = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_b = _create_mock_connector_factory(
            "database", [Schema("database_schema", "1.0.0")]
        )

        ep_a = _create_mock_entry_point("filesystem", connector_a)
        ep_b = _create_mock_entry_point("database", connector_b)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [ep_a, ep_b] if group == "waivern.connectors" else []
            )

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Fan-in incompatible test",
                "artifacts": {
                    "source_a": {"source": {"type": "filesystem", "properties": {}}},
                    "source_b": {"source": {"type": "database", "properties": {}}},
                    "merged": {
                        "inputs": ["source_a", "source_b"],  # Different schemas!
                    },
                },
            }

            # Act & Assert
            with pytest.raises(SchemaCompatibilityError) as exc_info:
                planner.plan_from_dict(runbook_data)

            assert "merged" in str(exc_info.value)
            assert "standard_input" in str(exc_info.value)
            assert "database_schema" in str(exc_info.value)

    def test_plan_fan_in_incompatible_schemas_different_version(self) -> None:
        """Fan-in with same schema name but different versions raises SchemaCompatibilityError."""
        # Arrange: Two sources with same name but different versions
        connector_v1 = _create_mock_connector_factory(
            "filesystem_v1", [Schema("standard_input", "1.0.0")]
        )
        connector_v2 = _create_mock_connector_factory(
            "filesystem_v2", [Schema("standard_input", "2.0.0")]
        )

        ep_v1 = _create_mock_entry_point("filesystem_v1", connector_v1)
        ep_v2 = _create_mock_entry_point("filesystem_v2", connector_v2)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [ep_v1, ep_v2] if group == "waivern.connectors" else []
            )

            planner = Planner()

            runbook_data = {
                "name": "Test",
                "description": "Fan-in version mismatch test",
                "artifacts": {
                    "source_v1": {
                        "source": {"type": "filesystem_v1", "properties": {}}
                    },
                    "source_v2": {
                        "source": {"type": "filesystem_v2", "properties": {}}
                    },
                    "merged": {
                        "inputs": [
                            "source_v1",
                            "source_v2",
                        ],  # Same name, different version!
                    },
                },
            }

            # Act & Assert
            with pytest.raises(SchemaCompatibilityError) as exc_info:
                planner.plan_from_dict(runbook_data)

            assert "merged" in str(exc_info.value)
            assert "1.0.0" in str(exc_info.value)
            assert "2.0.0" in str(exc_info.value)


class TestExecutionPlan:
    """Tests for the ExecutionPlan dataclass."""

    def test_execution_plan_immutable(self) -> None:
        """ExecutionPlan is frozen/immutable."""
        # Arrange
        connector_factory = _create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        connector_ep = _create_mock_entry_point("filesystem", connector_factory)

        with patch("waivern_orchestration.planner.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [connector_ep] if group == "waivern.connectors" else []
            )

            planner = Planner()
            runbook_data = {
                "name": "Test",
                "description": "Test",
                "artifacts": {
                    "data": {"source": {"type": "filesystem", "properties": {}}}
                },
            }
            plan = planner.plan_from_dict(runbook_data)

            # Act & Assert: attempting to modify frozen dataclass raises error
            with pytest.raises(AttributeError):
                plan.runbook = None  # type: ignore[misc]
