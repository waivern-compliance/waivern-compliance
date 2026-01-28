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
from waivern_orchestration.utils import get_origin_from_artifact_id

logger = logging.getLogger(__name__)


@dataclass
class _ExecutionContext:
    """Internal context for a single execution run."""

    run_id: str
    store: ArtifactStore
    semaphore: asyncio.Semaphore
    thread_pool: ThreadPoolExecutor
    results: dict[str, Message] = field(default_factory=dict)
    skipped: set[str] = field(default_factory=set)


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

        # Create thread pool for sync->async bridging
        logger.debug(
            "Creating ThreadPoolExecutor with max_workers=%d", config.max_concurrency
        )
        with ThreadPoolExecutor(max_workers=config.max_concurrency) as thread_pool:
            ctx = _ExecutionContext(
                run_id=run_id,
                store=store,
                semaphore=asyncio.Semaphore(config.max_concurrency),
                thread_pool=thread_pool,
            )

            try:
                async with asyncio.timeout(config.timeout):
                    await self._execute_dag(plan, ctx)
            except TimeoutError:
                # Mark all remaining artifacts as skipped due to timeout
                self._mark_remaining_as_skipped(plan, ctx)
                logger.warning("Execution timed out after %d seconds", config.timeout)

        logger.debug("ThreadPoolExecutor shutdown complete")
        total_duration = time.monotonic() - start_time
        return ExecutionResult(
            run_id=run_id,
            start_timestamp=start_timestamp,
            artifacts=ctx.results,
            skipped=ctx.skipped,
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
            # Get ready artifacts once (store result to avoid multiple calls)
            all_ready = list(sorter.get_ready())
            ready = [aid for aid in all_ready if aid not in ctx.skipped]

            # Mark skipped artifacts as done immediately so sorter can progress
            skipped_in_batch = [aid for aid in all_ready if aid in ctx.skipped]
            if skipped_in_batch:
                logger.debug("Marking skipped artifacts as done: %s", skipped_in_batch)
                for aid in skipped_in_batch:
                    sorter.done(aid)

            if not ready:
                continue

            logger.debug("Starting batch execution for artifacts: %s", ready)
            tasks = [self._produce(aid, plan, ctx) for aid in ready]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("Batch execution complete for artifacts: %s", ready)

            for aid, result in zip(ready, batch_results, strict=True):
                if isinstance(result, BaseException):
                    # Create error Message for unexpected exceptions
                    _, output_schema = plan.artifact_schemas[aid]
                    error_message = self._create_error_message(
                        artifact_id=aid,
                        schema=output_schema,
                        execution_context=ExecutionContext(
                            status="error",
                            error=str(result),
                            duration_seconds=0.0,
                            origin=self._determine_origin(aid),
                            alias=self._find_alias(aid, plan),
                        ),
                    )
                    ctx.results[aid] = error_message
                    # Skip all dependents of failed artifact
                    self._skip_dependents(aid, plan, ctx)
                else:
                    ctx.results[aid] = result
                    # Check if this artifact failed (status="error")
                    exec_ctx = (
                        result.extensions.execution if result.extensions else None
                    )
                    if exec_ctx and exec_ctx.status == "error":
                        self._skip_dependents(aid, plan, ctx)
                sorter.done(aid)

        logger.debug("DAG execution complete")

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

                await ctx.store.save(ctx.run_id, artifact_id, message)

                duration = time.monotonic() - start_time
                logger.debug(
                    "Artifact %s completed successfully (%.2fs)", artifact_id, duration
                )

                # Create new Message with execution context (don't mutate original)
                return replace(
                    message,
                    extensions=MessageExtensions(
                        execution=ExecutionContext(
                            status="success",
                            duration_seconds=duration,
                            origin=origin,
                            alias=alias,
                        )
                    ),
                )

            except Exception as e:
                duration = time.monotonic() - start_time
                logger.debug(
                    "Artifact %s failed: %s (%.2fs)", artifact_id, str(e), duration
                )
                if definition.optional:
                    logger.warning("Optional artifact '%s' failed: %s", artifact_id, e)

                return self._create_error_message(
                    artifact_id=artifact_id,
                    schema=output_schema,
                    execution_context=ExecutionContext(
                        status="error",
                        error=str(e),
                        duration_seconds=duration,
                        origin=origin,
                        alias=alias,
                    ),
                )

    def _skip_dependents(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Mark all dependents of a failed artifact as skipped (transitively)."""
        # Use iterative BFS to avoid stack overflow on deep chains
        to_skip = list(plan.dag.get_dependents(artifact_id))
        while to_skip:
            dep = to_skip.pop()
            if dep not in ctx.skipped:
                ctx.skipped.add(dep)
                # Add transitive dependents
                to_skip.extend(plan.dag.get_dependents(dep))

    def _mark_remaining_as_skipped(
        self,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Mark all artifacts not yet completed as skipped due to timeout."""
        all_artifacts = set(plan.runbook.artifacts.keys())
        completed = set(ctx.results.keys())
        remaining = all_artifacts - completed - ctx.skipped
        ctx.skipped.update(remaining)

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

    def _create_error_message(
        self,
        artifact_id: str,
        schema: Schema,
        execution_context: ExecutionContext,
    ) -> Message:
        """Create a Message representing a failed artifact execution.

        Args:
            artifact_id: The artifact ID that failed.
            schema: The intended output schema.
            execution_context: Pre-built execution context with error status.

        Returns:
            Message with empty content and error execution context.

        """
        return Message(
            id=str(uuid.uuid4()),
            content={},
            schema=schema,
            source=f"artifact:{artifact_id}",
            extensions=MessageExtensions(execution=execution_context),
        )
