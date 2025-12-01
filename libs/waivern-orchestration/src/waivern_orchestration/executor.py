"""DAG Executor for parallel artifact production.

The DAGExecutor executes artifacts in parallel using asyncio, respecting
dependency ordering from the ExecutionDAG. Sync components (connectors,
analysers) are bridged to async via ThreadPoolExecutor.
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from waivern_artifact_store.base import ArtifactStore
from waivern_core import Message, Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.models import (
    ArtifactDefinition,
    ArtifactResult,
    ExecutionResult,
    SourceConfig,
    TransformConfig,
)
from waivern_orchestration.planner import ExecutionPlan

logger = logging.getLogger(__name__)


@dataclass
class _ExecutionContext:
    """Internal context for a single execution run."""

    store: ArtifactStore
    semaphore: asyncio.Semaphore
    thread_pool: ThreadPoolExecutor
    results: dict[str, ArtifactResult] = field(default_factory=dict)
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
        start_time = time.monotonic()
        config = plan.runbook.config

        # Get fresh ArtifactStore from container (requires transient lifetime)
        store = self._registry.container.get_service(ArtifactStore)

        # Create thread pool for sync->async bridging
        with ThreadPoolExecutor(max_workers=config.max_concurrency) as thread_pool:
            ctx = _ExecutionContext(
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

        total_duration = time.monotonic() - start_time
        return ExecutionResult(
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
        sorter = plan.dag.get_sorter()

        while sorter.is_active():
            # Get ready artifacts once (store result to avoid multiple calls)
            all_ready = list(sorter.get_ready())
            ready = [aid for aid in all_ready if aid not in ctx.skipped]

            if not ready:
                # Mark skipped artifacts as done so sorter can progress
                for aid in all_ready:
                    sorter.done(aid)
                continue

            tasks = [self._produce(aid, plan, ctx) for aid in ready]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for aid, result in zip(ready, batch_results, strict=True):
                if isinstance(result, BaseException):
                    artifact_result = ArtifactResult(
                        artifact_id=aid,
                        success=False,
                        error=str(result),
                        duration_seconds=0.0,
                    )
                    ctx.results[aid] = artifact_result
                    # Skip all dependents of failed artifact
                    self._skip_dependents(aid, plan, ctx)
                else:
                    ctx.results[aid] = result
                    # Also check if this artifact failed (success=False)
                    if not result.success:
                        self._skip_dependents(aid, plan, ctx)
                sorter.done(aid)

    async def _produce(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> ArtifactResult:
        """Produce a single artifact."""
        start_time = time.monotonic()
        definition = plan.runbook.artifacts[artifact_id]

        async with ctx.semaphore:
            try:
                # Get schemas from pre-resolved schemas
                input_schema, output_schema = plan.artifact_schemas[artifact_id]

                if definition.source is not None:
                    message = await self._run_connector(
                        definition.source, output_schema, ctx.thread_pool
                    )
                else:
                    # Derived artifact - get inputs from store
                    if input_schema is None:
                        raise ValueError(
                            f"Derived artifact '{artifact_id}' has no input schema"
                        )
                    message = await self._produce_derived(
                        definition,
                        input_schema,
                        output_schema,
                        ctx.store,
                        ctx.thread_pool,
                    )

                ctx.store.save(artifact_id, message)

                duration = time.monotonic() - start_time
                return ArtifactResult(
                    artifact_id=artifact_id,
                    success=True,
                    message=message,
                    duration_seconds=duration,
                )

            except Exception as e:
                duration = time.monotonic() - start_time
                if definition.optional:
                    logger.warning("Optional artifact '%s' failed: %s", artifact_id, e)
                return ArtifactResult(
                    artifact_id=artifact_id,
                    success=False,
                    error=str(e),
                    duration_seconds=duration,
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

    async def _run_analyser(
        self,
        transform: TransformConfig,
        input_message: Message,
        input_schema: Schema,
        output_schema: Schema,
        thread_pool: ThreadPoolExecutor,
    ) -> Message:
        """Run an analyser in the thread pool.

        Args:
            transform: Transform configuration with analyser type and properties.
            input_message: The input message to process.
            input_schema: The input schema for validation.
            output_schema: The output schema for the result.
            thread_pool: ThreadPoolExecutor for sync->async bridging.

        Returns:
            Processed message from the analyser.

        Raises:
            KeyError: If analyser type not found in registry.

        """
        factory = self._registry.analyser_factories[transform.type]

        def sync_process() -> Message:
            analyser = factory.create(transform.properties)
            return analyser.process(input_schema, output_schema, input_message)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(thread_pool, sync_process)

    async def _produce_derived(
        self,
        definition: ArtifactDefinition,
        input_schema: Schema,
        output_schema: Schema,
        store: ArtifactStore,
        thread_pool: ThreadPoolExecutor,
    ) -> Message:
        """Produce a derived artifact from its inputs.

        Args:
            definition: The artifact definition with inputs.
            input_schema: The input schema for this artifact.
            output_schema: The output schema for this artifact.
            store: The artifact store containing upstream artifacts.
            thread_pool: ThreadPoolExecutor for sync->async bridging.

        Returns:
            The produced message.

        """
        # Get input artifact IDs
        inputs = definition.inputs
        if inputs is None:
            raise ValueError("Derived artifact has no inputs")

        input_refs = [inputs] if isinstance(inputs, str) else inputs

        # Retrieve input messages from store
        input_messages = [store.get(ref) for ref in input_refs]

        if definition.transform is not None:
            # Analyser requires single input (fan-in with transform deferred to Phase 2)
            if len(input_messages) != 1:
                raise NotImplementedError(
                    "Analyser with multiple inputs not yet supported (deferred to Phase 2)"
                )
            return await self._run_analyser(
                definition.transform,
                input_messages[0],
                input_schema,
                output_schema,
                thread_pool,
            )

        # Passthrough: use first input (or merge for fan-in)
        if len(input_messages) == 1:
            return input_messages[0]

        # Fan-in: merge messages - deferred to Phase 2
        raise NotImplementedError("Fan-in message merge not yet implemented")
