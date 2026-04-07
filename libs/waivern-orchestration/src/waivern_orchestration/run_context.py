"""Run context model encapsulating all persistent data for a run.

RunContext is the single object the executor works with for run-level
state. It knows how to load/save each piece independently via the
ArtifactStore's generic system data API.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from waivern_artifact_store.base import ArtifactStore

from waivern_orchestration.planner import ExecutionPlan
from waivern_orchestration.run_metadata import RunMetadata
from waivern_orchestration.state import ExecutionState

_METADATA_KEY = "metadata"
_STATE_KEY = "state"
_PLAN_KEY = "plan"


@dataclass
class RunContext:
    """Encapsulates all persistent data for a run.

    Each field has different update frequencies:
    - metadata: 2-3 times per run (start, end)
    - state: after every artifact transition
    - plan: once at run start (never updated)
    """

    metadata: RunMetadata
    state: ExecutionState
    plan: ExecutionPlan

    @classmethod
    def new(
        cls,
        plan: ExecutionPlan,
        runbook_path: Path | None,
    ) -> RunContext:
        """Create a fresh RunContext for a new run.

        Args:
            plan: The validated execution plan.
            runbook_path: Path to the runbook file, or None for
                programmatic runs.

        Returns:
            RunContext with running metadata, all artifacts not_started,
            and the plan stored for persistence.

        """
        run_id = str(uuid.uuid4())
        artifact_ids = set(plan.runbook.artifacts.keys())

        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_path or Path(""),
        )
        state = ExecutionState.fresh(run_id=run_id, artifact_ids=artifact_ids)

        return cls(metadata=metadata, state=state, plan=plan)

    def validate_resumable(self) -> None:
        """Check that this run can be resumed.

        A run is resumable if its status is 'interrupted' or 'failed'.
        Runs that are still 'running' (stale lock) or already 'completed'
        cannot be resumed.

        Raises:
            ValueError: If the run status does not allow resumption.

        """
        resumable_statuses = {"interrupted", "failed"}
        if self.metadata.status not in resumable_statuses:
            raise ValueError(
                f"Run '{self.metadata.run_id}' has status "
                f"'{self.metadata.status}' and cannot be resumed. "
                f"Only interrupted or failed runs can be resumed."
            )

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    @classmethod
    async def load(cls, store: ArtifactStore, run_id: str) -> RunContext:
        """Load a complete RunContext from store for resume.

        Args:
            store: The artifact store to load from.
            run_id: The run identifier.

        Returns:
            Fully reconstituted RunContext.

        Raises:
            ArtifactNotFoundError: If any system data is missing.

        """
        metadata_data = await store.load_system_data(run_id, _METADATA_KEY)
        metadata = RunMetadata.model_validate(metadata_data)

        state_data = await store.load_system_data(run_id, _STATE_KEY)
        state = ExecutionState.model_validate(state_data)

        plan_data: dict[str, Any] = await store.load_system_data(run_id, _PLAN_KEY)
        plan = ExecutionPlan.from_dict(plan_data)

        return cls(metadata=metadata, state=state, plan=plan)

    async def save_metadata(self, store: ArtifactStore) -> None:
        """Persist metadata only.

        Used for status transitions (running → interrupted → completed).

        Args:
            store: The artifact store to save to.

        """
        data = self.metadata.model_dump(mode="json")
        await store.save_system_data(self.metadata.run_id, _METADATA_KEY, data)

    async def save_state(self, store: ArtifactStore) -> None:
        """Persist state only.

        Used after artifact state transitions (not_started → completed, etc.).

        Args:
            store: The artifact store to save to.

        """
        data = self.state.model_dump(mode="json")
        await store.save_system_data(self.metadata.run_id, _STATE_KEY, data)

    async def save_plan(self, store: ArtifactStore) -> None:
        """Persist plan only.

        Called once at run start. The plan is never updated after that.

        Args:
            store: The artifact store to save to.

        """
        data = self.plan.to_dict()
        await store.save_system_data(self.metadata.run_id, _PLAN_KEY, data)

    async def save_all(self, store: ArtifactStore) -> None:
        """Persist all run data.

        Used at run initialisation to save metadata, state, and plan
        in a single batch.

        Args:
            store: The artifact store to save to.

        """
        await self.save_metadata(store)
        await self.save_state(store)
        await self.save_plan(store)
