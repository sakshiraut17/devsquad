"""Run execution management API endpoints with authentication and authorization."""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_authorized_repository,
    get_authorized_run,
    get_current_user,
    get_stream_authorized_run,
)
from app.core.config import settings
from app.db.models.approval_record import ApprovalRecord
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.security_finding import SecurityFinding
from app.db.models.security_scan_record import SecurityScanRecord
from app.db.models.user import User
from app.db.session import async_session_factory, get_db
from app.schemas.approval import ApprovalRequest, ApprovalResponse
from app.schemas.patch import PatchResponse
from app.schemas.run import RunCreate, RunResponse

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.get("", response_model=list[RunResponse])
async def list_runs(
    repository_id: Optional[str] = Query(default=None),
    status_filter: Optional[RunStatus] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Run]:
    """Retrieve persisted workflow runs with pagination and owner authorization filters."""
    if repository_id:
        await get_authorized_repository(repository_id, current_user=current_user, db=db)
        query = select(Run).where(Run.repository_id == repository_id)
    else:
        # Only list runs for repositories belonging to current user or public unowned
        query = (
            select(Run)
            .join(Repository)
            .where((Repository.owner_id == current_user.id) | (Repository.owner_id.is_(None)))
        )

    if status_filter:
        query = query.where(Run.status == status_filter.value)

    query = query.offset(skip).limit(limit).order_by(Run.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Run:
    """Create and queue a new workflow run for an authorized repository and issue."""
    # Verify caller is authorized for repository
    repo = await get_authorized_repository(payload.repository_id, current_user=current_user, db=db)

    # Verify issue exists and belongs to this repository
    issue = await db.get(Issue, payload.issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue '{payload.issue_id}' does not exist.",
        )
    if issue.repository_id != payload.repository_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Issue '{payload.issue_id}' does not belong to repository '{payload.repository_id}'.",
        )

    run = Run(
        repository_id=payload.repository_id,
        issue_id=payload.issue_id,
        status=RunStatus.QUEUED.value,
        current_node="start",
        retry_count=0,
    )
    db.add(run)
    try:
        await db.commit()
        await db.refresh(run)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integrity violation while creating run.",
        ) from exc

    return run


_background_tasks: set[asyncio.Task] = set()


@router.post("/reconcile-orphaned", status_code=status.HTTP_200_OK)
async def reconcile_orphaned_runs_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reconcile in-flight runs that were orphaned due to API restarts or task terminations."""
    from app.orchestration import get_orchestrator
    orchestrator = get_orchestrator()
    reconciled = await orchestrator.reconcile_orphaned_runs(db)
    return {"reconciled_count": len(reconciled), "reconciled_run_ids": reconciled}


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run: Run = Depends(get_authorized_run),
) -> Run:
    """Retrieve a single execution run by its unique identifier."""
    return run


@router.post("/{run_id}/start", status_code=status.HTTP_200_OK)
async def start_run(
    run: Run = Depends(get_authorized_run),
    payload: Optional[dict] = None,
    background: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start executing the multi-agent workflow for an authorized run."""
    import asyncio
    import logging
    from datetime import datetime, timezone
    from app.orchestration import get_orchestrator, OrchestrationError

    meta = (payload or {}).get("metadata", {})
    is_bg = background or bool((payload or {}).get("background"))

    if is_bg:
        run_id_val = run.id
        orchestrator = get_orchestrator()

        async def _run_in_background():
            async with async_session_factory() as bg_session:
                try:
                    await orchestrator.start_run(
                        run_id=run_id_val,
                        db=bg_session,
                        metadata=meta,
                    )
                except Exception as exc:
                    logging.getLogger("devsquad.runs").error(
                        f"Background run {run_id_val} failed: {exc}", exc_info=True
                    )
                    try:
                        bg_run = await bg_session.get(Run, run_id_val)
                        if bg_run and bg_run.status not in (
                            RunStatus.COMPLETED.value,
                            RunStatus.FAILED.value,
                            RunStatus.CANCELLED.value,
                        ):
                            bg_run.status = RunStatus.FAILED.value
                            bg_run.error_summary = f"Workflow worker error: {str(exc)}"
                            bg_run.finished_at = datetime.now(timezone.utc)
                            from app.services.agents.repair import log_agent_event
                            await log_agent_event(
                                session=bg_session,
                                run_id=run_id_val,
                                agent_name="orchestrator",
                                event_type="workflow_failed",
                                message=f"Worker crashed or raised: {str(exc)}",
                            )
                            await bg_session.commit()
                    except Exception as commit_exc:
                        logging.getLogger("devsquad.runs").error(
                            f"Failed to record run {run_id_val} failure: {commit_exc}"
                        )
                        await bg_session.rollback()

        bg_task = asyncio.create_task(_run_in_background())
        _background_tasks.add(bg_task)
        bg_task.add_done_callback(_background_tasks.discard)

        return {
            "run_id": run.id,
            "status": RunStatus.PLANNING.value,
            "current_stage": "context_preparation",
            "patch_revision": 0,
            "background": True,
        }

    orchestrator = get_orchestrator()
    try:
        final_state = await orchestrator.start_run(
            run_id=run.id,
            db=db,
            metadata=meta,
        )
        return {
            "run_id": run.id,
            "status": final_state.get("status"),
            "current_stage": final_state.get("current_stage"),
            "patch_revision": final_state.get("patch_revision", 0),
            "validation_status": final_state.get("validation_status"),
            "completed_at": final_state.get("completed_at"),
            "error_message": final_state.get("error_message"),
        }
    except OrchestrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{run_id}/resume", status_code=status.HTTP_200_OK)
async def resume_run(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resume an interrupted or waiting workflow run from its latest checkpoint."""
    from app.orchestration import get_orchestrator, OrchestrationError, RunNotResumableError

    orchestrator = get_orchestrator()
    try:
        final_state = await orchestrator.resume_run(run_id=run.id, db=db)
        return {
            "run_id": run.id,
            "status": final_state.get("status"),
            "current_stage": final_state.get("current_stage"),
            "patch_revision": final_state.get("patch_revision", 0),
            "completed_at": final_state.get("completed_at"),
        }
    except RunNotResumableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OrchestrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_run(
    run: Run = Depends(get_authorized_run),
    payload: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Request idempotent cancellation of an active workflow run."""
    from app.orchestration import get_orchestrator, OrchestrationError

    orchestrator = get_orchestrator()
    reason = (payload or {}).get("reason", "Cancelled by user request.")
    try:
        final_state = await orchestrator.cancel_run(run_id=run.id, db=db, reason=reason)
        return {
            "run_id": run.id,
            "status": final_state.get("status"),
            "message": "Run cancelled successfully.",
        }
    except OrchestrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{run_id}/state")
async def get_run_workflow_state(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve the active LangGraph workflow state snapshot from the checkpointer."""
    from app.orchestration import get_orchestrator

    orchestrator = get_orchestrator()
    state_values = await orchestrator.get_run_state(run.id)
    if not state_values:
        return {
            "run_id": run.id,
            "thread_id": f"thread-{run.id}",
            "status": run.status,
            "stage": run.current_node,
            "checkpoint_found": False,
        }

    meta = state_values.get("metadata", {}) or {}
    return {
        "run_id": run.id,
        "checkpoint_found": True,
        "state": {
            "status": state_values.get("status"),
            "current_stage": state_values.get("current_stage"),
            "patch_revision": state_values.get("patch_revision", 0),
            "repair_attempts": state_values.get("repair_attempts", 0),
            "validation_status": state_values.get("validation_status"),
            "error_message": state_values.get("error_message"),
            "plan": state_values.get("plan"),
            "security_result": state_values.get("security_result"),
            "test_result": state_values.get("test_result"),
            "review": state_values.get("review"),
            "repository_context": meta.get("repository_context"),
            "failed_patch_registry": state_values.get("failed_patch_registry"),
        },
    }


@router.post("/{run_id}/stream-ticket", status_code=status.HTTP_200_OK)
async def generate_stream_ticket(
    run: Run = Depends(get_authorized_run),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate a short-lived (60s), single-purpose signed ticket to stream events securely without URL token exposure."""
    from app.core.security import create_stream_ticket

    ticket = create_stream_ticket(user_id=current_user.id, run_id=run.id, expires_in_seconds=60)
    return {
        "ticket": ticket,
        "expires_in": 60,
        "run_id": run.id,
    }


@router.get("/{run_id}/stream")
async def stream_run_events(
    request: Request,
    run: Run = Depends(get_stream_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events (SSE) telemetry stream emitting real-time agent events and lifecycle updates."""
    import asyncio
    import json
    from app.db.models.agent_log import AgentLog
    from app.db.session import async_session_factory

    async def event_generator():
        last_event_id = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id")
        seen_ids = set()
        initial_sync_done = False
        last_emitted_status = None
        last_emitted_node = None

        terminal_statuses = {
            RunStatus.COMPLETED.value,
            RunStatus.FAILED.value,
            RunStatus.CANCELLED.value,
            RunStatus.AWAITING_APPROVAL.value,
            RunStatus.APPROVED.value,
            RunStatus.REJECTED.value,
        }

        consecutive_idle = 0
        while True:
            if await request.is_disconnected():
                break

            async with async_session_factory() as session:
                current_run = await session.get(Run, run.id)
                query = select(AgentLog).where(AgentLog.run_id == run.id).order_by(AgentLog.created_at.asc(), AgentLog.id.asc())
                res = await session.execute(query)
                logs = res.scalars().all()

                # On first iteration with last_event_id, mark all events up to last_event_id as delivered
                if not initial_sync_done:
                    if last_event_id:
                        found_idx = -1
                        for idx, l in enumerate(logs):
                            if l.id == last_event_id:
                                found_idx = idx
                                break
                        if found_idx >= 0:
                            for l in logs[:found_idx + 1]:
                                seen_ids.add(l.id)
                        else:
                            seen_ids.add(last_event_id)
                    initial_sync_done = True

                emitted = False
                new_logs = [log for log in logs if log.id not in seen_ids]
                for log in new_logs:
                    seen_ids.add(log.id)
                    payload = {
                        "id": log.id,
                        "run_id": log.run_id,
                        "agent_name": log.agent_name,
                        "event_type": log.event_type,
                        "message": log.message,
                        "input_summary": log.input_summary,
                        "output_summary": log.output_summary,
                        "duration_ms": log.duration_ms,
                        "created_at": log.created_at.isoformat(),
                    }
                    yield f"id: {log.id}\nevent: agent_event\ndata: {json.dumps(payload)}\n\n"
                    emitted = True

                status_val = current_run.status if current_run else run.status
                node_val = current_run.current_node if current_run else run.current_node

                if status_val != last_emitted_status or node_val != last_emitted_node:
                    last_emitted_status = status_val
                    last_emitted_node = node_val
                    yield f"event: status_update\ndata: {json.dumps({'status': status_val, 'current_node': node_val})}\n\n"
                    emitted = True

                if status_val in terminal_statuses:
                    consecutive_idle += 1
                    if consecutive_idle >= 2:
                        yield f"event: done\ndata: {json.dumps({'status': status_val})}\n\n"
                        break
                else:
                    consecutive_idle = 0

                if not emitted:
                    yield ": keepalive\n\n"

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.get("/{run_id}/events")
async def get_run_events(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Retrieve immutable audit log events for a given workflow run."""
    from app.db.models.agent_log import AgentLog

    query = select(AgentLog).where(AgentLog.run_id == run.id).order_by(AgentLog.created_at.asc())
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "run_id": log.run_id,
            "agent_name": log.agent_name,
            "event_type": log.event_type,
            "message": log.message,
            "input_summary": log.input_summary,
            "output_summary": log.output_summary,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/{run_id}/approve", response_model=ApprovalResponse, status_code=status.HTTP_200_OK)
async def approve_run(
    payload: ApprovalRequest,
    run: Run = Depends(get_authorized_run),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalRecord:
    # Refresh run from DB to ensure freshest state under concurrent requests
    try:
        await db.refresh(run)
    except Exception:
        pass

    # Ensure run is in an awaiting approval state
    if run.status != RunStatus.AWAITING_APPROVAL.value:
        conflict_statuses = (RunStatus.APPROVED.value, RunStatus.REJECTED.value, RunStatus.COMPLETED.value)
        status_code = status.HTTP_409_CONFLICT if run.status in conflict_statuses else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=f"Run '{run.id}' is in status '{run.status}' and cannot receive human approval.",
        )

    # Ensure the target patch exists and belongs to this run
    patch = await db.get(Patch, payload.patch_id)
    if not patch or patch.run_id != run.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch '{payload.patch_id}' does not belong to run '{run.id}'.",
        )

    # Invalidation guard: ensure the target patch is the active, latest revision (not an invalidated/superseded revision)
    latest_patch_query = (
        select(Patch).where(Patch.run_id == run.id).order_by(Patch.revision.desc()).limit(1)
    )
    latest_result = await db.execute(latest_patch_query)
    latest_patch = latest_result.scalar_one_or_none()
    if latest_patch and latest_patch.id != patch.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval rejected: patch '{payload.patch_id}' (revision {patch.revision}) has been superseded by newer revision {latest_patch.revision}.",
        )

    # Cryptographic anti-tamper verification: submitted hash must match stored patch hash exactly
    if patch.content_hash != payload.patch_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval rejected: submitted patch_hash does not match the stored patch revision content hash.",
        )

    # Evidence guard: if approving, patch must have completed validation
    allowed_validation_statuses = {"TESTS_PASSED", "VALIDATED", "PASSED"}
    if settings.allow_manual_approval_without_sandbox:
        allowed_validation_statuses.update({"PARTIAL_VALIDATION", "SANDBOX_UNAVAILABLE", "UNTESTED_MANUAL_VALIDATION_REQUIRED"})
    if payload.decision == "approved" and (patch.validation_status or "").upper() not in allowed_validation_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval rejected: patch revision {patch.revision} has validation status '{patch.validation_status}' which is ineligible for approval.",
        )

    # Reviewer and base commit validation guard when approving
    from app.orchestration import get_orchestrator
    orchestrator = get_orchestrator()
    state_values = await orchestrator.get_run_state(run.id)

    if payload.decision == "approved" and state_values:
        # Check for blocking review findings or rejection recommendation
        review_data = state_values.get("review")
        if review_data and isinstance(review_data, dict):
            recommendation = str(review_data.get("recommendation", "")).lower()
            findings = review_data.get("findings", [])
            has_blocking_finding = any(
                isinstance(f, dict) and str(f.get("severity", "")).upper() in ("CRITICAL", "BLOCKING")
                for f in findings
            )
            if recommendation == "reject" or has_blocking_finding:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Approval rejected: patch has blocking reviewer findings or a reject recommendation.",
                )

        # Base commit SHA verification
        if payload.base_commit_sha:
            meta = state_values.get("metadata", {}) or {}
            expected_commit = meta.get("base_commit_sha")
            if expected_commit and expected_commit != payload.base_commit_sha:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Approval rejected: submitted base_commit_sha '{payload.base_commit_sha}' does not match run base commit SHA '{expected_commit}'.",
                )

    # Mandatory AI Security Guardian Gate Guard: patch must have completed security scanning with zero blockers
    if payload.decision == "approved":
        sec_query = (
            select(SecurityScanRecord)
            .where(
                SecurityScanRecord.run_id == run.id,
                SecurityScanRecord.patch_hash == patch.content_hash,
            )
            .order_by(SecurityScanRecord.created_at.desc())
            .limit(1)
        )
        sec_result = await db.execute(sec_query)
        sec_record = sec_result.scalar_one_or_none()

        sec_status = None
        block_reasons = []

        if sec_record:
            sec_status = sec_record.status
            block_reasons = sec_record.block_reasons or []
        elif state_values and state_values.get("security_result"):
            sec_data = state_values.get("security_result")
            if sec_data.get("patch_hash") == patch.content_hash:
                sec_status = sec_data.get("status")
                block_reasons = sec_data.get("block_reasons", [])

        if not sec_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval rejected: patch revision {patch.revision} has not completed mandatory Security Guardian evaluation.",
            )

        if sec_status != "PASSED" or (sec_record and (sec_record.critical_count > 0 or sec_record.high_count > 0)):
            reasons_str = "; ".join(block_reasons) if block_reasons else "Mandatory security policy violation"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval rejected: Security Guardian gate is BLOCKED ({reasons_str}).",
            )

        # Check for active blocking findings in database
        active_blocker_query = select(SecurityFinding).where(
            SecurityFinding.run_id == run.id,
            SecurityFinding.patch_hash == patch.content_hash,
            SecurityFinding.is_blocking == True,
            SecurityFinding.status == "ACTIVE",
        )
        active_blockers = (await db.execute(active_blocker_query)).scalars().all()
        if active_blockers:
            reasons = [f"[{b.severity}] {b.title}" for b in active_blockers[:3]]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval rejected: Security Guardian gate is BLOCKED ({'; '.join(reasons)}).",
            )

    approval = ApprovalRecord(
        run_id=run.id,
        patch_id=patch.id,
        approver_id=current_user.id,
        decision=payload.decision,
        patch_hash=patch.content_hash,
        validation_evidence={"prior_status": run.status, "revision": patch.revision},
        feedback=payload.feedback,
    )
    db.add(approval)

    # Record distinct human audit event in immutable agent_logs
    from app.db.models.agent_log import AgentLog
    human_event_type = "human_approved" if payload.decision == "approved" else "human_rejected"
    human_message = (
        f"Authenticated maintainer ({current_user.email}) recorded {payload.decision.upper()} decision "
        f"for patch revision {patch.revision} (SHA-256: {patch.content_hash[:8]}…)."
    )
    if payload.feedback:
        human_message += f" Feedback: {payload.feedback}"

    human_audit_log = AgentLog(
        run_id=run.id,
        agent_name="human_gatekeeper",
        event_type=human_event_type,
        message=human_message,
        input_summary=f"Patch rev {patch.revision} (SHA-256: {patch.content_hash[:8]}…)",
        output_summary=f"Decision: {payload.decision.upper()}",
    )
    db.add(human_audit_log)

    # Update run lifecycle state
    if payload.decision == "approved":
        run.status = RunStatus.APPROVED.value
    else:
        run.status = RunStatus.REJECTED.value

    try:
        await db.commit()
        await db.refresh(approval)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error recording approval audit record.",
        ) from exc

    return approval


@router.get("/{run_id}/patches", response_model=list[PatchResponse])
async def list_run_patches(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> list[Patch]:
    """Retrieve all persisted patch revisions for an authorized workflow run."""
    query = select(Patch).where(Patch.run_id == run.id).order_by(Patch.revision.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{run_id}/approvals", response_model=list[ApprovalResponse])
async def list_run_approvals(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalRecord]:
    """Retrieve all recorded human approval decisions for an authorized run."""
    query = select(ApprovalRecord).where(ApprovalRecord.run_id == run.id).order_by(ApprovalRecord.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{run_id}/security")
async def get_run_security_report(
    run: Run = Depends(get_authorized_run),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve detailed AI Security Guardian findings, scan records, and gate status for a run."""
    # Fetch latest scan record
    scan_query = (
        select(SecurityScanRecord)
        .where(SecurityScanRecord.run_id == run.id)
        .order_by(SecurityScanRecord.created_at.desc())
        .limit(1)
    )
    scan_res = await db.execute(scan_query)
    latest_scan = scan_res.scalar_one_or_none()

    # Fetch all findings for run
    findings_query = (
        select(SecurityFinding)
        .where(SecurityFinding.run_id == run.id)
        .order_by(SecurityFinding.created_at.desc())
    )
    findings_res = await db.execute(findings_query)
    findings = findings_res.scalars().all()

    # Also check LangGraph state for in-flight scan data
    from app.orchestration import get_orchestrator
    orchestrator = get_orchestrator()
    state_values = await orchestrator.get_run_state(run.id) or {}
    sec_state = state_values.get("security_result")

    findings_list = [
        {
            "id": f.id,
            "category": f.category,
            "rule_id": f.rule_id,
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "confidence": f.confidence,
            "file_path": f.file_path,
            "line_start": f.line_start,
            "line_end": f.line_end,
            "evidence_redacted": f.evidence_redacted,
            "remediation": f.remediation,
            "scanner_name": f.scanner_name,
            "scanner_version": f.scanner_version,
            "is_blocking": f.is_blocking,
            "status": f.status,
            "patch_revision": f.patch_revision,
            "patch_hash": f.patch_hash,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in findings
    ]

    if latest_scan:
        return {
            "run_id": run.id,
            "status": latest_scan.status,
            "can_approve": latest_scan.status == "PASSED",
            "patch_revision": latest_scan.patch_revision,
            "patch_hash": latest_scan.patch_hash,
            "base_commit_sha": latest_scan.base_commit_sha,
            "findings_count": latest_scan.findings_count,
            "critical_count": latest_scan.critical_count,
            "high_count": latest_scan.high_count,
            "medium_count": latest_scan.medium_count,
            "low_count": latest_scan.low_count,
            "info_count": latest_scan.info_count,
            "block_reasons": latest_scan.block_reasons,
            "scanners_executed": latest_scan.scanners_executed,
            "duration_ms": latest_scan.duration_ms,
            "scanned_at": latest_scan.created_at.isoformat(),
            "findings": findings_list,
        }
    elif sec_state:
        return sec_state
    else:
        return {
            "run_id": run.id,
            "status": "UNVERIFIED",
            "can_approve": False,
            "findings_count": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "info_count": 0,
            "block_reasons": ["Security evaluation has not yet been executed for this run."],
            "scanners_executed": [],
            "findings": [],
        }
