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
from collections import defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_core import ExecutionContext, Message, MessageExtensions, Schema
from waivern_core.dispatch import (
    DispatchRequest,
    DispatchResult,
    DistributedProcessor,
    PrepareResult,
)
from waivern_core.errors import PendingProcessingError
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
    pending_batch_artifacts: set[str] = dataclass_field(default_factory=set)


@dataclass
class _DistributedEntry:
    """Tracks a distributed processor through its prepare-dispatch-finalise lifecycle.

    Bundles the processor instance, inputs, and schema so they survive
    across phases. ``prepare_result`` is populated after Phase 1 (or
    loaded from store on resume).

    """

    artifact_id: str
    processor: DistributedProcessor[Any]
    inputs: list[Message]
    output_schema: Schema
    prepare_result: PrepareResult[Any] | None = None
    start_time: float = 0.0


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

        # Persist final state (safety net — state may already have been saved
        # incrementally, but pending-only runs skip the per-artifact save)
        await ctx.state.save(ctx.store)

        # Determine final status: interrupted > failed > completed
        if ctx.pending_batch_artifacts:
            metadata.mark_interrupted()
        elif len(ctx.state.failed) > 0:
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
        """Execute artifacts in topological order with parallel batches.

        Each level of the DAG is processed in three phases:
        1. **Classification** — split ready artifacts into regular,
           distributed, and resuming groups
        2. **Concurrent execution** — ``_produce`` for regular artifacts
           and ``_run_prepare`` for distributed artifacts run together
           in ``asyncio.gather``
        3. **Dispatch and finalise** — distributed entries go through
           dispatch → finalise (possibly multi-round)

        The loop exits when no more progress is possible. If pending batch
        artifacts exist at that point, the run is marked interrupted.
        """
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
                if not already_done:
                    # No progress possible — stalled
                    if ctx.pending_batch_artifacts:
                        logger.info(
                            "DAG stalled with pending batch artifacts: %s",
                            ctx.pending_batch_artifacts,
                        )
                    else:
                        logger.error("DAG stalled unexpectedly with no pending batches")
                    break
                continue

            # ── Classification ──
            (
                regular_aids,
                distributed_entries,
                resuming_entries,
            ) = await self._classify_artifacts(ready, plan, ctx)

            # ── Regular + Phase 1 (concurrent) ──
            regular_tasks = [self._produce(aid, plan, ctx) for aid in regular_aids]
            prepare_tasks = [
                self._run_prepare(entry, ctx) for entry in distributed_entries
            ]

            logger.debug(
                "Starting batch: %d regular, %d distributed, %d resuming",
                len(regular_aids),
                len(distributed_entries),
                len(resuming_entries),
            )
            regular_batch, prepare_batch = await asyncio.gather(
                asyncio.gather(*regular_tasks, return_exceptions=True),
                asyncio.gather(*prepare_tasks, return_exceptions=True),
            )

            # ── Handle regular results ──
            for aid, regular_result in zip(regular_aids, regular_batch, strict=True):
                await self._handle_artifact_result(aid, regular_result, plan, ctx)
                sorter.done(aid)

            # ── Collect Phase 1 results ──
            phase2_entries: list[_DistributedEntry] = list(resuming_entries)
            for entry, prepare_result in zip(
                distributed_entries, prepare_batch, strict=True
            ):
                if isinstance(prepare_result, BaseException):
                    message = self._create_error_message_for_exception(
                        entry.artifact_id, prepare_result, plan, ctx
                    )
                    await ctx.store.save_artifact(
                        ctx.run_id, entry.artifact_id, message
                    )
                    await self._mark_failed_and_skip_dependents(
                        entry.artifact_id, plan, ctx
                    )
                    sorter.done(entry.artifact_id)
                else:
                    entry.prepare_result = prepare_result
                    phase2_entries.append(entry)

            # ── Phase 2→3: Dispatch and Finalise (with multi-round) ──
            if phase2_entries:
                await self._finalise_distributed_artifacts(
                    phase2_entries, plan, ctx, sorter
                )

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

    async def _classify_artifacts(
        self,
        ready_aids: list[str],
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> tuple[list[str], list[_DistributedEntry], list[_DistributedEntry]]:
        """Classify ready artifacts into regular, distributed, and resuming.

        Classification order for each artifact:
        1. In ``state.pending`` → resuming (load PrepareResult from store)
        2. Source/reuse artifact → regular
        3. Has process config with ``DistributedProcessor`` → distributed
        4. Has process config without ``DistributedProcessor`` → regular
        5. Passthrough (no process config) → regular

        Args:
            ready_aids: Artifact IDs ready for execution at this level.
            plan: The execution plan with artifact definitions and schemas.
            ctx: The execution context with store and state.

        Returns:
            Tuple of (regular_aids, distributed_entries, resuming_entries).

        """
        regular: list[str] = []
        distributed: list[_DistributedEntry] = []
        resuming: list[_DistributedEntry] = []

        for aid in ready_aids:
            definition = plan.runbook.artifacts[aid]
            _, output_schema = plan.artifact_schemas[aid]

            # 1. Pending → resuming
            if aid in ctx.state.pending:
                raw = await ctx.store.load_prepared(ctx.run_id, aid)
                processor = self._create_distributed_processor(definition)
                prepare_result = processor.deserialise_prepare_result(raw)
                resuming.append(
                    _DistributedEntry(
                        artifact_id=aid,
                        processor=processor,
                        inputs=[],
                        output_schema=output_schema,
                        prepare_result=prepare_result,
                        start_time=time.monotonic(),
                    )
                )
                continue

            # 2. Source/reuse → regular
            if definition.source is not None or definition.reuse is not None:
                regular.append(aid)
                continue

            # 3. Has process config → check isinstance
            if definition.process is not None:
                try:
                    factory = self._registry.processor_factories[
                        definition.process.type
                    ]
                    processor_instance = factory.create(definition.process.properties)
                except KeyError:
                    # Unknown processor type — classify as regular so _produce
                    # handles it with a proper error message
                    regular.append(aid)
                    continue

                if isinstance(processor_instance, DistributedProcessor):
                    inputs = await self._load_inputs(definition, ctx)
                    distributed.append(
                        _DistributedEntry(
                            artifact_id=aid,
                            processor=processor_instance,
                            inputs=inputs,
                            output_schema=output_schema,
                            start_time=time.monotonic(),
                        )
                    )
                else:
                    regular.append(aid)
                continue

            # 4. Passthrough → regular
            regular.append(aid)

        return regular, distributed, resuming

    def _create_distributed_processor(
        self,
        definition: ArtifactDefinition,
    ) -> DistributedProcessor[Any]:
        """Re-create a DistributedProcessor from its factory.

        Used on the resume path where the processor must be re-created
        (stateless — all state lives in the persisted PrepareResult).

        Raises:
            KeyError: If processor type not found in registry.
            TypeError: If the processor does not implement DistributedProcessor.

        """
        if definition.process is None:
            msg = f"Cannot create distributed processor: no process config on '{definition}'"
            raise TypeError(msg)

        factory = self._registry.processor_factories[definition.process.type]
        processor = factory.create(definition.process.properties)

        if not isinstance(processor, DistributedProcessor):
            msg = (
                f"Processor '{definition.process.type}' does not implement "
                f"DistributedProcessor but artifact is in pending state"
            )
            raise TypeError(msg)

        return processor

    async def _load_inputs(
        self,
        definition: ArtifactDefinition,
        ctx: _ExecutionContext,
    ) -> list[Message]:
        """Load input messages for an artifact from the store.

        Args:
            definition: The artifact definition with input references.
            ctx: The execution context with store and run_id.

        Returns:
            List of input messages.

        Raises:
            ValueError: If the artifact has no inputs defined.

        """
        inputs = definition.inputs
        if inputs is None:
            msg = "Cannot load inputs: artifact has no inputs defined"
            raise ValueError(msg)

        input_refs = [inputs] if isinstance(inputs, str) else inputs
        return [await ctx.store.get_artifact(ctx.run_id, ref) for ref in input_refs]

    async def _run_prepare(
        self,
        entry: _DistributedEntry,
        ctx: _ExecutionContext,
    ) -> PrepareResult[Any]:
        """Run prepare() in the thread pool, governed by the semaphore.

        Follows the same bridge pattern as ``_run_connector`` and
        ``_run_processor``, but acquires the semaphore internally
        (called from ``asyncio.gather``, not wrapped by ``_produce``).

        """
        async with ctx.semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                ctx.thread_pool,
                entry.processor.prepare,
                entry.inputs,
                entry.output_schema,
            )

    async def _run_finalise(
        self,
        entry: _DistributedEntry,
        results: Sequence[DispatchResult],
        ctx: _ExecutionContext,
    ) -> Message | PrepareResult[Any]:
        """Run finalise() in the thread pool, governed by the semaphore.

        Follows the same bridge pattern as ``_run_prepare``.

        Args:
            entry: The distributed entry with processor, state, and schema.
            results: Dispatch results routed to this entry.
            ctx: The execution context with semaphore and thread pool.

        """
        if entry.prepare_result is None:
            msg = f"Cannot finalise '{entry.artifact_id}': no prepare_result"
            raise RuntimeError(msg)

        async with ctx.semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                ctx.thread_pool,
                entry.processor.finalise,
                entry.prepare_result.state,
                results,
                entry.output_schema,
            )

    async def _finalise_distributed_artifacts(
        self,
        entries: list[_DistributedEntry],
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
        sorter: TopologicalSorter[str],
        *,
        max_rounds: int = 3,
    ) -> None:
        """Orchestrate Phase 2–3 with multi-round loop for distributed entries.

        Drives the dispatch → finalise cycle until all entries produce a
        ``Message`` or max rounds is exceeded:
        1. Filter out entries already marked pending by dispatch
        2. Dispatch all entries with requests (Phase 2)
        3. Finalise each entry (Phase 3)
        4. Message → save artifact, mark completed, clean up, notify sorter
        5. PrepareResult → queue for another round
        6. Repeat until no entries remain or max rounds exceeded

        Args:
            entries: Distributed entries with ``prepare_result`` populated.
            plan: The execution plan (for failure handling and metadata).
            ctx: The execution context.
            sorter: The topological sorter (to notify on completion).
            max_rounds: Maximum dispatch-finalise cycles (default 3).

        """
        active_entries = [
            e for e in entries if e.artifact_id not in ctx.pending_batch_artifacts
        ]

        for _round in range(max_rounds):
            if not active_entries:
                return

            # Phase 2: dispatch
            results_by_artifact = await self._dispatch_all(active_entries, plan, ctx)

            # Phase 3: finalise each non-pending entry
            next_round: list[_DistributedEntry] = []
            for entry in active_entries:
                if entry.artifact_id in ctx.pending_batch_artifacts:
                    continue
                if entry.artifact_id not in results_by_artifact:
                    continue

                try:
                    result = await self._run_finalise(
                        entry, results_by_artifact[entry.artifact_id], ctx
                    )
                except Exception as exc:
                    message = self._create_error_message_for_exception(
                        entry.artifact_id, exc, plan, ctx
                    )
                    await ctx.store.save_artifact(
                        ctx.run_id, entry.artifact_id, message
                    )
                    await self._mark_failed_and_skip_dependents(
                        entry.artifact_id, plan, ctx
                    )
                    continue

                if isinstance(result, Message):
                    await self._save_distributed_artifact(
                        entry, result, results_by_artifact[entry.artifact_id], plan, ctx
                    )
                    sorter.done(entry.artifact_id)
                else:
                    entry.prepare_result = result
                    next_round.append(entry)

            active_entries = next_round

        # Entries still active after max rounds → fail
        for entry in active_entries:
            logger.warning(
                "Artifact '%s' exceeded max dispatch rounds (%d)",
                entry.artifact_id,
                max_rounds,
            )
            await self._mark_failed_and_skip_dependents(entry.artifact_id, plan, ctx)

    async def _save_distributed_artifact(
        self,
        entry: _DistributedEntry,
        message: Message,
        results: Sequence[DispatchResult],
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Save a completed distributed artifact with metadata.

        Follows the same metadata pattern as ``_produce``: populates
        ``run_id``, ``source``, and ``extensions`` with ``ExecutionContext``.
        Calls ``enrich_execution_context`` on each dispatch result to
        propagate dispatch-specific metadata (e.g., ``model_name``).

        """
        definition = plan.runbook.artifacts[entry.artifact_id]
        origin = get_origin_from_artifact_id(entry.artifact_id)
        alias = plan.reversed_aliases.get(entry.artifact_id)

        duration = time.monotonic() - entry.start_time
        execution_context = ExecutionContext(
            status="success",
            duration_seconds=duration,
            origin=origin,
            alias=alias,
        )
        for result in results:
            execution_context = result.enrich_execution_context(execution_context)

        message = replace(
            message,
            run_id=ctx.run_id,
            source=self._determine_source(definition),
            extensions=MessageExtensions(execution=execution_context),
        )
        await ctx.store.save_artifact(ctx.run_id, entry.artifact_id, message)
        await ctx.store.delete_prepared(ctx.run_id, entry.artifact_id)
        ctx.state.mark_completed(entry.artifact_id)
        await ctx.state.save(ctx.store)

    async def _dispatch_all(
        self,
        entries: list[_DistributedEntry],
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> Mapping[str, Sequence[DispatchResult]]:
        """Group requests by type, dispatch each group, and route results back.

        Orchestrates Phase 2 of the distributed processor lifecycle:
        1. Collect all requests from entries and build request-to-artifact mapping
        2. Group requests by concrete type (e.g., all LLMRequest together)
        3. Resolve a dispatcher per group and dispatch
        4. Route results back to artifacts via request_id

        Short-circuited entries (empty requests) get empty result sequences
        without going through dispatch.

        Args:
            entries: Distributed entries with ``prepare_result`` populated.
            plan: The execution plan (needed for failure handling).
            ctx: The execution context with store, state, and registry access.

        Returns:
            Mapping from artifact_id to its dispatch results. Artifacts
            that were marked pending (PendingBatchError) or failed are
            excluded from the returned mapping.

        """
        results_by_artifact: dict[str, list[DispatchResult]] = {
            entry.artifact_id: [] for entry in entries
        }

        # Map request_id → artifact_id for result routing
        request_to_artifact: dict[str, str] = {}
        # Group requests by concrete type for consolidated dispatch
        requests_by_type: dict[type[DispatchRequest], list[DispatchRequest]] = (
            defaultdict(list)
        )
        # Track which entries are affected by each request type group
        entries_by_type: dict[type[DispatchRequest], list[_DistributedEntry]] = (
            defaultdict(list)
        )

        for entry in entries:
            if entry.prepare_result is None or not entry.prepare_result.requests:
                continue

            request_type = type(entry.prepare_result.requests[0])
            for request in entry.prepare_result.requests:
                request_to_artifact[request.request_id] = entry.artifact_id
                requests_by_type[request_type].append(request)

            if entry not in entries_by_type[request_type]:
                entries_by_type[request_type].append(entry)

        # Dispatch each type group
        for request_type, requests in requests_by_type.items():
            affected_entries = entries_by_type[request_type]
            try:
                dispatcher = self._registry.get_dispatcher_for(request_type)
                group_results = await dispatcher.dispatch(requests)
            except PendingProcessingError:
                await self._persist_pending_entries(affected_entries, ctx)
                continue
            except Exception:
                affected_ids = [e.artifact_id for e in affected_entries]
                logger.exception(
                    "Dispatch failed for request type %s affecting artifacts %s",
                    request_type.__name__,
                    affected_ids,
                )
                for entry in affected_entries:
                    await self._mark_failed_and_skip_dependents(
                        entry.artifact_id, plan, ctx
                    )
                    results_by_artifact.pop(entry.artifact_id, None)
                continue

            # Route results back to artifacts via request_id
            for result in group_results:
                artifact_id = request_to_artifact[result.request_id]
                results_by_artifact[artifact_id].append(result)

        return results_by_artifact

    async def _persist_pending_entries(
        self,
        entries: list[_DistributedEntry],
        ctx: _ExecutionContext,
    ) -> None:
        """Persist PrepareResult for entries affected by PendingBatchError.

        Serialises each entry's PrepareResult, saves to store, marks the
        artifact as pending, and adds to the pending tracking set.

        """
        for entry in entries:
            if entry.prepare_result is not None:
                data = entry.prepare_result.model_dump(mode="json")
                await ctx.store.save_prepared(ctx.run_id, entry.artifact_id, data)
            ctx.state.mark_pending(entry.artifact_id)
            ctx.pending_batch_artifacts.add(entry.artifact_id)
        await ctx.state.save(ctx.store)

    async def _handle_artifact_result(
        self,
        artifact_id: str,
        result: Message | BaseException,
        plan: ExecutionPlan,
        ctx: _ExecutionContext,
    ) -> None:
        """Handle the result of producing a regular artifact.

        Persists state transitions. On failure, skips all dependent artifacts.
        Success messages are saved in _produce(). Error messages from
        exceptions caught in _produce() need to be saved here.

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
        input_messages = await self._load_inputs(definition, ctx)

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
