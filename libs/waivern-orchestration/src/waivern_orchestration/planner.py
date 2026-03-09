"""Planner for artifact-centric runbook orchestration.

The Planner is responsible for:
1. Parsing runbooks and building the execution DAG
2. Validating references and schema compatibility
3. Delegating child runbook flattening to ChildRunbookFlattener
4. Producing an immutable ExecutionPlan
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from waivern_core.component_factory import ComponentFactory
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.dag import ExecutionDAG
from waivern_orchestration.errors import (
    ComponentNotFoundError,
    MissingArtifactError,
    SchemaCompatibilityError,
)
from waivern_orchestration.flattener import ChildRunbookFlattener
from waivern_orchestration.models import ArtifactDefinition, Runbook
from waivern_orchestration.parser import parse_runbook, parse_runbook_from_dict
from waivern_orchestration.utils import parse_schema_string


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable, validated execution plan.

    Contains all information needed by the executor to run the runbook:
    - The parsed and validated Runbook model
    - The ExecutionDAG for dependency ordering
    - Pre-resolved schemas for each artifact (input, output)
    - Aliases mapping parent artifact names to namespaced child artifacts
    - Reversed aliases for O(1) lookup from artifact ID to alias name
    """

    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[list[Schema] | None, Schema]]
    aliases: dict[str, str] = field(default_factory=dict)
    reversed_aliases: dict[str, str] = field(default_factory=dict)
    """Maps artifact IDs to alias names (reverse of aliases)."""


class Planner:
    """Plans runbook execution by validating and resolving all dependencies upfront."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise Planner with component registry.

        Args:
            registry: ComponentRegistry for accessing component factories.

        """
        self._registry = registry
        self._runbook_path: Path | None = None
        self._flattener = ChildRunbookFlattener(registry)

    def plan(self, runbook_path: Path) -> ExecutionPlan:
        """Plan execution from a runbook file.

        Args:
            runbook_path: Path to the runbook YAML file.

        Returns:
            Validated, immutable ExecutionPlan.

        Raises:
            RunbookParseError: If runbook cannot be parsed.
            CycleDetectedError: If dependency cycle detected.
            MissingArtifactError: If artifact reference is invalid.
            ComponentNotFoundError: If connector/processor type not found.
            SchemaCompatibilityError: If schemas are incompatible.
            CircularRunbookError: If circular runbook references detected.

        """
        self._runbook_path = runbook_path
        runbook = parse_runbook(runbook_path)
        return self._create_plan(runbook)

    def plan_from_dict(self, data: dict[str, Any]) -> ExecutionPlan:
        """Plan execution from a runbook dictionary.

        This function is useful for testing and programmatic runbook creation.
        It does NOT perform environment variable substitution.

        Args:
            data: Dictionary containing runbook configuration.

        Returns:
            Validated, immutable ExecutionPlan.

        Raises:
            RunbookParseError: If runbook structure is invalid.
            CycleDetectedError: If dependency cycle detected.
            MissingArtifactError: If artifact reference is invalid.
            ComponentNotFoundError: If connector/processor type not found.
            SchemaCompatibilityError: If schemas are incompatible.

        """
        runbook = parse_runbook_from_dict(data)
        return self._create_plan(runbook)

    def _create_plan(self, runbook: Runbook) -> ExecutionPlan:
        """Create an execution plan from a parsed runbook.

        Args:
            runbook: Parsed runbook model.

        Returns:
            Validated, immutable ExecutionPlan.

        """
        # Flatten child runbooks into parent artifacts
        flattened_artifacts, aliases = self._flattener.flatten(
            runbook, self._runbook_path
        )

        # Create a new runbook with flattened artifacts
        flattened_runbook = Runbook(
            name=runbook.name,
            description=runbook.description,
            contact=runbook.contact,
            config=runbook.config,
            inputs=runbook.inputs,
            outputs=runbook.outputs,
            artifacts=flattened_artifacts,
        )

        # Build DAG and validate for cycles
        dag = ExecutionDAG(flattened_artifacts)
        dag.validate()

        # Validate references and resolve schemas
        self._validate_refs(flattened_runbook)
        artifact_schemas = self._resolve_schemas(flattened_runbook, dag)

        # Pre-compute reversed aliases for O(1) lookup from artifact ID to alias
        reversed_aliases = {v: k for k, v in aliases.items()}

        return ExecutionPlan(
            runbook=flattened_runbook,
            dag=dag,
            artifact_schemas=artifact_schemas,
            aliases=aliases,
            reversed_aliases=reversed_aliases,
        )

    def _validate_refs(self, runbook: Runbook) -> None:
        """Validate all artifact references exist.

        Args:
            runbook: Runbook to validate.

        Raises:
            MissingArtifactError: If a referenced artifact doesn't exist.

        """
        artifact_ids = set(runbook.artifacts.keys())

        for artifact_id, definition in runbook.artifacts.items():
            if definition.inputs is not None:
                # Normalise inputs to a list
                inputs = (
                    [definition.inputs]
                    if isinstance(definition.inputs, str)
                    else definition.inputs
                )
                for ref in inputs:
                    if ref not in artifact_ids:
                        raise MissingArtifactError(
                            f"Artifact '{artifact_id}' references non-existent "
                            f"artifact '{ref}'"
                        )

    def _resolve_schemas(
        self, runbook: Runbook, dag: ExecutionDAG
    ) -> dict[str, tuple[list[Schema] | None, Schema]]:
        """Resolve input and output schemas for each artifact.

        Processes artifacts in topological order so dependencies are resolved first.

        Args:
            runbook: Runbook to resolve schemas for.
            dag: ExecutionDAG for topological ordering.

        Returns:
            Dict mapping artifact ID to (input_schema, output_schema) tuple.

        """
        result: dict[str, tuple[list[Schema] | None, Schema]] = {}

        sorter = dag.create_sorter()
        while sorter.is_active():
            for artifact_id in sorter.get_ready():
                definition = runbook.artifacts[artifact_id]

                if definition.source is not None:
                    schemas = self._resolve_source_schema(definition)
                else:
                    schemas = self._resolve_derived_schema(
                        artifact_id, definition, result
                    )

                result[artifact_id] = schemas
                sorter.done(artifact_id)

        return result

    def _resolve_source_schema(
        self, definition: ArtifactDefinition
    ) -> tuple[None, Schema]:
        """Resolve schema for a source artifact (connector).

        Args:
            definition: The artifact definition with source config.

        Returns:
            Tuple of (None, output_schema) - source artifacts have no input.

        Raises:
            ComponentNotFoundError: If connector type not found.

        """
        connector_type = definition.source.type  # type: ignore[union-attr]
        if connector_type not in self._registry.connector_factories:
            raise ComponentNotFoundError(f"Connector type '{connector_type}' not found")

        # Use explicit override if specified, otherwise infer from connector
        if definition.output_schema is not None:
            output_schema = parse_schema_string(definition.output_schema)
        else:
            factory = self._registry.connector_factories[connector_type]
            output_schema = self._get_first_output_schema(
                factory, f"Connector '{connector_type}'"
            )

        return (None, output_schema)

    def _resolve_derived_schema(
        self,
        artifact_id: str,
        definition: ArtifactDefinition,
        resolved: dict[str, tuple[list[Schema] | None, Schema]],
    ) -> tuple[list[Schema], Schema]:
        """Resolve schemas for a derived artifact.

        Args:
            artifact_id: The artifact ID (for error messages).
            definition: The artifact definition.
            resolved: Already-resolved schemas for upstream artifacts.

        Returns:
            Tuple of (input_schemas, output_schema).

        Raises:
            ComponentNotFoundError: If processor type not found.
            SchemaCompatibilityError: If fan-in inputs have incompatible schemas.

        """
        inputs = definition.inputs
        if inputs is None:
            raise ValueError(f"Artifact '{artifact_id}' has neither source nor inputs")

        # Get all input schemas and validate fan-in compatibility
        input_refs = [inputs] if isinstance(inputs, str) else inputs
        processor_type = (
            definition.process.type if definition.process is not None else None
        )
        input_schemas = self._validate_fan_in_schemas(
            artifact_id, input_refs, resolved, processor_type
        )

        # Determine output schema - explicit override takes precedence
        if definition.output_schema is not None:
            output_schema = parse_schema_string(definition.output_schema)
        elif definition.process is not None:
            output_schema = self._get_processor_output_schema(definition.process.type)
        else:
            # Pass-through: output equals input (only valid for single-schema)
            output_schema = input_schemas[0]

        return (input_schemas, output_schema)

    def _validate_fan_in_schemas(
        self,
        artifact_id: str,
        input_refs: list[str],
        resolved: dict[str, tuple[list[Schema] | None, Schema]],
        processor_type: str | None,
    ) -> list[Schema]:
        """Validate fan-in input schemas for compatibility.

        For same-schema fan-in (all inputs share one schema), returns a list
        containing that single schema. For multi-schema combinations (inputs
        produce different schemas), validates against the processor's declared
        input requirements and returns the list of unique schemas.

        Args:
            artifact_id: The artifact ID (for error messages).
            input_refs: List of upstream artifact IDs.
            resolved: Already-resolved schemas for upstream artifacts.
            processor_type: The processor type name, or None for pass-through.

        Returns:
            List of unique input schemas.

        Raises:
            SchemaCompatibilityError: If inputs have incompatible schemas
                that don't match any declared input requirement combination.

        """
        # Collect unique schemas preserving first occurrence order
        seen: set[tuple[str, str]] = set()
        unique_schemas: list[Schema] = []
        for ref in input_refs:
            schema = resolved[ref][1]
            key = (schema.name, schema.version)
            if key not in seen:
                seen.add(key)
                unique_schemas.append(schema)

        # Fast path: all inputs share the same schema (same-schema fan-in)
        if len(unique_schemas) == 1:
            return unique_schemas

        # Multiple distinct schemas — validate against processor requirements
        return self._validate_multi_schema_combination(
            artifact_id, unique_schemas, processor_type
        )

    def _validate_multi_schema_combination(
        self,
        artifact_id: str,
        unique_schemas: list[Schema],
        processor_type: str | None,
    ) -> list[Schema]:
        """Validate multi-schema inputs against processor's declared requirements.

        Args:
            artifact_id: The artifact ID (for error messages).
            unique_schemas: List of unique schemas from the inputs.
            processor_type: The processor type name, or None for pass-through.

        Returns:
            The validated list of unique schemas.

        Raises:
            SchemaCompatibilityError: If no matching combination is found
                or no processor is declared.

        """
        schema_desc = ", ".join(f"{s.name}/{s.version}" for s in unique_schemas)

        if processor_type is None:
            raise SchemaCompatibilityError(
                f"Artifact '{artifact_id}' has multiple input schema types "
                f"({schema_desc}) but no processor is declared. "
                f"Multi-schema inputs require a processor with matching "
                f"input requirements."
            )

        if processor_type not in self._registry.processor_factories:
            raise ComponentNotFoundError(f"Processor type '{processor_type}' not found")

        factory = self._registry.processor_factories[processor_type]
        requirements = factory.component_class.get_input_requirements()

        # Match input schema types against declared requirement combinations
        input_schema_set = frozenset((s.name, s.version) for s in unique_schemas)
        for combination in requirements:
            combination_set = frozenset((r.schema_name, r.version) for r in combination)
            if input_schema_set == combination_set:
                return unique_schemas

        raise SchemaCompatibilityError(
            f"Artifact '{artifact_id}' has input schema types ({schema_desc}) "
            f"that don't match any declared input requirement combination "
            f"for processor '{processor_type}'."
        )

    def _get_processor_output_schema(self, processor_type: str) -> Schema:
        """Get output schema from a processor factory.

        Args:
            processor_type: The processor type name.

        Returns:
            The processor's output schema.

        Raises:
            ComponentNotFoundError: If processor type not found or has no output schemas.

        """
        if processor_type not in self._registry.processor_factories:
            raise ComponentNotFoundError(f"Processor type '{processor_type}' not found")

        factory = self._registry.processor_factories[processor_type]
        return self._get_first_output_schema(factory, f"Processor '{processor_type}'")

    def _get_first_output_schema(
        self, factory: ComponentFactory[Any], component_desc: str
    ) -> Schema:
        """Get the first output schema from a component factory.

        Args:
            factory: The component factory.
            component_desc: Description for error messages (e.g., "Connector 'mysql'").

        Returns:
            The first output schema.

        Raises:
            ComponentNotFoundError: If factory has no output schemas.

        """
        output_schemas = factory.component_class.get_supported_output_schemas()
        if not output_schemas:
            raise ComponentNotFoundError(f"{component_desc} has no output schemas")
        return output_schemas[0]
