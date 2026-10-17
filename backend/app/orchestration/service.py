"""High-level Orchestration Service coordinating workflow execution, resumption, and cancellation."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.run import Run, RunStatus
from app.orchestration.checkpointer import DEFAULT_CHECKPOINT_DB_PATH, get_async_checkpointer
from app.orchestration.exceptions import (
    CheckpointError,
    OrchestrationError,
    RunNotResumableError,
    UnauthorizedRunAccessError,
)
from app.orchestration.graph import compile_devsquad_graph
from app.orchestration.state import (
    DevSquadState,
    WorkflowStage,
    WorkflowStatus,
    create_initial_state,
)
from app.services.agents.repair import log_agent_event

logger = logging.getLogger("devsquad.orchestrator")

# Concurrency-safe in-memory registries for active runs
_active_tasks: Dict[str, asyncio.Task] = {}
_cancel_events: Dict[str, asyncio.Event] = {}
_registry_lock = asyncio.Lock()


class DevSquadOrchestrator:
    """Service facade coordinating the LangGraph execution engine, persistence, and recovery."""

    def __init__(self, checkpoint_db_path: Optional[str] = None):
        self.checkpoint_db_path = checkpoint_db_path or DEFAULT_CHECKPOINT_DB_PATH

    async def start_run(
        self,
        run_id: str,
        db: AsyncSession,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DevSquadState:
        """Start a new workflow run from the beginning."""
        logger.info(f"DevSquadOrchestrator starting run {run_id}")

        current_task = asyncio.current_task()
        cancel_event = asyncio.Event()

        async with _registry_lock:
            if run_id in _active_tasks and not _active_tasks[run_id].done():
                raise OrchestrationError(f"Run '{run_id}' is already actively executing.")
            if current_task:
                _active_tasks[run_id] = current_task
            _cancel_events[run_id] = cancel_event

        run = await db.get(Run, run_id)
        if not run:
            raise OrchestrationError(f"Run '{run_id}' not found in database.")

        # Check terminal state
        if run.status in (RunStatus.COMPLETED.value, RunStatus.CANCELLED.value):
            raise OrchestrationError(f"Run '{run_id}' is in terminal state '{run.status}' and cannot be started.")

        initial_state = create_initial_state(
            run_id=run.id,
            repository_id=run.repository_id,
            issue_id=run.issue_id,
            max_repair_attempts=settings.max_agent_retries,
            metadata=metadata or {},
        )

        thread_config = {"configurable": {"thread_id": initial_state["thread_id"]}}

        try:
            async with get_async_checkpointer(self.checkpoint_db_path) as checkpointer:
                graph = compile_devsquad_graph(checkpointer=checkpointer)
                try:
                    final_state = await graph.ainvoke(initial_state, config=thread_config)
                except asyncio.CancelledError:
                    logger.info(f"Workflow execution for run {run_id} observed cancellation.")
                    try:
                        await db.refresh(run)
                    except Exception:
                        pass
                    if run.status != RunStatus.CANCELLED.value:
                        run.status = RunStatus.CANCELLED.value
                        run.error_summary = "Workflow execution cancelled by user request."
                        run.finished_at = datetime.now(timezone.utc)
                        try:
                            await db.commit()
                        except Exception:
                            await db.rollback()
                    return DevSquadState(
                        run_id=run_id,
                        thread_id=initial_state["thread_id"],
                        repository_id=run.repository_id,
                        issue_id=run.issue_id,
                        status=WorkflowStatus.CANCELLED.value,
                        current_stage=WorkflowStage.FINALIZING.value,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        error_message="Workflow execution cancelled.",
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                except Exception as exc:
                    logger.error(f"Uncaught exception during workflow execution: {str(exc)}", exc_info=True)
                    run.status = RunStatus.FAILED.value
                    run.error_summary = f"Workflow runtime error: {str(exc)}"
                    run.finished_at = datetime.now(timezone.utc)
                    await db.commit()
                    raise OrchestrationError(f"Workflow execution failed: {str(exc)}") from exc

            return final_state

        finally:
            async with _registry_lock:
                _active_tasks.pop(run_id, None)
                _cancel_events.pop(run_id, None)

    async def resume_run(
        self,
        run_id: str,
        db: AsyncSession,
    ) -> DevSquadState:
        """Resume an interrupted or waiting workflow run from its latest checkpoint."""
        logger.info(f"DevSquadOrchestrator resuming run {run_id}")

        current_task = asyncio.current_task()
        cancel_event = asyncio.Event()

        async with _registry_lock:
            if run_id in _active_tasks and not _active_tasks[run_id].done():
                raise OrchestrationError(f"Run '{run_id}' is already actively executing.")
            if current_task:
                _active_tasks[run_id] = current_task
            _cancel_events[run_id] = cancel_event

        run = await db.get(Run, run_id)
        if not run:
            raise OrchestrationError(f"Run '{run_id}' not found in database.")

        if run.status in (RunStatus.COMPLETED.value, RunStatus.CANCELLED.value):
            raise RunNotResumableError(f"Cannot resume run '{run_id}' with terminal status '{run.status}'.")

        thread_id = f"thread-{run_id}"
        thread_config = {"configurable": {"thread_id": thread_id}}

        try:
            async with get_async_checkpointer(self.checkpoint_db_path) as checkpointer:
                graph = compile_devsquad_graph(checkpointer=checkpointer)

                # Retrieve state snapshot
                state_snapshot = await graph.aget_state(thread_config)
                if not state_snapshot or not state_snapshot.values:
                    raise RunNotResumableError(f"No valid checkpoint found to resume run '{run_id}'.")

                current_values = dict(state_snapshot.values)
                if current_values.get("status") in (WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value):
                    raise RunNotResumableError(f"Checkpoint for '{run_id}' indicates already concluded workflow.")

                # Revalidate cryptographic provenance and patch integrity before resuming
                meta = current_values.get("metadata", {})
                if "repository_context" in meta:
                    from app.schemas.repository_context import RepositoryContext
                    try:
                        ctx = RepositoryContext(**meta["repository_context"])
                        if not ctx.verify_integrity():
                            raise RunNotResumableError(
                                f"Cannot resume run '{run_id}': Checkpoint repository context failed cryptographic integrity check."
                            )
                    except Exception as val_exc:
                        if isinstance(val_exc, RunNotResumableError):
                            raise
                        raise RunNotResumableError(
                            f"Cannot resume run '{run_id}': Invalid repository context in checkpoint: {val_exc}"
                        ) from val_exc

                current_patch = current_values.get("current_patch")
                if current_patch and isinstance(current_patch, dict):
                    from app.core.security import compute_sha256
                    stored_hash = current_patch.get("patch_hash")
                    unified_diff = current_patch.get("unified_diff", "")
                    if stored_hash and unified_diff:
                        actual_hash = compute_sha256(unified_diff.strip())
                        if actual_hash != stored_hash:
                            raise RunNotResumableError(
                                f"Cannot resume run '{run_id}': Checkpoint patch hash mismatch detected."
                            )

                # Log resume event
                await log_agent_event(
                    session=db,
                    run_id=run_id,
                    agent_name="orchestrator",
                    event_type="workflow_resumed",
                    message=f"Workflow resumed from stage '{current_values.get('current_stage')}'.",
                )

                # Resume execution
                try:
                    final_state = await graph.ainvoke(None, config=thread_config)
                except asyncio.CancelledError:
                    logger.info(f"Resumed workflow execution for run {run_id} observed cancellation.")
                    try:
                        await db.refresh(run)
                    except Exception:
                        pass
                    if run.status != RunStatus.CANCELLED.value:
                        run.status = RunStatus.CANCELLED.value
                        run.error_summary = "Workflow resume cancelled by user request."
                        run.finished_at = datetime.now(timezone.utc)
                        try:
                            await db.commit()
                        except Exception:
                            await db.rollback()
                    return DevSquadState(
                        run_id=run_id,
                        thread_id=thread_id,
                        repository_id=run.repository_id,
                        issue_id=run.issue_id,
                        status=WorkflowStatus.CANCELLED.value,
                        current_stage=WorkflowStage.FINALIZING.value,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        error_message="Workflow resume cancelled.",
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                except Exception as exc:
                    logger.error(f"Error resuming workflow execution: {str(exc)}", exc_info=True)
                    raise OrchestrationError(f"Workflow resume failed: {str(exc)}") from exc

            return final_state

        finally:
            async with _registry_lock:
                _active_tasks.pop(run_id, None)
                _cancel_events.pop(run_id, None)

    async def cancel_run(
        self,
        run_id: str,
        db: AsyncSession,
        reason: Optional[str] = None,
    ) -> DevSquadState:
        """Idempotently cancel an active or waiting workflow run."""
        logger.info(f"DevSquadOrchestrator requesting cancellation for run {run_id}")

        run = await db.get(Run, run_id)
        if not run:
            raise OrchestrationError(f"Run '{run_id}' not found.")

        # Idempotent return if already cancelled
        if run.status == RunStatus.CANCELLED.value:
            return DevSquadState(
                run_id=run_id,
                thread_id=f"thread-{run_id}",
                repository_id=run.repository_id,
                issue_id=run.issue_id,
                status=WorkflowStatus.CANCELLED.value,
                current_stage=WorkflowStage.FINALIZING.value,
                completed_at=run.finished_at.isoformat() if run.finished_at else datetime.now(timezone.utc).isoformat(),
                error_message=run.error_summary or "Run already cancelled.",
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

        if run.status == RunStatus.COMPLETED.value:
            raise OrchestrationError(f"Cannot cancel run '{run_id}' because it has already COMPLETED.")

        now = datetime.now(timezone.utc)
        run.status = RunStatus.CANCELLED.value
        run.finished_at = now
        run.error_summary = reason or "Run cancelled by user request."
        await db.commit()

        # Signal cancellation event and cancel active task if running
        async with _registry_lock:
            event = _cancel_events.get(run_id)
            if event:
                event.set()
            task = _active_tasks.get(run_id)
            if task and not task.done() and task != asyncio.current_task():
                task.cancel()

        await log_agent_event(
            session=db,
            run_id=run_id,
            agent_name="orchestrator",
            event_type="workflow_cancelled",
            message=reason or "Workflow run cancelled.",
        )

        return DevSquadState(
            run_id=run_id,
            thread_id=f"thread-{run_id}",
            repository_id=run.repository_id,
            issue_id=run.issue_id,
            status=WorkflowStatus.CANCELLED.value,
            current_stage=WorkflowStage.FINALIZING.value,
            completed_at=now.isoformat(),
            error_message=reason or "Run cancelled.",
            updated_at=now.isoformat(),
        )

    async def get_run_state(self, run_id: str) -> Optional[DevSquadState]:
        """Fetch the latest state snapshot from the checkpointer for a run."""
        thread_id = f"thread-{run_id}"
        thread_config = {"configurable": {"thread_id": thread_id}}

        async with get_async_checkpointer(self.checkpoint_db_path) as checkpointer:
            graph = compile_devsquad_graph(checkpointer=checkpointer)
            state_snapshot = await graph.aget_state(thread_config)
            if state_snapshot and state_snapshot.values:
                return state_snapshot.values
        return None

    async def reconcile_orphaned_runs(self, db: AsyncSession) -> list[str]:
        """Detect and reconcile in-flight runs orphaned by server restarts or unhandled worker terminations."""
        active_statuses = [
            RunStatus.QUEUED.value,
            RunStatus.INGESTING.value,
            RunStatus.PLANNING.value,
            RunStatus.CODING.value,
            RunStatus.TESTING.value,
            RunStatus.REVIEWING.value,
        ]
        stmt = select(Run).where(Run.status.in_(active_statuses))
        result = await db.execute(stmt)
        candidates = result.scalars().all()
        reconciled_ids: list[str] = []

        now = datetime.now(timezone.utc)
        async with _registry_lock:
            for r in candidates:
                task = _active_tasks.get(r.id)
                if task is None or task.done():
                    logger.warning(f"Reconciling orphaned run {r.id} with status '{r.status}' to FAILED.")
                    r.status = RunStatus.FAILED.value
                    r.error_summary = "Workflow execution interrupted by system restart or unhandled worker termination."
                    r.finished_at = now
                    reconciled_ids.append(r.id)

        if reconciled_ids:
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise
        return reconciled_ids
