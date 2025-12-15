"""Tests for basic child runbook flattening in the Planner.

This module contains:
- TestBasicFlattening: Core flattening functionality
- TestMultipleOutputs: Multiple output handling

Related test modules:
- test_planner_flattening_nested.py: Nested composition tests
- test_planner_flattening_validation.py: Validation and error handling

Fixtures for these tests are defined in conftest.py.
"""

from pathlib import Path

from waivern_core.services import ComponentRegistry

from waivern_orchestration.planner import Planner

from .test_helpers import write_runbook

# =============================================================================
# Basic Flattening Tests
# =============================================================================


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


# =============================================================================
# Multiple Outputs Tests
# =============================================================================


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
