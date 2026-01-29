"""DAG Executor for parallel artifact production.

The DAGExecutor executes artifacts in parallel using asyncio, respecting
dependency ordering from the ExecutionDAG. Sync components (connectors,
processors) are bridged to async via ThreadPoolExecutor.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from waivern_artifact_store.base import ArtifactStore
from waivern_core import ExecutionContext, Message, MessageExtensions, Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.models import (
    ArtifactDefinition,
    ExecutionResult,
    ProcessConfig,
    SourceConfig,
)
from waivern_orchestration.planner import ExecutionPlan
from waivern_orchestration.state import ExecutionState
from waivern_orchestration.utils import get_origin_from_artifact_id

logger = logging.getLogger(__name__)


@dataclass
class _ExecutionContext:
    """Internal context for a single execution run."""

    run_id: str
    store: ArtifactStore
    state: ExecutionState
    semaphore: asyncio.Semaphore
    thread_pool: ThreadPoolExecutor
    results: dict[str, Message] = field(default_factory=dict)


class DAGExecutor:
    """Executes artifacts in parallel using asyncio with ThreadPoolExecutor bridge."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise executor with component registry.

        Args:
            registry: ComponentRegistry for accessing services and component factories.

        """
        self._registry = registry

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute artifacts in parallel according to the DAG.

        Args:
            plan: Validated ExecutionPlan from Planner.

        Returns:
            ExecutionResult containing artifact results and skipped artifacts.

        """
        # Generate run metadata at execution start
        run_id = str(uuid.uuid4())
        start_timestamp = datetime.now(UTC).isoformat()
        start_time = time.monotonic()
        config = plan.runbook.config

        # Get fresh ArtifactStore from container (requires transient lifetime)
        store = self._registry.container.get_service(ArtifactStore)

        # Create fresh execution state tracking all artifacts
        artifact_ids = set(plan.runbook.artifacts.keys())
        state = ExecutionState.fresh(artifact_ids)

        # Create thread pool for sync->async bridging
        logger.debug(
            "Creating ThreadPoolExecutor with max_workers=%d", config.max_concurrency
        )
        with ThreadPoolExecutor(max_workers=config.max_concurrency) as thread_pool:
            ctx = _ExecutionContext(
                run_id=run_id,
                store=store,
                state=state,
                semaphore=asyncio.Semaphore(config.max_concurrency),
                thread_pool=thread_pool,
            )

            try:
                async with asyncio.timeout(config.timeout):
                    await self._execute_dag(plan, ctx)
            except TimeoutError:
                # Mark all remaining artifacts as skipped due to timeout
                await self._mark_remaining_as_skipped(plan, ctx)
                logger.warning("Execution timed out after %d seconds", config.timeout)

        logger.debug("ThreadPoolExecutor shutdown complete")
        total_duration = time.monotonic() - start_time
        return ExecutionResult(
            run_id=run_id,
            start_timestamp=start_timestamp,
            artifacts=ctx.results,
            skipped=ctx.state.skipped,
            total_duration_seconds=total_duration,
        )

    async def _execute_dag(
        self,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Execute artifacts in topological order with parallel batches."""
        logger.debug("Starting DAG execution")
        sorter = plan.dag.create_sorter()

        while sorter.is_active():
            ready, skipped_in_batch = self._partition_ready_artifacts(
                list(sorter.get_ready()), ctx
            )

            # Mark skipped artifacts as done immediately so sorter can progress
            for aid in skipped_in_batch:
                sorter.done(aid)

            if not ready:
                continue

            logger.debug("Starting batch execution for artifacts: %s", ready)
            tasks = [self._produce(aid, plan, ctx) for aid in ready]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("Batch execution complete for artifacts: %s", ready)

            for aid, result in zip(ready, batch_results, strict=True):
                await self._handle_artifact_result(aid, result, plan, ctx)
                sorter.done(aid)

        logger.debug("DAG execution complete")

    def _partition_ready_artifacts(
        self,
        all_ready: list[str],
        ctx: _ExecutionContext,
    ) -> tuple[list[str], list[str]]:
        """Partition ready artifacts into executable and already-skipped.

        Returns:
            Tuple of (ready_to_execute, already_skipped).

        """
        ready = [aid for aid in all_ready if aid not in ctx.state.skipped]
        skipped = [aid for aid in all_ready if aid in ctx.state.skipped]

        if skipped:
            logger.debug("Marking skipped artifacts as done: %s", skipped)

        return ready, skipped

    async def _handle_artifact_result(
        self,
        artifact_id: str,
        result: Message | BaseException,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Handle the result of producing an artifact.

        Updates ctx.results with the message and persists state transitions.
        On failure, skips all dependent artifacts.

        """
        if isinstance(result, BaseException):
            message = self._create_error_message_for_exception(
                artifact_id, result, plan, ctx
            )
            ctx.results[artifact_id] = message
            await self._mark_failed_and_skip_dependents(artifact_id, plan, ctx)
        elif not result.is_success:
            # Artifact returned an error message (status != "success")
            ctx.results[artifact_id] = result
            await self._mark_failed_and_skip_dependents(artifact_id, plan, ctx)
        else:
            ctx.results[artifact_id] = result
            ctx.state.mark_completed(artifact_id)
            await ctx.state.save(ctx.store, ctx.run_id)

    def _create_error_message_for_exception(
        self,
        artifact_id: str,
        exception: BaseException,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> Message:
        """Create an error Message for an unexpected exception during production."""
        _, output_schema = plan.artifact_schemas[artifact_id]
        definition = plan.runbook.artifacts[artifact_id]

        return self._create_error_message(
            schema=output_schema,
            execution_context=ExecutionContext(
                status="error",
                error=str(exception),
                duration_seconds=0.0,
                origin=self._determine_origin(artifact_id),
                alias=self._find_alias(artifact_id, plan),
            ),
            run_id=ctx.run_id,
            source=self._determine_source(definition),
        )

    async def _mark_failed_and_skip_dependents(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Mark artifact as failed, persist state, and skip all dependents."""
        ctx.state.mark_failed(artifact_id)
        await ctx.state.save(ctx.store, ctx.run_id)
        await self._skip_dependents(artifact_id, plan, ctx)

    async def _produce(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> Message:
        """Produce a single artifact.

        Returns a Message with extensions.execution populated:
        - On success: status="success", the actual content
        - On failure: status="error", empty content

        """
        logger.debug("Starting production of artifact: %s", artifact_id)
        start_time = time.monotonic()
        definition = plan.runbook.artifacts[artifact_id]

        # Determine origin and alias for this artifact
        origin = self._determine_origin(artifact_id)
        alias = self._find_alias(artifact_id, plan)

        # Get schemas from pre-resolved schemas
        _input_schema, output_schema = plan.artifact_schemas[artifact_id]

        async with ctx.semaphore:
            try:
                if definition.source is not None:
                    message = await self._run_connector(
                        definition.source, output_schema, ctx.thread_pool
                    )
                else:
                    # Derived artifact - get inputs from store
                    message = await self._produce_derived(
                        definition,
                        output_schema,
                        ctx,
                    )

                # Determine source component type
                source = self._determine_source(definition)
                duration = time.monotonic() - start_time

                # Add all metadata to the message before saving
                message = replace(
                    message,
                    run_id=ctx.run_id,
                    source=source,
                    extensions=MessageExtensions(
                        execution=ExecutionContext(
                            status="success",
                            duration_seconds=duration,
                            origin=origin,
                            alias=alias,
                        )
                    ),
                )
                await ctx.store.save(ctx.run_id, artifact_id, message)

                logger.debug(
                    "Artifact %s completed successfully (%.2fs)", artifact_id, duration
                )

                return message

            except Exception as e:
                duration = time.monotonic() - start_time
                logger.debug(
                    "Artifact %s failed: %s (%.2fs)", artifact_id, str(e), duration
                )
                if definition.optional:
                    logger.warning("Optional artifact '%s' failed: %s", artifact_id, e)

                return self._create_error_message(
                    schema=output_schema,
                    execution_context=ExecutionContext(
                        status="error",
                        error=str(e),
                        duration_seconds=duration,
                        origin=origin,
                        alias=alias,
                    ),
                    run_id=ctx.run_id,
                    source=self._determine_source(definition),
                )

    async def _skip_dependents(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Mark all dependents of a failed artifact as skipped (transitively)."""
        # Collect all dependents to skip using BFS
        to_process = list(plan.dag.get_dependents(artifact_id))
        dependents_to_skip: set[str] = set()

        while to_process:
            dep = to_process.pop()
            if dep not in ctx.state.skipped and dep not in dependents_to_skip:
                dependents_to_skip.add(dep)
                # Add transitive dependents
                to_process.extend(plan.dag.get_dependents(dep))

        # Mark all collected dependents as skipped and persist
        if dependents_to_skip:
            ctx.state.mark_skipped(dependents_to_skip)
            await ctx.state.save(ctx.store, ctx.run_id)

    async def _mark_remaining_as_skipped(
        self,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Mark all artifacts not yet completed as skipped due to timeout."""
        all_artifacts = set(plan.runbook.artifacts.keys())
        completed = ctx.state.completed
        remaining = all_artifacts - completed - ctx.state.skipped - ctx.state.failed
        if remaining:
            ctx.state.mark_skipped(remaining)
            await ctx.state.save(ctx.store, ctx.run_id)

    async def _run_connector(
        self,
        source: SourceConfig,
        output_schema: Schema,
        thread_pool: ThreadPoolExecutor,
    ) -> Message:
        """Run a connector in the thread pool."""
        factory = self._registry.connector_factories[source.type]

        def sync_extract() -> Message:
            connector = factory.create(source.properties)
            return connector.extract(output_schema)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(thread_pool, sync_extract)

    async def _run_processor(
        self,
        process_config: ProcessConfig,
        inputs: list[Message],
        output_schema: Schema,
        thread_pool: ThreadPoolExecutor,
    ) -> Message:
        """Run a processor in the thread pool.

        Args:
            process_config: Process configuration with processor type and properties.
            inputs: List of input messages to process.
            output_schema: The output schema for the result.
            thread_pool: ThreadPoolExecutor for sync->async bridging.

        Returns:
            Processed message from the processor.

        Raises:
            KeyError: If processor type not found in registry.

        """
        factory = self._registry.processor_factories[process_config.type]

        def sync_process() -> Message:
            processor = factory.create(process_config.properties)
            return processor.process(inputs, output_schema)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(thread_pool, sync_process)

    async def _produce_derived(
        self,
        definition: ArtifactDefinition,
        output_schema: Schema,
        ctx: _ExecutionContext,
    ) -> Message:
        """Produce a derived artifact from its inputs.

        Args:
            definition: The artifact definition with inputs.
            output_schema: The output schema for this artifact.
            ctx: The execution context containing store, run_id, and thread pool.

        Returns:
            The produced message.

        """
        # Get input artifact IDs
        inputs = definition.inputs
        if inputs is None:
            raise ValueError("Derived artifact has no inputs")

        input_refs = [inputs] if isinstance(inputs, str) else inputs

        # Retrieve input messages from store (async)
        input_messages = [await ctx.store.get(ctx.run_id, ref) for ref in input_refs]

        if definition.process is not None:
            return await self._run_processor(
                definition.process,
                input_messages,
                output_schema,
                ctx.thread_pool,
            )

        # Passthrough: use first input (or merge for fan-in)
        if len(input_messages) == 1:
            return input_messages[0]

        # Fan-in: merge messages - deferred to Phase 2
        raise NotImplementedError("Fan-in message merge not yet implemented")

    def _determine_origin(self, artifact_id: str) -> str:
        """Determine the origin of an artifact based on its ID.

        Delegates to the shared utility function to ensure consistent
        namespace parsing across the codebase.

        Args:
            artifact_id: The artifact ID to check.

        Returns:
            'parent' for regular artifacts, 'child:{runbook_name}' for namespaced.

        """
        return get_origin_from_artifact_id(artifact_id)

    def _find_alias(self, artifact_id: str, plan: ExecutionPlan) -> str | None:
        """Find the alias name for an artifact if one exists.

        Uses the pre-computed reversed_aliases dict for O(1) lookup.

        Args:
            artifact_id: The artifact ID to find an alias for.
            plan: The execution plan containing aliases.

        Returns:
            The alias name if found, None otherwise.

        """
        return plan.reversed_aliases.get(artifact_id)

    def _determine_source(self, definition: ArtifactDefinition) -> str:
        """Determine the source component type for an artifact.

        Returns a string in the format 'connector:{type}' or 'processor:{type}'.

        Args:
            definition: The artifact definition.

        Returns:
            Source identifier string.

        """
        if definition.source is not None:
            return f"connector:{definition.source.type}"
        elif definition.process is not None:
            return f"processor:{definition.process.type}"
        else:
            return "unknown"

    def _create_error_message(
        self,
        schema: Schema,
        execution_context: ExecutionContext,
        run_id: str,
        source: str,
    ) -> Message:
        """Create a Message representing a failed artifact execution.

        Args:
            schema: The intended output schema.
            execution_context: Pre-built execution context with error status.
            run_id: The run identifier for correlation.
            source: The source component identifier.

        Returns:
            Message with empty content and error execution context.

        """
        return Message(
            id=str(uuid.uuid4()),
            content={},
            schema=schema,
            run_id=run_id,
            source=source,
            extensions=MessageExtensions(execution=execution_context),
        )
