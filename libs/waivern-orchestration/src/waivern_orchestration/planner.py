"""Planner for artifact-centric runbook orchestration.

The Planner is responsible for:
1. Parsing runbooks and building the execution DAG
2. Validating references and schema compatibility
3. Flattening child runbooks into a single execution plan
4. Producing an immutable ExecutionPlan
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from waivern_core.component_factory import ComponentFactory
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.dag import ExecutionDAG
from waivern_orchestration.errors import (
    CircularRunbookError,
    ComponentNotFoundError,
    InvalidOutputMappingError,
    MissingArtifactError,
    MissingInputMappingError,
    SchemaCompatibilityError,
)
from waivern_orchestration.models import ArtifactDefinition, ChildRunbookConfig, Runbook
from waivern_orchestration.parser import parse_runbook, parse_runbook_from_dict
from waivern_orchestration.path_resolver import resolve_child_runbook_path


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable, validated execution plan.

    Contains all information needed by the executor to run the runbook:
    - The parsed and validated Runbook model
    - The ExecutionDAG for dependency ordering
    - Pre-resolved schemas for each artifact (input, output)
    - Aliases mapping parent artifact names to namespaced child artifacts
    """

    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema | None, Schema]]
    aliases: dict[str, str] = field(default_factory=dict)


class Planner:
    """Plans runbook execution by validating and resolving all dependencies upfront."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise Planner with component registry.

        Args:
            registry: ComponentRegistry for accessing component factories.

        """
        self._registry = registry
        self._runbook_path: Path | None = None

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
        flattened_artifacts, aliases = self._flatten_child_runbooks(runbook)

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

        return ExecutionPlan(
            runbook=flattened_runbook,
            dag=dag,
            artifact_schemas=artifact_schemas,
            aliases=aliases,
        )

    def _flatten_child_runbooks(
        self, runbook: Runbook
    ) -> tuple[dict[str, ArtifactDefinition], dict[str, str]]:
        """Flatten child runbooks into parent artifacts.

        Uses an iterative queue-based approach to handle nested composition.

        Args:
            runbook: The parent runbook to flatten.

        Returns:
            Tuple of (flattened_artifacts, aliases).

        Raises:
            CircularRunbookError: If circular runbook references detected.
            MissingInputMappingError: If required child inputs are not mapped.
            InvalidOutputMappingError: If output references non-existent artifact.
            SchemaCompatibilityError: If parent artifact schema mismatches child input.

        """
        # Result containers
        flattened: dict[str, ArtifactDefinition] = {}
        aliases: dict[str, str] = {}

        # Queue of (artifact_id, definition, parent_runbook_path, ancestor_paths, context_remapping)
        # ancestor_paths tracks the call stack for circular detection
        # context_remapping maps declared input names to resolved artifact IDs at this level
        queue: list[
            tuple[str, ArtifactDefinition, Path | None, frozenset[Path], dict[str, str]]
        ] = []

        # Initial ancestor set includes the root runbook
        initial_ancestors: frozenset[Path] = frozenset()
        if self._runbook_path:
            initial_ancestors = frozenset([self._runbook_path.resolve()])

        # Seed queue with parent artifacts (no context remapping at root level)
        for artifact_id, definition in runbook.artifacts.items():
            queue.append(
                (artifact_id, definition, self._runbook_path, initial_ancestors, {})
            )

        while queue:
            artifact_id, definition, parent_path, ancestor_paths, context_remapping = (
                queue.pop(0)
            )

            if definition.child_runbook is None:
                # Regular artifact - add to flattened (resolve aliases in inputs)
                resolved_def = self._resolve_aliases_in_definition(definition, aliases)
                flattened[artifact_id] = resolved_def
            else:
                # Child runbook directive - need to expand
                child_config = definition.child_runbook

                # Resolve child runbook path
                if parent_path is None:
                    raise ValueError(
                        f"Cannot resolve child runbook path '{child_config.path}' "
                        "without parent runbook path"
                    )

                child_path = resolve_child_runbook_path(
                    child_config.path,
                    parent_path,
                    runbook.config.template_paths,
                )

                # Check for circular references (in ancestor chain only)
                resolved_child = child_path.resolve()
                if resolved_child in ancestor_paths:
                    raise CircularRunbookError(
                        f"Circular runbook reference detected: {child_path}"
                    )

                # Parse child runbook
                child_runbook = parse_runbook(child_path)

                # Resolve input_mapping values through:
                # 1. Context remapping (for nested runbooks - declared inputs from parent level)
                # 2. Aliases (for sibling dependencies)
                resolved_input_mapping: dict[str, str] = {}
                for k, v in child_config.input_mapping.items():
                    # First resolve through context remapping (parent's declared inputs)
                    resolved_v = context_remapping.get(v, v)
                    # Then resolve through aliases (sibling outputs)
                    resolved_v = aliases.get(resolved_v, resolved_v)
                    resolved_input_mapping[k] = resolved_v

                # Validate input mapping (required inputs and schema compatibility)
                # Pass original runbook artifacts for schema lookup (in case parent artifact
                # hasn't been added to flattened yet due to iteration order)
                self._validate_input_mapping(
                    artifact_id,
                    resolved_input_mapping,
                    child_runbook,
                    flattened,
                    runbook.artifacts,
                )

                # Validate output mapping and get alias mappings
                output_names = self._get_output_names(
                    artifact_id, child_config, child_runbook
                )

                # Generate unique namespace for child artifacts
                namespace = self._generate_namespace(child_runbook.name)

                # Build input remapping for child artifacts
                # Maps child declared input names to parent artifact IDs (with aliases resolved)
                child_input_remapping: dict[str, str] = {}
                for child_input, parent_artifact in resolved_input_mapping.items():
                    child_input_remapping[child_input] = parent_artifact

                # New ancestor set for child artifacts includes this child
                child_ancestors = ancestor_paths | {resolved_child}

                # Add child artifacts to queue (namespaced)
                for child_artifact_id, child_def in child_runbook.artifacts.items():
                    namespaced_id = f"{namespace}__{child_artifact_id}"

                    # Remap inputs: declared inputs → parent artifacts,
                    # internal refs → namespaced versions
                    remapped_inputs = self._remap_child_inputs(
                        child_def.inputs,
                        child_input_remapping,
                        namespace,
                        set(child_runbook.artifacts.keys()),
                        set(child_runbook.inputs.keys())
                        if child_runbook.inputs
                        else set(),
                    )

                    # Create new definition with remapped inputs
                    new_def = ArtifactDefinition(
                        name=child_def.name,
                        description=child_def.description,
                        contact=child_def.contact,
                        source=child_def.source,
                        inputs=remapped_inputs,
                        process=child_def.process,
                        merge=child_def.merge,
                        output_schema=child_def.output_schema,
                        output=child_def.output,
                        optional=child_def.optional,
                        execute=child_def.execute,
                        child_runbook=child_def.child_runbook,
                    )

                    queue.append(
                        (
                            namespaced_id,
                            new_def,
                            child_path,
                            child_ancestors,
                            child_input_remapping,
                        )
                    )

                # Create aliases for outputs
                for output_name, parent_alias in output_names.items():
                    child_artifact = child_runbook.outputs[output_name].artifact  # type: ignore[index]
                    namespaced_artifact = f"{namespace}__{child_artifact}"
                    aliases[parent_alias] = namespaced_artifact

        return flattened, aliases

    def _resolve_aliases_in_definition(
        self, definition: ArtifactDefinition, aliases: dict[str, str]
    ) -> ArtifactDefinition:
        """Resolve aliases in artifact definition inputs.

        Args:
            definition: The artifact definition.
            aliases: Dict mapping alias names to real artifact IDs.

        Returns:
            New ArtifactDefinition with aliases resolved in inputs.

        """
        if definition.inputs is None:
            return definition

        new_inputs = self._apply_remapping(definition.inputs, aliases)

        if new_inputs == definition.inputs:
            return definition

        return ArtifactDefinition(
            name=definition.name,
            description=definition.description,
            contact=definition.contact,
            source=definition.source,
            inputs=new_inputs,
            process=definition.process,
            merge=definition.merge,
            output_schema=definition.output_schema,
            output=definition.output,
            optional=definition.optional,
            execute=definition.execute,
            child_runbook=definition.child_runbook,
        )

    def _remap_artifact_inputs(
        self, definition: ArtifactDefinition, remapping: dict[str, str]
    ) -> ArtifactDefinition:
        """Remap artifact inputs based on remapping dict.

        Args:
            definition: The artifact definition.
            remapping: Dict mapping old input names to new ones.

        Returns:
            New ArtifactDefinition with remapped inputs.

        """
        if not remapping or definition.inputs is None:
            return definition

        new_inputs = self._apply_remapping(definition.inputs, remapping)

        return ArtifactDefinition(
            name=definition.name,
            description=definition.description,
            contact=definition.contact,
            source=definition.source,
            inputs=new_inputs,
            process=definition.process,
            merge=definition.merge,
            output_schema=definition.output_schema,
            output=definition.output,
            optional=definition.optional,
            execute=definition.execute,
            child_runbook=definition.child_runbook,
        )

    def _apply_remapping(
        self, inputs: str | list[str], remapping: dict[str, str]
    ) -> str | list[str]:
        """Apply input remapping to inputs.

        Args:
            inputs: Single input or list of inputs.
            remapping: Dict mapping old input names to new ones.

        Returns:
            Remapped inputs.

        """
        if isinstance(inputs, str):
            return remapping.get(inputs, inputs)
        return [remapping.get(inp, inp) for inp in inputs]

    def _validate_input_mapping(
        self,
        artifact_id: str,
        input_mapping: dict[str, str],
        child_runbook: Runbook,
        flattened: dict[str, ArtifactDefinition],
        original_artifacts: dict[str, ArtifactDefinition],
    ) -> None:
        """Validate that all required child inputs are mapped and schemas are compatible.

        Args:
            artifact_id: Parent artifact ID (for error messages).
            input_mapping: Mapping from child input to parent artifact.
            child_runbook: The child runbook being invoked.
            flattened: Already-flattened artifacts (for schema lookup).
            original_artifacts: Original runbook artifacts (fallback for schema lookup).

        Raises:
            MissingInputMappingError: If required input is not mapped.
            SchemaCompatibilityError: If parent artifact schema mismatches child input.

        """
        if not child_runbook.inputs:
            return

        for input_name, input_decl in child_runbook.inputs.items():
            if input_name not in input_mapping:
                if not input_decl.optional:
                    raise MissingInputMappingError(
                        f"Artifact '{artifact_id}': child runbook requires input "
                        f"'{input_name}' but it is not mapped"
                    )
                continue

            # Validate schema compatibility if we can resolve the parent's schema
            parent_artifact_id = input_mapping[input_name]

            # Look up parent definition from flattened first, then original artifacts
            parent_def: ArtifactDefinition | None = None
            if parent_artifact_id in flattened:
                parent_def = flattened[parent_artifact_id]
            elif parent_artifact_id in original_artifacts:
                parent_def = original_artifacts[parent_artifact_id]

            if parent_def is not None:
                parent_schema = self._get_artifact_output_schema(parent_def)
                if parent_schema is not None:
                    # Parse the child's declared input schema
                    child_schema = self._parse_schema_string(input_decl.input_schema)
                    if (
                        parent_schema.name != child_schema.name
                        or parent_schema.version != child_schema.version
                    ):
                        raise SchemaCompatibilityError(
                            f"Artifact '{artifact_id}': parent artifact "
                            f"'{parent_artifact_id}' produces schema "
                            f"'{parent_schema.name}/{parent_schema.version}', "
                            f"but child input '{input_name}' expects "
                            f"'{child_schema.name}/{child_schema.version}'"
                        )

    def _get_artifact_output_schema(
        self, definition: ArtifactDefinition
    ) -> Schema | None:
        """Get the output schema for an artifact definition.

        Args:
            definition: The artifact definition.

        Returns:
            The output schema, or None if it cannot be determined.

        """
        # If explicit output_schema is set, use it
        if definition.output_schema is not None:
            return self._parse_schema_string(definition.output_schema)

        # For source artifacts, get schema from connector factory
        if definition.source is not None:
            connector_type = definition.source.type
            if connector_type in self._registry.connector_factories:
                factory = self._registry.connector_factories[connector_type]
                schemas = factory.component_class.get_supported_output_schemas()
                if schemas:
                    return schemas[0]

        # For derived artifacts with process, get schema from processor factory
        if definition.process is not None:
            processor_type = definition.process.type
            if processor_type in self._registry.processor_factories:
                factory = self._registry.processor_factories[processor_type]
                schemas = factory.component_class.get_supported_output_schemas()
                if schemas:
                    return schemas[0]

        return None

    def _get_output_names(
        self,
        parent_artifact_id: str,
        child_config: ChildRunbookConfig,
        child_runbook: Runbook,
    ) -> dict[str, str]:
        """Get mapping of child output names to parent alias names.

        Args:
            parent_artifact_id: The parent artifact ID that invokes the child.
            child_config: The child runbook configuration.
            child_runbook: The parsed child runbook.

        Returns:
            Dict mapping child output name to parent alias name.

        Raises:
            InvalidOutputMappingError: If output references non-existent artifact.

        """
        result: dict[str, str] = {}

        if child_config.output is not None:
            # Single output mode - parent artifact ID becomes the alias
            output_name = child_config.output
            if not child_runbook.outputs or output_name not in child_runbook.outputs:
                raise InvalidOutputMappingError(
                    f"Output '{output_name}' not found in child runbook outputs"
                )
            result[output_name] = parent_artifact_id
        elif child_config.output_mapping is not None:
            # Multiple outputs mode
            for child_output, parent_alias in child_config.output_mapping.items():
                if (
                    not child_runbook.outputs
                    or child_output not in child_runbook.outputs
                ):
                    raise InvalidOutputMappingError(
                        f"Output '{child_output}' not found in child runbook outputs"
                    )
                result[child_output] = parent_alias

        return result

    def _generate_namespace(self, runbook_name: str) -> str:
        """Generate unique namespace for child runbook artifacts.

        Args:
            runbook_name: Name of the child runbook.

        Returns:
            Unique namespace string.

        """
        short_uuid = str(uuid.uuid4())[:8]
        # Clean runbook name for use in identifier
        clean_name = runbook_name.replace(" ", "_").replace("-", "_").lower()
        return f"{clean_name}__{short_uuid}"

    def _remap_child_inputs(
        self,
        inputs: str | list[str] | None,
        input_remapping: dict[str, str],
        namespace: str,
        child_artifact_ids: set[str],
        declared_input_names: set[str],
    ) -> str | list[str] | None:
        """Remap child artifact inputs.

        Declared inputs are remapped to parent artifacts.
        Internal references are namespaced.

        Args:
            inputs: The inputs to remap.
            input_remapping: Maps declared input names to parent artifacts.
            namespace: Namespace prefix for child artifacts.
            child_artifact_ids: Set of artifact IDs in the child runbook.
            declared_input_names: Set of declared input names.

        Returns:
            Remapped inputs.

        """
        if inputs is None:
            return None

        def remap_single(inp: str) -> str:
            # If it's a declared input, map to parent artifact
            if inp in declared_input_names:
                return input_remapping.get(inp, inp)
            # If it's an internal child artifact, namespace it
            if inp in child_artifact_ids:
                return f"{namespace}__{inp}"
            # Otherwise return as-is (shouldn't happen in valid runbooks)
            return inp

        if isinstance(inputs, str):
            return remap_single(inputs)
        return [remap_single(inp) for inp in inputs]

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
            ComponentNotFoundError: If processor type not found.
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
        elif definition.process is not None:
            output_schema = self._get_processor_output_schema(definition.process.type)
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
