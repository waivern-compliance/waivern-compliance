"""Planner for artifact-centric runbook orchestration.

The Planner is responsible for:
1. Parsing runbooks and building the execution DAG
2. Validating references and schema compatibility
3. Producing an immutable ExecutionPlan
"""

from dataclasses import dataclass
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
from waivern_orchestration.models import ArtifactDefinition, Runbook
from waivern_orchestration.parser import parse_runbook, parse_runbook_from_dict


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable, validated execution plan.

    Contains all information needed by the executor to run the runbook:
    - The parsed and validated Runbook model
    - The ExecutionDAG for dependency ordering
    - Pre-resolved schemas for each artifact (input, output)
    """

    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema | None, Schema]]


class Planner:
    """Plans runbook execution by validating and resolving all dependencies upfront."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise Planner with component registry.

        Args:
            registry: ComponentRegistry for accessing component factories.

        """
        self._registry = registry

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
            ComponentNotFoundError: If connector/analyser type not found.
            SchemaCompatibilityError: If schemas are incompatible.

        """
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
            ComponentNotFoundError: If connector/analyser type not found.
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
        # Build DAG and validate for cycles
        dag = ExecutionDAG(runbook.artifacts)
        dag.validate()

        # Validate references and resolve schemas
        self._validate_refs(runbook)
        artifact_schemas = self._resolve_schemas(runbook, dag)

        return ExecutionPlan(
            runbook=runbook,
            dag=dag,
            artifact_schemas=artifact_schemas,
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
    ) -> dict[str, tuple[Schema | None, Schema]]:
        """Resolve input and output schemas for each artifact.

        Processes artifacts in topological order so dependencies are resolved first.

        Args:
            runbook: Runbook to resolve schemas for.
            dag: ExecutionDAG for topological ordering.

        Returns:
            Dict mapping artifact ID to (input_schema, output_schema) tuple.

        """
        result: dict[str, tuple[Schema | None, Schema]] = {}

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
            output_schema = self._parse_schema_string(definition.output_schema)
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
        resolved: dict[str, tuple[Schema | None, Schema]],
    ) -> tuple[Schema, Schema]:
        """Resolve schemas for a derived artifact.

        Args:
            artifact_id: The artifact ID (for error messages).
            definition: The artifact definition.
            resolved: Already-resolved schemas for upstream artifacts.

        Returns:
            Tuple of (input_schema, output_schema).

        Raises:
            ComponentNotFoundError: If analyser type not found.
            SchemaCompatibilityError: If fan-in inputs have incompatible schemas.

        """
        inputs = definition.inputs
        if inputs is None:
            raise ValueError(f"Artifact '{artifact_id}' has neither source nor inputs")

        # Get all input schemas and validate fan-in compatibility
        input_refs = [inputs] if isinstance(inputs, str) else inputs
        input_schema = self._validate_fan_in_schemas(artifact_id, input_refs, resolved)

        # Determine output schema - explicit override takes precedence
        if definition.output_schema is not None:
            output_schema = self._parse_schema_string(definition.output_schema)
        elif definition.transform is not None:
            output_schema = self._get_analyser_output_schema(definition.transform.type)
        else:
            # Pass-through: output equals input
            output_schema = input_schema

        return (input_schema, output_schema)

    def _validate_fan_in_schemas(
        self,
        artifact_id: str,
        input_refs: list[str],
        resolved: dict[str, tuple[Schema | None, Schema]],
    ) -> Schema:
        """Validate that all fan-in inputs have the same schema.

        Args:
            artifact_id: The artifact ID (for error messages).
            input_refs: List of upstream artifact IDs.
            resolved: Already-resolved schemas for upstream artifacts.

        Returns:
            The common input schema.

        Raises:
            SchemaCompatibilityError: If inputs have different schemas.

        """
        first_schema = resolved[input_refs[0]][1]

        for ref in input_refs[1:]:
            schema = resolved[ref][1]
            if (
                schema.name != first_schema.name
                or schema.version != first_schema.version
            ):
                raise SchemaCompatibilityError(
                    f"Artifact '{artifact_id}' has incompatible fan-in schemas: "
                    f"'{input_refs[0]}' produces {first_schema.name}/{first_schema.version}, "
                    f"but '{ref}' produces {schema.name}/{schema.version}. "
                    f"All fan-in inputs must have the same schema."
                )

        return first_schema

    def _parse_schema_string(self, schema_str: str) -> Schema:
        """Parse a schema string into a Schema object.

        Supports formats:
        - "schema_name" (defaults to version 1.0.0)
        - "schema_name/1.0.0" (explicit version)

        Args:
            schema_str: Schema string from runbook.

        Returns:
            Schema object.

        """
        if "/" in schema_str:
            name, version = schema_str.rsplit("/", 1)
        else:
            name = schema_str
            version = "1.0.0"
        return Schema(name, version)

    def _get_analyser_output_schema(self, analyser_type: str) -> Schema:
        """Get output schema from an analyser factory.

        Args:
            analyser_type: The analyser type name.

        Returns:
            The analyser's output schema.

        Raises:
            ComponentNotFoundError: If analyser type not found or has no output schemas.

        """
        if analyser_type not in self._registry.analyser_factories:
            raise ComponentNotFoundError(f"Analyser type '{analyser_type}' not found")

        factory = self._registry.analyser_factories[analyser_type]
        return self._get_first_output_schema(factory, f"Analyser '{analyser_type}'")

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
