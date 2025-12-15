"""Tests for validation and error handling in child runbook flattening.

Fixtures for these tests are defined in conftest.py.
"""

from pathlib import Path
from typing import Any

import pytest
from waivern_core.component_factory import ComponentFactory
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration import (
    CircularRunbookError,
    InvalidOutputMappingError,
    MissingInputMappingError,
    SchemaCompatibilityError,
)
from waivern_orchestration.planner import Planner

from .test_helpers import (
    create_mock_processor_factory,
    create_mock_registry,
    write_runbook,
)

# =============================================================================
# Validation Tests
# =============================================================================


class TestFlatteningValidation:
    """Tests for validation during flattening."""

    def test_plan_circular_runbook_reference(
        self, tmp_path: Path, filesystem_connector_factory: ComponentFactory[Any]
    ) -> None:
        """Circular runbook reference (A->B->A) raises CircularRunbookError."""
        child_a = tmp_path / "child_a.yaml"
        write_runbook(
            child_a,
            {
                "name": "ChildA",
                "description": "ChildA",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./child_b.yaml",
                            "input_mapping": {"data": "data"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        child_b = tmp_path / "child_b.yaml"
        write_runbook(
            child_b,
            {
                "name": "ChildB",
                "description": "ChildB",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./child_a.yaml",  # Circular!
                            "input_mapping": {"data": "data"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "circular": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child_a.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": filesystem_connector_factory}
        )

        planner = Planner(registry)
        with pytest.raises(CircularRunbookError):
            planner.plan(parent_path)

    def test_plan_missing_required_input_mapping(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Unmapped required input raises MissingInputMappingError."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child with required input",
                "inputs": {
                    "required_input": {"input_schema": "standard_input/1.0.0"},
                },
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "required_input",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "child_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {},  # Missing required input!
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        with pytest.raises(MissingInputMappingError) as exc_info:
            planner.plan(parent_path)

        assert "required_input" in str(exc_info.value)

    def test_plan_optional_input_not_mapped(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Optional inputs do not require mapping."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {
                    "required_data": {"input_schema": "standard_input/1.0.0"},
                    "optional_config": {
                        "input_schema": "config/1.0.0",
                        "optional": True,
                    },
                },
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "required_data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "child_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {
                                "required_data": "source"
                                # optional_config not mapped - should be fine
                            },
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        # Should not raise - optional input doesn't need mapping
        plan = planner.plan(parent_path)
        assert "child_result" in plan.aliases

    def test_plan_schema_mismatch_raises_error(
        self, tmp_path: Path, filesystem_connector_factory: ComponentFactory[Any]
    ) -> None:
        """Parent artifact schema mismatch with child input raises SchemaCompatibilityError."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child expecting specific schema",
                "inputs": {
                    "data": {"input_schema": "database_schema/1.0.0"},  # Expects DB
                },
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {
                        "source": {"type": "filesystem", "properties": {}}
                    },  # Produces standard_input
                    "child_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},  # Schema mismatch!
                            "output": "out",
                        },
                    },
                },
            },
        )

        # Custom registry: filesystem produces standard_input, analyser expects database_schema
        analyser_factory = create_mock_processor_factory(
            "analyser",
            [Schema("database_schema", "1.0.0")],
            [Schema("finding", "1.0.0")],
        )
        registry = create_mock_registry(
            connector_factories={"filesystem": filesystem_connector_factory},
            processor_factories={"analyser": analyser_factory},
        )

        planner = Planner(registry)
        with pytest.raises(SchemaCompatibilityError):
            planner.plan(parent_path)

    def test_plan_invalid_output_reference(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Output referencing non-existent child artifact raises InvalidOutputMappingError."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "child_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "nonexistent_output",  # Invalid!
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        with pytest.raises(InvalidOutputMappingError) as exc_info:
            planner.plan(parent_path)

        assert "nonexistent_output" in str(exc_info.value)


# =============================================================================
# Schema Resolution Tests
# =============================================================================


class TestSchemaResolution:
    """Tests for schema resolution in flattened plans."""

    def test_plan_child_artifact_schemas_resolved(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Flattened child artifacts have correctly resolved schemas."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "analysis"}},
                "artifacts": {
                    "analysis": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Find the namespaced analysis artifact
        analysis_id = next(
            aid for aid in plan.artifact_schemas if "analysis" in aid and "__" in aid
        )
        input_schema, output_schema = plan.artifact_schemas[analysis_id]

        assert input_schema is not None
        assert input_schema.name == "standard_input"
        assert output_schema.name == "finding"

    def test_plan_aliases_in_execution_plan(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """ExecutionPlan.aliases is populated with output aliases."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"findings": {"artifact": "analysis"}},
                "artifacts": {
                    "analysis": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "child_findings": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "findings",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # aliases dict should map alias -> namespaced artifact
        assert isinstance(plan.aliases, dict)
        assert "child_findings" in plan.aliases

        # The alias should point to a namespaced artifact
        target = plan.aliases["child_findings"]
        assert "__" in target


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in child runbook flattening."""

    def test_plan_child_with_default_input_value(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Default value is used when optional input is not mapped."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {
                    "data": {"input_schema": "standard_input/1.0.0"},
                    "config": {
                        "input_schema": "config/1.0.0",
                        "optional": True,
                        "default": {"threshold": 0.5},
                    },
                },
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "child_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            # config not mapped - should use default
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        # Should not raise - default value is used
        plan = planner.plan(parent_path)
        assert "child_result" in plan.aliases

    def test_plan_multiple_children_same_parent(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Parent can have multiple child runbook artifacts."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source1": {"source": {"type": "filesystem", "properties": {}}},
                    "source2": {"source": {"type": "filesystem", "properties": {}}},
                    "child1_result": {
                        "inputs": "source1",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source1"},
                            "output": "out",
                        },
                    },
                    "child2_result": {
                        "inputs": "source2",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source2"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Both child aliases should exist
        assert "child1_result" in plan.aliases
        assert "child2_result" in plan.aliases

        # They should point to different namespaced artifacts
        assert plan.aliases["child1_result"] != plan.aliases["child2_result"]

    def test_plan_child_output_used_by_sibling(
        self, tmp_path: Path, registry_with_summariser: ComponentRegistry
    ) -> None:
        """One child's output can be used by another child."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        # Second child that consumes finding schema
        consumer_child_path = tmp_path / "consumer.yaml"
        write_runbook(
            consumer_child_path,
            {
                "name": "Consumer",
                "description": "Consumer child",
                "inputs": {"findings": {"input_schema": "finding/1.0.0"}},
                "outputs": {"out": {"artifact": "summary"}},
                "artifacts": {
                    "summary": {
                        "inputs": "findings",
                        "process": {"type": "summariser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent",
                "description": "Parent",
                "artifacts": {
                    "source": {"source": {"type": "filesystem", "properties": {}}},
                    "first_child": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "out",
                        },
                    },
                    "second_child": {
                        "inputs": "first_child",  # Uses first child's output
                        "child_runbook": {
                            "path": "./consumer.yaml",
                            "input_mapping": {"findings": "first_child"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(registry_with_summariser)
        plan = planner.plan(parent_path)

        # Both aliases should exist
        assert "first_child" in plan.aliases
        assert "second_child" in plan.aliases

        # Second child should depend on first child's output
        second_target = plan.aliases["second_child"]
        deps = plan.dag.get_dependencies(second_target)
        # Should have a dependency chain that goes back to first_child's output
        assert len(deps) > 0
