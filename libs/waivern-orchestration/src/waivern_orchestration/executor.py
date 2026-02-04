"""DAG Executor for parallel artifact production.

The DAGExecutor executes artifacts in parallel using asyncio, respecting
dependency ordering from the ExecutionDAG. Sync components (connectors,
processors) are bridged to async via ThreadPoolExecutor.

Resume Capability
-----------------

The executor supports resuming failed or interrupted runs::

    result = await executor.execute(plan, runbook_path=path, resume_run_id="...")

Execution Flow
~~~~~~~~~~~~~~

::

    1. Start/Resume run
       ├─ New run: Create fresh ExecutionState and RunMetadata
       └─ Resume: Load existing state, validate runbook hash and status

    2. Run DAG sorter - sorter handles dependencies:
       ├─ sorter.get_ready() returns artifacts whose deps are satisfied
       ├─ For each ready artifact:
       │   ├─ If in state.completed → sorter.done(id), skip execution
       │   ├─ If not completed → execute, then state.mark_completed(id)
       │   └─ On failure: state.mark_failed(id), skip dependents
       └─ Save state after each artifact completes

    3. On completion/failure:
       └─ Update RunMetadata status and save

Design Decisions
~~~~~~~~~~~~~~~~

**Runbook hash verification**: On resume, the current runbook's SHA-256 hash
must match the original. Any runbook modification requires a fresh run - this
prevents subtle bugs from partially-executed modified runbooks.

**Concurrent execution prevention**: ``status: "running"`` in run metadata acts
as a lock. Attempting to resume an already-running run raises ``RunAlreadyActiveError``.

**State persistence granularity**: State is saved after each artifact (not per-batch)
to minimise lost progress on crash. The trade-off is more I/O, but artifacts
typically take seconds to minutes, making this acceptable.

**Store as single source of truth**: ``ExecutionResult`` contains only artifact IDs,
not artifact content. Consumers load artifacts from the store using ``run_id``.
This avoids memory duplication and ensures the store is always authoritative.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_core import ExecutionContext, Message, MessageExtensions, Schema
from waivern_core.services import ComponentRegistry

from waivern_orchestration.errors import (
    RunAlreadyActiveError,
    RunbookChangedError,
    RunNotFoundError,
)
from waivern_orchestration.models import (
    ArtifactDefinition,
    ExecutionResult,
    ProcessConfig,
    ReuseConfig,
    SourceConfig,
)
from waivern_orchestration.planner import ExecutionPlan
from waivern_orchestration.run_metadata import RunMetadata, compute_runbook_hash
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


class DAGExecutor:
    """Executes artifacts in parallel using asyncio with ThreadPoolExecutor bridge."""

    def __init__(self, registry: ComponentRegistry) -> None:
        """Initialise executor with component registry.

        Args:
            registry: ComponentRegistry for accessing services and component factories.

        """
        self._registry = registry

    async def execute(
        self,
        plan: ExecutionPlan,
        *,
        runbook_path: Path | None = None,
        resume_run_id: str | None = None,
    ) -> ExecutionResult:
        """Execute artifacts in parallel according to the DAG.

        Args:
            plan: Validated ExecutionPlan from Planner.
            runbook_path: Path to runbook file (required for resume validation).
            resume_run_id: If provided, resume from this existing run.

        Returns:
            ExecutionResult containing artifact results and skipped artifacts.

        Raises:
            RunNotFoundError: If resume_run_id doesn't exist.
            RunbookChangedError: If runbook has changed since the original run.
            RunAlreadyActiveError: If the run is already executing.

        """
        start_time = time.monotonic()
        config = plan.runbook.config

        # Get ArtifactStore from container (singleton - shared with exporter)
        store = self._registry.container.get_service(ArtifactStore)

        # Initialise run metadata and state (new or resume)
        run_id, start_timestamp, metadata, state = await self._initialise_run(
            plan, store, runbook_path, resume_run_id
        )

        # Save metadata with status='running' before starting execution
        await metadata.save(store)

        # Create thread pool for sync->async bridging
        logger.debug(
            "Creating ThreadPoolExecutor with max_workers=%d", config.max_concurrency
        )

        execution_failed = False
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

            # Determine final status
            execution_failed = len(ctx.state.failed) > 0

        logger.debug("ThreadPoolExecutor shutdown complete")

        # Update and save run metadata
        if execution_failed:
            metadata.mark_failed()
        else:
            metadata.mark_completed()
        await metadata.save(store)

        total_duration = time.monotonic() - start_time
        return ExecutionResult(
            run_id=run_id,
            start_timestamp=start_timestamp,
            completed=ctx.state.completed,
            failed=ctx.state.failed,
            skipped=ctx.state.skipped,
            total_duration_seconds=total_duration,
        )

    async def _initialise_run(
        self,
        plan: ExecutionPlan,
        store: ArtifactStore,
        runbook_path: Path | None,
        resume_run_id: str | None,
    ) -> tuple[str, str, RunMetadata, ExecutionState]:
        """Initialise run metadata and state for new or resumed run.

        Args:
            plan: The execution plan.
            store: The artifact store.
            runbook_path: Path to runbook file (for hash computation).
            resume_run_id: If provided, resume from this existing run.

        Returns:
            Tuple of (run_id, start_timestamp, metadata, state).

        Raises:
            RunNotFoundError: If resume_run_id doesn't exist.
            RunbookChangedError: If runbook has changed since the original run.
            RunAlreadyActiveError: If the run is already executing.

        """
        if resume_run_id is not None:
            return await self._resume_run(plan, store, runbook_path, resume_run_id)
        else:
            return self._start_new_run(plan, store, runbook_path)

    def _start_new_run(
        self,
        plan: ExecutionPlan,
        store: ArtifactStore,
        runbook_path: Path | None,
    ) -> tuple[str, str, RunMetadata, ExecutionState]:
        """Start a new run with fresh metadata and state."""
        run_id = str(uuid.uuid4())
        start_timestamp = datetime.now(UTC).isoformat()

        # Compute runbook hash if path provided
        runbook_hash = ""
        if runbook_path is not None:
            runbook_hash = compute_runbook_hash(runbook_path)

        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_path or Path("."),
            runbook_hash=runbook_hash,
        )

        artifact_ids = set(plan.runbook.artifacts.keys())
        state = ExecutionState.fresh(run_id, artifact_ids)

        return run_id, start_timestamp, metadata, state

    async def _resume_run(
        self,
        plan: ExecutionPlan,
        store: ArtifactStore,
        runbook_path: Path | None,
        resume_run_id: str,
    ) -> tuple[str, str, RunMetadata, ExecutionState]:
        """Resume an existing run, validating metadata.

        Raises:
            ValueError: If runbook_path is not provided (required for resume).
            RunNotFoundError: If the run doesn't exist.
            RunbookChangedError: If runbook has changed.
            RunAlreadyActiveError: If run is already executing.

        """
        # Runbook path is required for resume to validate hash
        if runbook_path is None:
            raise ValueError("runbook_path is required when resuming a run")

        # Load existing metadata
        try:
            metadata = await RunMetadata.load(store, resume_run_id)
        except ArtifactNotFoundError as e:
            raise RunNotFoundError(
                f"Cannot resume: run '{resume_run_id}' not found"
            ) from e

        # Validate runbook hasn't changed
        current_hash = compute_runbook_hash(runbook_path)
        if metadata.runbook_hash and current_hash != metadata.runbook_hash:
            raise RunbookChangedError(
                f"Runbook has changed since run {resume_run_id} was started.\n"
                f"Original hash: {metadata.runbook_hash}\n"
                f"Current hash:  {current_hash}\n"
                f"Start a new run instead."
            )

        # Check not already running
        if metadata.status == "running":
            raise RunAlreadyActiveError(f"Run {resume_run_id} is already in progress")

        # Load existing state
        state = await ExecutionState.load(store, resume_run_id)

        # Update metadata status back to running
        metadata.status = "running"

        return resume_run_id, metadata.started_at.isoformat(), metadata, state

    async def _execute_dag(
        self,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Execute artifacts in topological order with parallel batches."""
        logger.debug("Starting DAG execution...")
        sorter = plan.dag.create_sorter()

        while sorter.is_active():
            ready, already_done = self._partition_ready_artifacts(
                list(sorter.get_ready()), ctx
            )

            # Mark already-done artifacts (completed or skipped) as done in sorter
            for aid in already_done:
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

        logger.debug("DAG execution complete.")

    def _partition_ready_artifacts(
        self,
        all_ready: list[str],
        ctx: _ExecutionContext,
    ) -> tuple[list[str], list[str]]:
        """Partition ready artifacts into executable and already-done.

        Artifacts are considered 'already done' if they are in:
        - state.completed (already executed successfully, e.g., from resume)
        - state.skipped (skipped due to upstream failure)

        Returns:
            Tuple of (ready_to_execute, already_done).

        """
        already_done = ctx.state.completed | ctx.state.skipped
        ready = [aid for aid in all_ready if aid not in already_done]
        done = [aid for aid in all_ready if aid in already_done]

        if done:
            logger.debug("Skipping already-done artifacts: %s", done)

        return ready, done

    async def _handle_artifact_result(
        self,
        artifact_id: str,
        result: Message | BaseException,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Handle the result of producing an artifact.

        Persists state transitions. On failure, skips all dependent artifacts.
        Success messages are saved in _produce(). Error messages from exceptions
        caught in _produce() need to be saved here.

        """
        if isinstance(result, BaseException):
            # Exception during production (from asyncio.gather) - create and save
            message = self._create_error_message_for_exception(
                artifact_id, result, plan, ctx
            )
            await ctx.store.save_artifact(ctx.run_id, artifact_id, message)
            await self._mark_failed_and_skip_dependents(artifact_id, plan, ctx)
        elif not result.is_success:
            # Error message from _produce() - need to save it
            await ctx.store.save_artifact(ctx.run_id, artifact_id, result)
            await self._mark_failed_and_skip_dependents(artifact_id, plan, ctx)
        else:
            # Success - message already saved in _produce()
            ctx.state.mark_completed(artifact_id)
            await ctx.state.save(ctx.store)

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
                origin=get_origin_from_artifact_id(artifact_id),
                alias=plan.reversed_aliases.get(artifact_id),
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
        await ctx.state.save(ctx.store)
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
        origin = get_origin_from_artifact_id(artifact_id)
        alias = plan.reversed_aliases.get(artifact_id)

        # Get schemas from pre-resolved schemas
        _input_schema, output_schema = plan.artifact_schemas[artifact_id]

        async with ctx.semaphore:
            try:
                match definition:
                    case ArtifactDefinition(reuse=ReuseConfig() as reuse):
                        message = await self._reuse_from_previous_run(
                            reuse.from_run, reuse.artifact, ctx
                        )
                    case ArtifactDefinition(source=SourceConfig() as source):
                        message = await self._run_connector(
                            source, output_schema, ctx.thread_pool
                        )
                    case _:
                        message = await self._process_from_inputs(
                            definition, output_schema, ctx
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
                await ctx.store.save_artifact(ctx.run_id, artifact_id, message)

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
            await ctx.state.save(ctx.store)

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
            await ctx.state.save(ctx.store)

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

    async def _process_from_inputs(
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
            # Should never happen - Planner validates this
            raise ValueError(
                "Bug: derived artifact has no inputs (Planner should have caught this)"
            )

        input_refs = [inputs] if isinstance(inputs, str) else inputs

        # Retrieve input messages from store (async)
        input_messages = [
            await ctx.store.get_artifact(ctx.run_id, ref) for ref in input_refs
        ]

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

    async def _reuse_from_previous_run(
        self,
        from_run: str,
        source_artifact: str,
        ctx: _ExecutionContext,
    ) -> Message:
        """Load an artifact from a previous run for reuse.

        Args:
            from_run: The run ID to load the artifact from.
            source_artifact: The artifact ID in the source run.
            ctx: The execution context.

        Returns:
            The loaded message (metadata will be updated by caller).

        Raises:
            ArtifactNotFoundError: If the artifact doesn't exist in the source run.

        """
        logger.debug("Reusing artifact '%s' from run '%s'", source_artifact, from_run)
        return await ctx.store.get_artifact(from_run, source_artifact)

    def _determine_source(self, definition: ArtifactDefinition) -> str:
        """Determine the source component type for an artifact.

        Returns a string identifying how the artifact was produced:
        - 'connector:{type}' for source artifacts
        - 'processor:{type}' for processed artifacts
        - 'reuse:{run_id}/{artifact_id}' for reused artifacts

        Args:
            definition: The artifact definition.

        Returns:
            Source identifier string.

        """
        match definition:
            case ArtifactDefinition(reuse=ReuseConfig() as reuse):
                return f"reuse:{reuse.from_run}/{reuse.artifact}"
            case ArtifactDefinition(source=SourceConfig() as source):
                return f"connector:{source.type}"
            case ArtifactDefinition(process=ProcessConfig() as process):
                return f"processor:{process.type}"
            case _:
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
