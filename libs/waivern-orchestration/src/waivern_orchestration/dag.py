"""Execution DAG for artifact dependency management.

This module provides the ExecutionDAG class that builds and validates
the dependency graph from artifact definitions.
"""

from graphlib import CycleError, TopologicalSorter

from waivern_orchestration.errors import CycleDetectedError
from waivern_orchestration.models import ArtifactDefinition


class ExecutionDAG:
    """Directed Acyclic Graph for artifact execution ordering.

    Builds a dependency graph from artifact definitions and provides
    methods for topological traversal and dependency/dependent queries.
    """

    def __init__(self, artifacts: dict[str, ArtifactDefinition]) -> None:
        """Build the DAG from artifact definitions.

        Args:
            artifacts: Dictionary mapping artifact IDs to their definitions.

        """
        self._artifacts = artifacts
        self._graph: dict[str, set[str]] = {}
        self._reverse_graph: dict[str, set[str]] = {}

        self._build_graph()

    def _build_graph(self) -> None:
        """Build the forward and reverse dependency graphs."""
        # Initialise all artifacts with empty sets
        for artifact_id in self._artifacts:
            self._graph[artifact_id] = set()
            self._reverse_graph[artifact_id] = set()

        # Build dependencies from inputs field
        for artifact_id, definition in self._artifacts.items():
            deps = self._extract_dependencies(definition)
            self._graph[artifact_id] = deps

            # Build reverse graph for get_dependents()
            for dep in deps:
                if dep in self._reverse_graph:
                    self._reverse_graph[dep].add(artifact_id)

    def _extract_dependencies(self, definition: ArtifactDefinition) -> set[str]:
        """Extract dependency artifact IDs from an artifact definition.

        Args:
            definition: The artifact definition.

        Returns:
            Set of artifact IDs this artifact depends on.

        """
        if definition.inputs is None:
            return set()
        if isinstance(definition.inputs, str):
            return {definition.inputs}
        return set(definition.inputs)

    def validate(self) -> None:
        """Validate the DAG has no cycles.

        Raises:
            CycleDetectedError: If a cycle is detected in the dependency graph.

        """
        try:
            sorter = TopologicalSorter(self._graph)
            sorter.prepare()
        except CycleError as e:
            raise CycleDetectedError(
                f"Cycle detected in artifact dependencies: {e}"
            ) from e

    def create_sorter(self) -> TopologicalSorter[str]:
        """Create a new prepared TopologicalSorter for parallel execution.

        Each call creates a fresh sorter instance - the sorter is stateful
        and calling done() on one instance does not affect other instances.

        Returns:
            A new, prepared TopologicalSorter that can be used for parallel execution.

        Raises:
            CycleDetectedError: If a cycle is detected in the dependency graph.

        """
        self.validate()
        sorter: TopologicalSorter[str] = TopologicalSorter(self._graph)
        sorter.prepare()
        return sorter

    def get_dependencies(self, artifact_id: str) -> set[str]:
        """Get the artifacts that this artifact depends on.

        Args:
            artifact_id: The artifact ID to query.

        Returns:
            Set of artifact IDs that must complete before this artifact.

        """
        return self._graph.get(artifact_id, set())

    def get_dependents(self, artifact_id: str) -> set[str]:
        """Get the artifacts that depend on this artifact.

        Args:
            artifact_id: The artifact ID to query.

        Returns:
            Set of artifact IDs that depend on this artifact completing.

        """
        return self._reverse_graph.get(artifact_id, set())

    def get_depth(self) -> int:
        """Get the depth (number of levels) in the DAG.

        The depth is the number of sequential levels when traversing
        the DAG in topological order. Root nodes (no dependencies) are
        at level 0.

        Returns:
            The maximum depth of the DAG.

        Raises:
            CycleDetectedError: If a cycle is detected in the dependency graph.

        """
        if not self._artifacts:
            return 0

        sorter = self.create_sorter()
        depth = 0

        while sorter.is_active():
            ready = sorter.get_ready()
            ready_list = list(ready)
            if not ready_list:
                break
            for artifact_id in ready_list:
                sorter.done(artifact_id)
            depth += 1

        return depth
