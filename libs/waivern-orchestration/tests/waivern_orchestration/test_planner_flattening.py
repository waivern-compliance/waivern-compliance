"""Tests for child runbook flattening in the Planner."""

from pathlib import Path
from typing import Any

import pytest
import yaml
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
    create_mock_connector_factory,
    create_mock_processor_factory,
    create_mock_registry,
)


def write_runbook(path: Path, runbook: dict[str, object]) -> None:
    """Write a runbook dictionary to a YAML file."""
    path.write_text(yaml.dump(runbook))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def filesystem_connector_factory() -> ComponentFactory[Any]:
    """Factory for filesystem connector producing standard_input schema."""
    return create_mock_connector_factory(
        "filesystem", [Schema("standard_input", "1.0.0")]
    )


@pytest.fixture
def analyser_processor_factory() -> ComponentFactory[Any]:
    """Factory for analyser processor: standard_input → finding."""
    return create_mock_processor_factory(
        "analyser",
        [Schema("standard_input", "1.0.0")],
        [Schema("finding", "1.0.0")],
    )


@pytest.fixture
def summariser_processor_factory() -> ComponentFactory[Any]:
    """Factory for summariser processor: finding → summary."""
    return create_mock_processor_factory(
        "summariser",
        [Schema("finding", "1.0.0")],
        [Schema("summary", "1.0.0")],
    )


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


class TestBasicFlattening:
    """Tests for basic child runbook flattening."""

    def test_plan_simple_child_runbook(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Basic child runbook is flattened into parent plan."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child Runbook",
                "description": "A child runbook",
                "inputs": {
                    "source_data": {"input_schema": "standard_input/1.0.0"},
                },
                "outputs": {
                    "findings": {"artifact": "analysis"},
                },
                "artifacts": {
                    "analysis": {
                        "inputs": "source_data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        parent_path = tmp_path / "parent.yaml"
        write_runbook(
            parent_path,
            {
                "name": "Parent Runbook",
                "description": "Parent with child",
                "artifacts": {
                    "data": {"source": {"type": "filesystem", "properties": {}}},
                    "child_results": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"source_data": "data"},
                            "output": "findings",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Parent artifacts should still exist
        assert "data" in plan.artifact_schemas

        # Child artifacts should be namespaced
        child_artifact_ids = [
            aid for aid in plan.artifact_schemas if "child_runbook__" in aid.lower()
        ]
        assert len(child_artifact_ids) > 0

    def test_plan_child_runbook_artifacts_namespaced(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Child artifacts receive unique namespace to prevent collisions."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child Runbook",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"result": {"artifact": "processed"}},
                "artifacts": {
                    "processed": {
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
                    "child_output": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "result",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Child artifact "processed" should be namespaced
        namespaced_artifacts = [
            aid for aid in plan.artifact_schemas if "__" in aid and "processed" in aid
        ]
        assert len(namespaced_artifacts) == 1, (
            f"Expected one namespaced 'processed' artifact, "
            f"got: {list(plan.artifact_schemas.keys())}"
        )

    def test_plan_child_runbook_input_remapped_to_parent(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Child's declared inputs are remapped to parent artifacts."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"input_data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "result"}},
                "artifacts": {
                    "result": {
                        "inputs": "input_data",
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
                    "parent_source": {
                        "source": {"type": "filesystem", "properties": {}}
                    },
                    "child_result": {
                        "inputs": "parent_source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"input_data": "parent_source"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # The child's "result" artifact should depend on "parent_source"
        dag = plan.dag
        namespaced_result = next(
            aid for aid in plan.artifact_schemas if "result" in aid and "__" in aid
        )
        deps = dag.get_dependencies(namespaced_result)
        assert "parent_source" in deps

    def test_plan_child_runbook_internal_inputs_namespaced(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Child's internal artifact references are namespaced."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child with internal chain",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "step2"}},
                "artifacts": {
                    "step1": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                    "step2": {
                        "inputs": "step1",  # Internal reference
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

        # Both step1 and step2 should be namespaced
        namespaced = [aid for aid in plan.artifact_schemas if "__" in aid]
        assert any("step1" in aid for aid in namespaced)
        assert any("step2" in aid for aid in namespaced)

        # step2 should depend on namespaced step1, not raw "step1"
        step2_id = next(aid for aid in namespaced if "step2" in aid)
        deps = plan.dag.get_dependencies(step2_id)
        assert all("__" in dep or dep == "source" for dep in deps)

    def test_plan_child_runbook_output_aliased(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Child's output artifact creates alias in parent."""
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

        # ExecutionPlan should have aliases
        assert hasattr(plan, "aliases")
        assert "child_findings" in plan.aliases


class TestMultipleOutputs:
    """Tests for child runbooks with multiple outputs."""

    def test_plan_child_runbook_multiple_outputs(
        self, tmp_path: Path, registry_with_summariser: ComponentRegistry
    ) -> None:
        """output_mapping creates multiple aliases for child outputs."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Multi-Output Child",
                "description": "Child with multiple outputs",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {
                    "findings": {"artifact": "analysis"},
                    "summary": {"artifact": "summary"},
                },
                "artifacts": {
                    "analysis": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                    "summary": {
                        "inputs": "analysis",
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
                    "child_data": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output_mapping": {
                                "findings": "child_findings",
                                "summary": "child_summary",
                            },
                        },
                    },
                },
            },
        )

        planner = Planner(registry_with_summariser)
        plan = planner.plan(parent_path)

        # Both aliases should exist
        assert "child_findings" in plan.aliases
        assert "child_summary" in plan.aliases

    def test_plan_child_runbook_multiple_outputs_all_aliased(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Each mapped output in output_mapping creates an alias."""
        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {
                    "out1": {"artifact": "a1"},
                    "out2": {"artifact": "a2"},
                    "out3": {"artifact": "a3"},
                },
                "artifacts": {
                    "a1": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                    "a2": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                    "a3": {
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
                    "child": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output_mapping": {
                                "out1": "alias1",
                                "out2": "alias2",
                                "out3": "alias3",
                            },
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # All three aliases should exist
        assert "alias1" in plan.aliases
        assert "alias2" in plan.aliases
        assert "alias3" in plan.aliases


class TestNestedComposition:
    """Tests for nested child runbook composition."""

    def test_plan_nested_child_runbooks(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Child runbook can reference grandchild runbook."""
        grandchild_path = tmp_path / "grandchild.yaml"
        write_runbook(
            grandchild_path,
            {
                "name": "Grandchild",
                "description": "Grandchild",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"result": {"artifact": "processed"}},
                "artifacts": {
                    "processed": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        child_path = tmp_path / "child.yaml"
        write_runbook(
            child_path,
            {
                "name": "Child",
                "description": "Child",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"result": {"artifact": "grandchild_result"}},
                "artifacts": {
                    "grandchild_result": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./grandchild.yaml",
                            "input_mapping": {"data": "data"},
                            "output": "result",
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
                    "final_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./child.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "result",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Final alias should exist
        assert "final_result" in plan.aliases

        # Should have grandchild artifacts namespaced
        namespaced = [aid for aid in plan.artifact_schemas if "__" in aid]
        assert len(namespaced) >= 1  # At least the grandchild's "processed"

    def test_plan_deeply_nested_runbooks(
        self, tmp_path: Path, basic_registry: ComponentRegistry
    ) -> None:
        """Multiple levels of nesting work correctly."""
        level3_path = tmp_path / "level3.yaml"
        write_runbook(
            level3_path,
            {
                "name": "Level3",
                "description": "Level3",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "processed"}},
                "artifacts": {
                    "processed": {
                        "inputs": "data",
                        "process": {"type": "analyser", "properties": {}},
                    },
                },
            },
        )

        level2_path = tmp_path / "level2.yaml"
        write_runbook(
            level2_path,
            {
                "name": "Level2",
                "description": "Level2",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "l3_result"}},
                "artifacts": {
                    "l3_result": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./level3.yaml",
                            "input_mapping": {"data": "data"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        level1_path = tmp_path / "level1.yaml"
        write_runbook(
            level1_path,
            {
                "name": "Level1",
                "description": "Level1",
                "inputs": {"data": {"input_schema": "standard_input/1.0.0"}},
                "outputs": {"out": {"artifact": "l2_result"}},
                "artifacts": {
                    "l2_result": {
                        "inputs": "data",
                        "child_runbook": {
                            "path": "./level2.yaml",
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
                    "deep_result": {
                        "inputs": "source",
                        "child_runbook": {
                            "path": "./level1.yaml",
                            "input_mapping": {"data": "source"},
                            "output": "out",
                        },
                    },
                },
            },
        )

        planner = Planner(basic_registry)
        plan = planner.plan(parent_path)

        # Final alias should exist
        assert "deep_result" in plan.aliases


class TestFlatteningValidation:
    """Tests for validation during flattening."""

    def test_plan_circular_runbook_reference(
        self, tmp_path: Path, filesystem_connector_factory: ComponentFactory[Any]
    ) -> None:
        """Circular runbook reference (A→B→A) raises CircularRunbookError."""
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

        # aliases dict should map alias → namespaced artifact
        assert isinstance(plan.aliases, dict)
        assert "child_findings" in plan.aliases

        # The alias should point to a namespaced artifact
        target = plan.aliases["child_findings"]
        assert "__" in target


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
