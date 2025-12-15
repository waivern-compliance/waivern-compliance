"""Tests for nested child runbook composition in the Planner.

Fixtures for these tests are defined in conftest.py.
"""

from pathlib import Path

from waivern_core.services import ComponentRegistry

from waivern_orchestration.planner import Planner

from .test_helpers import write_runbook


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
