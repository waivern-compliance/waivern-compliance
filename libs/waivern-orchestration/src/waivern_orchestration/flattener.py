"""Child runbook flattener for plan-time composition.

The ChildRunbookFlattener handles the expansion of child runbook directives
into the parent's artifact structure. This is a plan-time operation that:
1. Resolves child runbook paths with security constraints
2. Validates input mappings and schema compatibility
3. Namespaces child artifacts to avoid collisions
4. Creates aliases for output mapping
"""

from pathlib import Path

from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.errors import (
    CircularRunbookError,
    InvalidOutputMappingError,
    MissingInputMappingError,
    SchemaCompatibilityError,
)
from waivern_orchestration.models import ArtifactDefinition, ChildRunbookConfig, Runbook
from waivern_orchestration.parser import parse_runbook
from waivern_orchestration.path_resolver import resolve_child_runbook_path
from waivern_orchestration.utils import (
    create_namespaced_id,
    generate_namespace,
    parse_schema_string,
)

# Type alias for queue items: (artifact_id, definition, parent_path, ancestors, context_remap)
_QueueItem = tuple[
    str, ArtifactDefinition, Path | None, frozenset[Path], dict[str, str]
]


class ChildRunbookFlattener:
    """Flattens child runbooks into parent artifact structure at plan time."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise flattener with component registry.

        Args:
            registry: ComponentRegistry for schema resolution.

        """
        self._registry = registry

        # Operation state (reset per flatten call)
        self._queue: list[_QueueItem] = []
        self._flattened: dict[str, ArtifactDefinition] = {}
        self._aliases: dict[str, str] = {}
        self._runbook: Runbook | None = None

    def flatten(
        self,
        runbook: Runbook,
        runbook_path: Path | None,
    ) -> tuple[dict[str, ArtifactDefinition], dict[str, str]]:
        """Flatten child runbooks into parent artifacts.

        Uses an iterative queue-based approach to handle nested composition.

        Args:
            runbook: The parent runbook to flatten.
            runbook_path: Path to the runbook file (for resolving child paths).

        Returns:
            Tuple of (flattened_artifacts, aliases).

        Raises:
            CircularRunbookError: If circular runbook references detected.
            MissingInputMappingError: If required child inputs are not mapped.
            InvalidOutputMappingError: If output references non-existent artifact.
            SchemaCompatibilityError: If parent artifact schema mismatches child input.

        """
        # Reset operation state
        self._queue = []
        self._flattened = {}
        self._aliases = {}
        self._runbook = runbook

        # Initial ancestor set includes the root runbook
        initial_ancestors: frozenset[Path] = frozenset()
        if runbook_path:
            initial_ancestors = frozenset([runbook_path.resolve()])

        # Seed queue with parent artifacts (no context remapping at root level)
        for artifact_id, definition in runbook.artifacts.items():
            self._queue.append(
                (artifact_id, definition, runbook_path, initial_ancestors, {})
            )

        while self._queue:
            artifact_id, definition, parent_path, ancestor_paths, context_remapping = (
                self._queue.pop(0)
            )

            if definition.child_runbook is None:
                # Regular artifact - add to flattened (resolve aliases in inputs)
                resolved_def = self._resolve_aliases_in_definition(definition)
                self._flattened[artifact_id] = resolved_def
            else:
                # Child runbook directive - need to expand
                self._expand_child_runbook(
                    artifact_id=artifact_id,
                    child_config=definition.child_runbook,
                    parent_path=parent_path,
                    ancestor_paths=ancestor_paths,
                    context_remapping=context_remapping,
                )

        return self._flattened, self._aliases

    def _expand_child_runbook(
        self,
        *,
        artifact_id: str,
        child_config: ChildRunbookConfig,
        parent_path: Path | None,
        ancestor_paths: frozenset[Path],
        context_remapping: dict[str, str],
    ) -> None:
        """Expand a child runbook directive into queued artifacts.

        Args:
            artifact_id: The parent artifact ID with child_runbook directive.
            child_config: The child runbook configuration.
            parent_path: Path to the parent runbook file.
            ancestor_paths: Ancestor runbook paths for circular detection.
            context_remapping: Input name to artifact ID mapping for this level.

        """
        if self._runbook is None:
            raise ValueError("Runbook not set - call flatten() first")

        # Resolve child runbook path
        if parent_path is None:
            raise ValueError(
                f"Cannot resolve child runbook path '{child_config.path}' "
                "without parent runbook path"
            )

        child_path = resolve_child_runbook_path(
            child_config.path,
            parent_path,
            self._runbook.config.template_paths,
        )

        # Check for circular references (in ancestor chain only)
        resolved_child = child_path.resolve()
        if resolved_child in ancestor_paths:
            raise CircularRunbookError(
                f"Circular runbook reference detected: {child_path}"
            )

        # Parse child runbook
        child_runbook = parse_runbook(child_path)

        # Resolve input_mapping values through context and aliases
        resolved_input_mapping = self._resolve_input_mapping(
            child_config.input_mapping, context_remapping
        )

        # Validate input mapping (required inputs and schema compatibility)
        self._validate_input_mapping(artifact_id, resolved_input_mapping, child_runbook)

        # Validate output mapping and get alias mappings
        output_names = self._get_output_names(artifact_id, child_config, child_runbook)

        # Generate unique namespace for child artifacts
        namespace = generate_namespace(child_runbook.name)

        # Build input remapping for child artifacts
        child_input_remapping = dict(resolved_input_mapping)

        # New ancestor set for child artifacts includes this child
        child_ancestors = ancestor_paths | {resolved_child}

        # Add child artifacts to queue (namespaced)
        self._queue_child_artifacts(
            child_runbook=child_runbook,
            namespace=namespace,
            child_input_remapping=child_input_remapping,
            child_path=child_path,
            child_ancestors=child_ancestors,
        )

        # Create aliases for outputs
        # Note: child_runbook.outputs is guaranteed to be non-None here because
        # _get_output_names validates that outputs exist
        outputs = child_runbook.outputs
        if outputs is None:
            raise ValueError(
                "Child runbook outputs are None (should be validated earlier)"
            )
        for output_name, parent_alias in output_names.items():
            child_artifact = outputs[output_name].artifact
            namespaced_artifact = create_namespaced_id(namespace, child_artifact)
            self._aliases[parent_alias] = namespaced_artifact

    def _resolve_input_mapping(
        self,
        input_mapping: dict[str, str],
        context_remapping: dict[str, str],
    ) -> dict[str, str]:
        """Resolve input mapping through context and aliases.

        Args:
            input_mapping: Original input mapping from child config.
            context_remapping: Parent's declared inputs to resolved artifact IDs.

        Returns:
            Resolved input mapping with all indirections resolved.

        """
        resolved: dict[str, str] = {}
        for k, v in input_mapping.items():
            # First resolve through context remapping (parent's declared inputs)
            resolved_v = context_remapping.get(v, v)
            # Then resolve through aliases (sibling outputs)
            resolved_v = self._aliases.get(resolved_v, resolved_v)
            resolved[k] = resolved_v
        return resolved

    def _queue_child_artifacts(
        self,
        *,
        child_runbook: Runbook,
        namespace: str,
        child_input_remapping: dict[str, str],
        child_path: Path,
        child_ancestors: frozenset[Path],
    ) -> None:
        """Add child runbook artifacts to the processing queue.

        Args:
            child_runbook: The parsed child runbook.
            namespace: Unique namespace for child artifacts.
            child_input_remapping: Maps declared inputs to parent artifacts.
            child_path: Path to the child runbook file.
            child_ancestors: Ancestor paths including this child.

        """
        for child_artifact_id, child_def in child_runbook.artifacts.items():
            namespaced_id = create_namespaced_id(namespace, child_artifact_id)

            # Remap inputs: declared inputs → parent artifacts,
            # internal refs → namespaced versions
            remapped_inputs = self._remap_child_inputs(
                child_def.inputs,
                child_input_remapping,
                namespace,
                set(child_runbook.artifacts.keys()),
                set(child_runbook.inputs.keys()) if child_runbook.inputs else set(),
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

            self._queue.append(
                (
                    namespaced_id,
                    new_def,
                    child_path,
                    child_ancestors,
                    child_input_remapping,
                )
            )

    def _resolve_aliases_in_definition(
        self, definition: ArtifactDefinition
    ) -> ArtifactDefinition:
        """Resolve aliases in artifact definition inputs.

        Args:
            definition: The artifact definition.

        Returns:
            New ArtifactDefinition with aliases resolved in inputs.

        """
        if definition.inputs is None:
            return definition

        new_inputs = self._apply_remapping(definition.inputs, self._aliases)

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
    ) -> None:
        """Validate that all required child inputs are mapped and schemas are compatible.

        Args:
            artifact_id: Parent artifact ID (for error messages).
            input_mapping: Mapping from child input to parent artifact.
            child_runbook: The child runbook being invoked.

        Raises:
            MissingInputMappingError: If required input is not mapped.
            SchemaCompatibilityError: If parent artifact schema mismatches child input.

        """
        if not child_runbook.inputs:
            return

        if self._runbook is None:
            raise ValueError("Runbook not set - call flatten() first")

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
            if parent_artifact_id in self._flattened:
                parent_def = self._flattened[parent_artifact_id]
            elif parent_artifact_id in self._runbook.artifacts:
                parent_def = self._runbook.artifacts[parent_artifact_id]

            if parent_def is not None:
                parent_schema = self._get_artifact_output_schema(parent_def)
                if parent_schema is not None:
                    # Parse the child's declared input schema
                    child_schema = parse_schema_string(input_decl.input_schema)
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
            return parse_schema_string(definition.output_schema)

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
                return create_namespaced_id(namespace, inp)
            # Otherwise return as-is (shouldn't happen in valid runbooks)
            return inp

        if isinstance(inputs, str):
            return remap_single(inputs)
        return [remap_single(inp) for inp in inputs]
