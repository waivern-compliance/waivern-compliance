"""Tests for ExecutionDAG - dependency graph building and validation."""

import pytest

from waivern_orchestration import (
    ArtifactDefinition,
    CycleDetectedError,
    ProcessConfig,
    SourceConfig,
)
from waivern_orchestration.dag import ExecutionDAG


class TestExecutionDAGDependencies:
    """Tests for dependency tracking in ExecutionDAG."""

    def test_dag_linear_chain_dependencies(self) -> None:
        """Linear chain A → B → C: B depends on A, C depends on B."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(inputs="B", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependencies("A") == set()
        assert dag.get_dependencies("B") == {"A"}
        assert dag.get_dependencies("C") == {"B"}

    def test_dag_source_artifact_no_dependencies(self) -> None:
        """Source artifact (no inputs) has empty dependencies set."""
        artifacts = {
            "source": ArtifactDefinition(source=SourceConfig(type="filesystem")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependencies("source") == set()

    def test_dag_fan_in_multiple_inputs(self) -> None:
        """Fan-in artifact with inputs: [A, B] has both A and B as dependencies."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "C": ArtifactDefinition(
                inputs=["A", "B"],
                process=ProcessConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependencies("C") == {"A", "B"}

    def test_dag_fan_out_dependents(self) -> None:
        """Fan-out: A → B and A → C means get_dependents(A) returns {B, C}."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependents("A") == {"B", "C"}


class TestExecutionDAGExecutionOrder:
    """Tests for topological execution order."""

    def test_dag_linear_chain_execution_order(self) -> None:
        """Linear chain A → B → C: sorter yields A first, then B, then C."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(inputs="B", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.create_sorter()

        # Get execution order
        order = []
        while sorter.is_active():
            ready = sorter.get_ready()
            order.extend(ready)
            for item in ready:
                sorter.done(item)

        assert order == ["A", "B", "C"]

    def test_dag_parallel_independent_artifacts(self) -> None:
        """Multiple source artifacts (no dependencies) are all ready together."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "C": ArtifactDefinition(source=SourceConfig(type="sqlite")),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.create_sorter()

        # All three should be ready at once
        ready = sorter.get_ready()
        assert set(ready) == {"A", "B", "C"}

    def test_dag_fan_in_waits_for_all(self) -> None:
        """Fan-in artifact C (inputs: [A, B]) only ready after both A and B complete."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "C": ArtifactDefinition(
                inputs=["A", "B"],
                process=ProcessConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.create_sorter()

        # A and B ready first
        ready = sorter.get_ready()
        assert set(ready) == {"A", "B"}
        assert "C" not in ready

        # Complete A only - C still not ready
        sorter.done("A")
        ready = sorter.get_ready()
        assert "C" not in ready

        # Complete B - now C is ready
        sorter.done("B")
        ready = sorter.get_ready()
        assert "C" in ready

    def test_dag_create_sorter_returns_prepared_sorter(self) -> None:
        """create_sorter() returns a usable TopologicalSorter that can iterate."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.create_sorter()

        # Should be able to use get_ready() without calling prepare()
        ready = sorter.get_ready()
        assert "A" in ready


class TestExecutionDAGCycleDetection:
    """Tests for cycle detection in artifact dependencies."""

    def test_dag_direct_cycle_raises_error(self) -> None:
        """Direct cycle A → B → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(inputs="B", process=ProcessConfig(type="analyser")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()

    def test_dag_indirect_cycle_raises_error(self) -> None:
        """Indirect cycle A → B → C → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(inputs="C", process=ProcessConfig(type="analyser")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(inputs="B", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()

    def test_dag_self_reference_raises_error(self) -> None:
        """Self-reference A → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()


class TestExecutionDAGDepth:
    """Tests for DAG depth calculation."""

    def test_empty_dag_has_zero_depth(self) -> None:
        """Empty artifact dictionary results in depth 0."""
        artifacts: dict[str, ArtifactDefinition] = {}

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 0

    def test_single_source_artifact_has_depth_one(self) -> None:
        """Single source artifact has depth 1 (one level to execute)."""
        artifacts = {
            "source": ArtifactDefinition(source=SourceConfig(type="filesystem")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 1

    def test_parallel_sources_have_depth_one(self) -> None:
        """Multiple independent source artifacts execute in one level."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "C": ArtifactDefinition(source=SourceConfig(type="sqlite")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 1

    def test_linear_chain_depth_equals_chain_length(self) -> None:
        """Linear chain A → B → C has depth 3 (three sequential levels)."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(inputs="B", process=ProcessConfig(type="analyser")),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 3

    def test_fan_in_has_depth_two(self) -> None:
        """Fan-in pattern (A, B → C) has depth 2: sources then merger."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "C": ArtifactDefinition(
                inputs=["A", "B"],
                process=ProcessConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 2

    def test_complex_dag_depth_equals_longest_path(self) -> None:
        """Complex DAG depth is the longest path from any root to any leaf.

        Structure:
            A (source) → B (process) → D (process)
            C (source) ─────────────────↗

        Longest path is A → B → D = 3 levels.
        """
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(inputs="A", process=ProcessConfig(type="analyser")),
            "C": ArtifactDefinition(source=SourceConfig(type="mysql")),
            "D": ArtifactDefinition(
                inputs=["B", "C"],
                process=ProcessConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_depth() == 3


class TestExecutionDAGEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_dag_empty_artifacts(self) -> None:
        """Empty artifacts dict creates valid DAG with nothing to execute."""
        artifacts: dict[str, ArtifactDefinition] = {}

        dag = ExecutionDAG(artifacts)
        dag.validate()  # Should not raise

        sorter = dag.create_sorter()
        assert not sorter.is_active()  # Nothing to process
