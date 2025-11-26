"""Tests for ExecutionDAG - dependency graph building and validation."""

import pytest

from waivern_orchestration import (
    ArtifactDefinition,
    CycleDetectedError,
    SourceConfig,
    TransformConfig,
)
from waivern_orchestration.dag import ExecutionDAG


class TestExecutionDAGDependencies:
    """Tests for dependency tracking in ExecutionDAG."""

    def test_dag_linear_chain_dependencies(self) -> None:
        """Linear chain A → B → C: B depends on A, C depends on B."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
            "C": ArtifactDefinition(
                inputs="B", transform=TransformConfig(type="analyser")
            ),
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
                transform=TransformConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependencies("C") == {"A", "B"}

    def test_dag_fan_out_dependents(self) -> None:
        """Fan-out: A → B and A → C means get_dependents(A) returns {B, C}."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
            "C": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
        }

        dag = ExecutionDAG(artifacts)

        assert dag.get_dependents("A") == {"B", "C"}


class TestExecutionDAGExecutionOrder:
    """Tests for topological execution order."""

    def test_dag_linear_chain_execution_order(self) -> None:
        """Linear chain A → B → C: sorter yields A first, then B, then C."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
            "B": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
            "C": ArtifactDefinition(
                inputs="B", transform=TransformConfig(type="analyser")
            ),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.get_sorter()

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
        sorter = dag.get_sorter()

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
                transform=TransformConfig(type="merger"),
            ),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.get_sorter()

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

    def test_dag_get_sorter_returns_prepared_sorter(self) -> None:
        """get_sorter() returns a usable TopologicalSorter that can iterate."""
        artifacts = {
            "A": ArtifactDefinition(source=SourceConfig(type="filesystem")),
        }

        dag = ExecutionDAG(artifacts)
        sorter = dag.get_sorter()

        # Should be able to use get_ready() without calling prepare()
        ready = sorter.get_ready()
        assert "A" in ready


class TestExecutionDAGCycleDetection:
    """Tests for cycle detection in artifact dependencies."""

    def test_dag_direct_cycle_raises_error(self) -> None:
        """Direct cycle A → B → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(
                inputs="B", transform=TransformConfig(type="analyser")
            ),
            "B": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()

    def test_dag_indirect_cycle_raises_error(self) -> None:
        """Indirect cycle A → B → C → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(
                inputs="C", transform=TransformConfig(type="analyser")
            ),
            "B": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
            "C": ArtifactDefinition(
                inputs="B", transform=TransformConfig(type="analyser")
            ),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()

    def test_dag_self_reference_raises_error(self) -> None:
        """Self-reference A → A: validate() raises CycleDetectedError."""
        artifacts = {
            "A": ArtifactDefinition(
                inputs="A", transform=TransformConfig(type="analyser")
            ),
        }

        dag = ExecutionDAG(artifacts)

        with pytest.raises(CycleDetectedError):
            dag.validate()


class TestExecutionDAGEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_dag_empty_artifacts(self) -> None:
        """Empty artifacts dict creates valid DAG with nothing to execute."""
        artifacts: dict[str, ArtifactDefinition] = {}

        dag = ExecutionDAG(artifacts)
        dag.validate()  # Should not raise

        sorter = dag.get_sorter()
        assert not sorter.is_active()  # Nothing to process
