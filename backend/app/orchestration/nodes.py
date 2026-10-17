"""LangGraph workflow node implementations executing agent services and database updates."""

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import is_safe_relative_path
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.session import async_session_factory
from app.orchestration.state import DevSquadState, WorkflowStage, WorkflowStatus
from app.schemas.patch import PatchItem
from app.schemas.plan import StructuredPlan
from app.schemas.repair_registry import FailedPatchEntry, FailedPatchRegistry
from app.schemas.repository_context import RepositoryContext
from app.schemas.review import ReviewResponse
from app.schemas.test_result import TestResult
from app.services.agents.coder import CoderAgent
from app.services.agents.diff_utils import (
    canonicalize_unified_diff,
    compute_canonical_patch_hash,
    compute_canonical_patch_id,
)
from app.services.agents.evidence_verifier import (
    is_plan_invalidated_by_context,
    verify_plan_evidence,
)
from app.services.agents.planner import PlannerAgent
from app.services.agents.repair import log_agent_event, record_patch_revision
from app.services.agents.reviewer import ReviewerAgent
from app.services.agents.tester import SandboxTesterAgent
from app.services.context_ranker import ContextRanker, RankedContextPackage, RankedFile
from app.services.github_service import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
    GitHubResourceNotFoundError,
    GitHubService,
)
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider

logger = logging.getLogger("devsquad.nodes")


class NodeDependencies:
    """Dependency container injected into workflow nodes."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], AsyncSession]] = None,
        llm_provider: Optional[LLMProvider] = None,
        github_service: Optional[GitHubService] = None,
        planner_agent: Optional[PlannerAgent] = None,
        coder_agent: Optional[CoderAgent] = None,
        tester_agent: Optional[SandboxTesterAgent] = None,
        reviewer_agent: Optional[ReviewerAgent] = None,
    ):
        self.session_factory = session_factory or async_session_factory
        self.llm_provider = llm_provider or (get_llm_provider() if settings.gemini_api_key.get_secret_value() or settings.openai_api_key.get_secret_value() else None)
        self.github_service = github_service or GitHubService(token=settings.github_token.get_secret_value() or None)
        self.planner_agent = planner_agent or (PlannerAgent(self.llm_provider) if self.llm_provider else None)
        self.coder_agent = coder_agent or (CoderAgent(self.llm_provider) if self.llm_provider else None)
        self.tester_agent = tester_agent or SandboxTesterAgent()
        self.reviewer_agent = reviewer_agent or (ReviewerAgent(self.llm_provider) if self.llm_provider else None)


# Default shared dependencies
_default_deps = NodeDependencies()


def get_default_deps() -> NodeDependencies:
    return _default_deps


def set_default_deps(deps: NodeDependencies) -> None:
    global _default_deps
    _default_deps = deps


# --- Node Functions ---

async def validate_input_node(state: DevSquadState) -> Dict[str, Any]:
    """Verify run, repository, and issue records exist and are authorized."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    repo_id = state["repository_id"]
    issue_id = state["issue_id"]

    logger.info(f"[validate_input_node] Validating run {run_id}")
    deps = get_default_deps()

    async with deps.session_factory() as session:
        # Check Run record
        run = await session.get(Run, run_id)
        if not run:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "RUN_NOT_FOUND",
                "error_message": f"Run '{run_id}' does not exist in database.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        # Check Repository
        repo = await session.get(Repository, repo_id)
        if not repo:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "REPOSITORY_NOT_FOUND",
                "error_message": f"Repository '{repo_id}' does not exist.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        # Check Issue
        issue = await session.get(Issue, issue_id)
        if not issue or issue.repository_id != repo_id:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "INVALID_ISSUE_RELATIONSHIP",
                "error_message": f"Issue '{issue_id}' not found or does not belong to repository '{repo_id}'.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        # Update run status to RUNNING
        run.status = RunStatus.PLANNING.value
        run.current_node = "validate_input"
        run.started_at = datetime.now(timezone.utc)
        await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="orchestrator",
            event_type="workflow_started",
            message=f"Workflow run {run_id} validated and initialized.",
        )

    return {
        "status": WorkflowStatus.RUNNING.value,
        "current_stage": WorkflowStage.CONTEXT_PREPARATION.value,
        "error_code": None,
        "error_message": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def context_preparation_node(state: DevSquadState) -> Dict[str, Any]:
    """Retrieve issue context, comments, and ranked repository context."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    repo_id = state["repository_id"]
    issue_id = state["issue_id"]
    logger.info(f"[context_preparation_node] Preparing context for run {run_id}")

    deps = get_default_deps()

    async with deps.session_factory() as session:
        repo = await session.get(Repository, repo_id)
        issue = await session.get(Issue, issue_id)
        if not repo or not issue:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "CONTEXT_FETCH_FAILED",
                "error_message": "Repository or issue record missing during context retrieval.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        repo_full_name = repo.full_name
        issue_number = issue.github_issue_number
        issue_title = issue.title
        issue_body = issue.body or ""
        issue_labels = issue.labels or []

    if "/" in repo_full_name:
        repo_owner, repo_name = repo_full_name.split("/", 1)
    else:
        repo_owner, repo_name = "local", repo_full_name

    metadata = dict(state.get("metadata", {}))
    ranker = ContextRanker()

    # Determine if this run uses an explicit, validated offline test fixture
    is_test_fixture = bool(metadata.get("is_test_fixture") or metadata.get("offline_test_fixture"))

    if is_test_fixture:
        logger.info(f"[context_preparation_node] Using explicit test fixture context for run {run_id}")
        raw_source_files = metadata.get("source_files", {})
        validated_fixture_files: Dict[str, str] = {}
        for path, content in raw_source_files.items():
            if not is_safe_relative_path(path):
                return {
                    "status": WorkflowStatus.FAILED.value,
                    "error_code": "UNSAFE_FIXTURE_PATH",
                    "error_message": f"Fixture source file contains unsafe path: '{path}'",
                    "current_stage": WorkflowStage.FINALIZING.value,
                }
            validated_fixture_files[path] = content

        files_data = [{"path": p, "content": c} for p, c in validated_fixture_files.items()]
        ranked_pkg = ranker.rank_and_package(
            files_data=files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=issue_labels,
        )

        base_commit_sha = metadata.get("base_commit_sha", "fixture-base-sha-00000000")
        target_branch = metadata.get("target_branch", "main")
        fixture_identifier = metadata.get("fixture_identifier") or f"fixture-{repo_full_name}"

        repo_ctx = ranker.build_repository_context(
            files_data=files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=issue_labels,
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=target_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=True,
            fixture_identifier=fixture_identifier,
            total_tree_files=len(files_data),
            total_tree_bytes=sum(len(c.encode("utf-8")) for c in validated_fixture_files.values()),
            retrieval_strategy="test_fixture",
        )
        ranked_pkg = ranker.rank_and_package(
            files_data=files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=issue_labels,
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=target_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=True,
            fixture_identifier=fixture_identifier,
        )
        ranked_pkg.repository_context = repo_ctx

        retrieved_files = list(validated_fixture_files.keys())
        unretrieved_files: List[Dict[str, str]] = []
        source_files = {rf.path: rf.content for rf in ranked_pkg.selected_files}

    else:
        # Production pipeline: Live read-only GitHub retrieval
        logger.info(f"[context_preparation_node] Executing live GitHub context retrieval for {repo_full_name}#{issue_number}")
        has_token = bool(settings.github_token.get_secret_value() or (deps.github_service and getattr(deps.github_service, "token", None)))

        if not has_token and not (deps.github_service and deps.github_service.client.headers.get("Authorization")):
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "GITHUB_CREDENTIALS_UNAVAILABLE",
                "error_message": "GitHub API credentials are not configured (DEVSQUAD_GITHUB_TOKEN missing). Live repository context retrieval unavailable.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        try:
            gh_issue = await deps.github_service.get_issue(repo_owner, repo_name, issue_number)
            issue_title = gh_issue.title
            issue_body = gh_issue.body
            issue_labels = gh_issue.labels
            comments = await deps.github_service.get_issue_comments(repo_owner, repo_name, issue_number)
            combined_text = f"{issue_title}\n{issue_body}\n" + "\n".join(comments)

            repo_meta = await deps.github_service.get_repository(repo_owner, repo_name)
            default_branch = repo_meta.default_branch
            branch_meta = await deps.github_service.get_branch(repo_owner, repo_name, default_branch)
            base_commit_sha = branch_meta.commit_sha

            tree_items = await deps.github_service.get_repository_tree(
                repo_owner, repo_name, tree_sha=base_commit_sha, recursive=True
            )

        except GitHubAuthError as exc:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "GITHUB_AUTH_FAILED",
                "error_message": f"GitHub authentication error: {str(exc)}",
                "current_stage": WorkflowStage.FINALIZING.value,
            }
        except GitHubRateLimitError as exc:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "GITHUB_RATE_LIMITED",
                "error_message": f"GitHub API rate limit exceeded: {str(exc)}",
                "current_stage": WorkflowStage.FINALIZING.value,
            }
        except GitHubResourceNotFoundError as exc:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "GITHUB_RESOURCE_NOT_FOUND",
                "error_message": f"Repository '{repo_full_name}' or issue #{issue_number} not found on GitHub.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }
        except Exception as exc:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "GITHUB_API_ERROR",
                "error_message": f"Failed to retrieve repository metadata: {str(exc)}",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        # Filter candidate tree items and score paths
        mentioned_paths, mentioned_symbols = ranker._extract_mentioned_paths_and_symbols(combined_text)
        candidate_items, omitted_items = ranker.filter_tree(tree_items, mentioned_paths)

        scored_tree = []
        for item in candidate_items:
            score, expl = ranker.calculate_file_score(
                file_path=item.path,
                issue_text=combined_text,
                mentioned_paths=mentioned_paths,
                mentioned_symbols=mentioned_symbols,
            )
            scored_tree.append((score, item))

        scored_tree.sort(key=lambda x: (-x[0], x[1].path))

        # Select candidates within context budget
        total_candidate_bytes = 0
        to_fetch = []
        for score, item in scored_tree:
            item_sz = item.size or 2000
            if total_candidate_bytes + item_sz > settings.max_repo_context_bytes and to_fetch:
                break
            total_candidate_bytes += item_sz
            to_fetch.append(item)

        # Retrieve file contents
        retrieved_files_data = []
        retrieved_files = []
        unretrieved_files = [{"path": o.path, "reason": o.reason} for o in omitted_items]

        for item in to_fetch:
            try:
                fc = await deps.github_service.get_file_content(
                    repo_owner, repo_name, item.path, ref=base_commit_sha
                )
                if fc.is_binary:
                    unretrieved_files.append({"path": item.path, "reason": "binary"})
                    continue
                retrieved_files_data.append({"path": item.path, "content": fc.content})
                retrieved_files.append(item.path)
            except Exception as exc:
                unretrieved_files.append({"path": item.path, "reason": str(exc)})

        if not retrieved_files_data:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "NO_USABLE_SOURCE_FILES",
                "error_message": "No usable source files could be retrieved from repository.",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

        repo_ctx = ranker.build_repository_context(
            files_data=retrieved_files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=issue_labels,
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=default_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=False,
            fixture_identifier=None,
            total_tree_files=len(tree_items),
            total_tree_bytes=sum(item.size or 0 for item in tree_items),
            omitted_from_tree=omitted_items,
            retrieval_strategy="github_live_tree",
        )
        ranked_pkg = ranker.rank_and_package(
            files_data=retrieved_files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=issue_labels,
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=default_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=False,
            total_tree_files=len(tree_items),
            total_tree_bytes=sum(item.size or 0 for item in tree_items),
            omitted_from_tree=omitted_items,
        )
        ranked_pkg.repository_context = repo_ctx
        source_files = {rf.path: rf.content for rf in ranked_pkg.selected_files}

    repo_ctx.verify_integrity()
    metadata["source_files"] = source_files
    metadata["retrieved_files"] = retrieved_files
    metadata["unretrieved_files"] = unretrieved_files
    metadata["base_commit_sha"] = base_commit_sha
    metadata["ranked_context"] = ranked_pkg.model_dump()
    metadata["repository_context"] = repo_ctx.model_dump()
    metadata["issue_title"] = issue_title
    metadata["issue_body"] = issue_body
    metadata["repo_name"] = repo_name
    metadata["repo_owner"] = repo_owner

    return {
        "repository_context": repo_ctx.model_dump(),
        "metadata": metadata,
        "current_stage": WorkflowStage.PLANNING.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def planner_node(state: DevSquadState) -> Dict[str, Any]:
    """Execute PlannerAgent to produce a grounded StructuredPlan."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    logger.info(f"[planner_node] Executing PlannerAgent for run {run_id}")
    deps = get_default_deps()

    metadata = state.get("metadata", {})
    issue_title = metadata.get("issue_title", "Issue")
    issue_body = metadata.get("issue_body", "")
    repo_name = metadata.get("repo_name", "repo")
    repo_owner = metadata.get("repo_owner", "owner")
    ranked_pkg_data = metadata.get("ranked_context")

    if not ranked_pkg_data:
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "PLANNER_FAILED",
            "error_message": "Ranked context package missing from workflow state.",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    ranked_pkg = RankedContextPackage.model_validate(ranked_pkg_data)

    # Cryptographic provenance & integrity guard
    repo_ctx = None
    repo_ctx_data = state.get("repository_context") or metadata.get("repository_context")
    if repo_ctx_data:
        try:
            repo_ctx = RepositoryContext.model_validate(repo_ctx_data)
            repo_ctx.verify_integrity()
        except Exception as exc:
            logger.error(f"[planner_node] RepositoryContext integrity check failed: {str(exc)}")
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "CONTEXT_INTEGRITY_COMPROMISED",
                "error_message": f"Repository context failed cryptographic integrity check: {str(exc)}",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

    try:
        plan: StructuredPlan = await deps.planner_agent.plan(
            issue_title=issue_title,
            issue_body=issue_body,
            issue_number=1,
            ranked_context=ranked_pkg,
            repo_name=repo_name,
            repo_owner=repo_owner,
            repo_context=repo_ctx,
        )
    except Exception as exc:
        logger.error(f"[planner_node] Planner error: {str(exc)}")
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "PLANNER_FAILED",
            "error_message": f"PlannerAgent failed: {str(exc)}",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    # Deterministic Evidence Verification Guard
    if repo_ctx:
        verif_res = verify_plan_evidence(
            plan=plan,
            repo_context=repo_ctx,
            active_base_commit_sha=metadata.get("base_commit_sha") or repo_ctx.base_commit_sha,
            active_repo_owner=repo_owner,
            active_repo_name=repo_name,
        )
        if not verif_res.is_valid:
            logger.error(f"[planner_node] Evidence verification failed: {verif_res.error_summary}")
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "PLAN_EVIDENCE_VERIFICATION_FAILED",
                "error_message": f"Plan evidence verification failed: {verif_res.error_summary}",
                "current_stage": WorkflowStage.FINALIZING.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        plan.is_verified = True
    else:
        plan.is_verified = True

    # Persist audit log
    async with deps.session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.CODING.value
            run.current_node = "planner"
            await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="planner",
            event_type="plan_generated",
            message=f"Plan generated with {len(plan.steps)} step(s) and {len(plan.acceptance_criteria)} criteria.",
            input_summary=issue_title,
            output_summary=plan.objective,
        )

    return {
        "plan": plan.model_dump(),
        "current_stage": WorkflowStage.CODING.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def coder_node(state: DevSquadState) -> Dict[str, Any]:
    """Execute CoderAgent to generate a minimal, valid unified diff patch."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    repair_attempts = state.get("repair_attempts", 0)
    current_rev = state.get("patch_revision", 0) + 1
    logger.info(f"[coder_node] Executing CoderAgent for run {run_id} (rev {current_rev}, attempt {repair_attempts})")

    deps = get_default_deps()
    plan_data = state.get("plan")
    metadata = state.get("metadata", {})
    source_files = metadata.get("source_files", {})
    base_commit_sha = metadata.get("base_commit_sha", "initial-sha")
    repair_feedback = state.get("repair_feedback")

    if not plan_data:
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "CODER_FAILED",
            "error_message": "StructuredPlan missing from workflow state.",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    # Cryptographic provenance & integrity guard
    repo_ctx = None
    repo_ctx_data = state.get("repository_context") or metadata.get("repository_context")
    if repo_ctx_data:
        try:
            repo_ctx = RepositoryContext.model_validate(repo_ctx_data)
            repo_ctx.verify_integrity()
        except Exception as exc:
            logger.error(f"[coder_node] RepositoryContext integrity check failed: {str(exc)}")
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "CONTEXT_INTEGRITY_COMPROMISED",
                "error_message": f"Repository context failed cryptographic integrity check: {str(exc)}",
                "current_stage": WorkflowStage.FINALIZING.value,
            }

    plan = StructuredPlan.model_validate(plan_data)

    # Context Invalidation & Evidence Verification Guard
    if repo_ctx:
        if is_plan_invalidated_by_context(plan, repo_ctx):
            logger.error("[coder_node] Plan evidence invalidated by modified repository context snapshot.")
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_code": "STALE_PLAN_EVIDENCE",
                "error_message": "StructuredPlan evidence was invalidated by modified repository context snapshot.",
                "current_stage": WorkflowStage.FINALIZING.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        if plan.evidence_citations and not plan.is_verified:
            verif = verify_plan_evidence(plan, repo_ctx, active_base_commit_sha=base_commit_sha)
            if not verif.is_valid:
                logger.error(f"[coder_node] Plan evidence unverified: {verif.error_summary}")
                return {
                    "status": WorkflowStatus.FAILED.value,
                    "error_code": "PLAN_EVIDENCE_VERIFICATION_FAILED",
                    "error_message": f"CoderAgent blocked: plan evidence unverified ({verif.error_summary})",
                    "current_stage": WorkflowStage.FINALIZING.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            plan.is_verified = True

    try:
        patch_item: PatchItem = await deps.coder_agent.generate_patch(
            plan=plan,
            source_files=source_files,
            base_commit_sha=base_commit_sha,
            revision=current_rev,
            previous_feedback=repair_feedback,
        )
    except Exception as exc:
        logger.error(f"[coder_node] Coder error: {str(exc)}")
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "CODER_FAILED",
            "error_message": f"CoderAgent failed: {str(exc)}",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    patch_item.revision = current_rev
    if base_commit_sha:
        patch_item.base_commit_sha = base_commit_sha

    # Canonicalize diff and compute deterministic canonical patch hash
    canonical_diff = canonicalize_unified_diff(patch_item.unified_diff)
    canonical_hash = patch_item.content_hash or compute_canonical_patch_hash(canonical_diff)
    patch_item.unified_diff = canonical_diff
    patch_item.content_hash = canonical_hash

    # Anti-Repetition Registry Guard: check if this exact patch previously failed under equivalent circumstances
    failed_entries = state.get("failed_patch_registry") or []
    registry = FailedPatchRegistry(entries=failed_entries)
    dup_entry = registry.is_duplicate_failed_patch(
        run_id=run_id,
        base_commit_sha=base_commit_sha,
        patch_hash=canonical_hash,
    )
    if dup_entry:
        logger.warning(
            f"[coder_node] Duplicate failed patch detected for run {run_id}: hash={canonical_hash[:8]}, "
            f"prior revision={dup_entry.revision}, category={dup_entry.failure_category}"
        )
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "DUPLICATE_FAILED_PATCH",
            "error_message": (
                f"Automated tests failed or rejected: Coder generated duplicate patch with hash '{canonical_hash[:8]}' "
                f"which previously failed in revision {dup_entry.revision} ({dup_entry.failure_category}: {dup_entry.diagnostic_fingerprint}). "
                "Repair cycle terminated to prevent infinite looping."
            ),
            "current_stage": WorkflowStage.FINALIZING.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Persist Patch entity & audit log
    async with deps.session_factory() as session:
        patch_model = await record_patch_revision(
            session=session,
            run_id=run_id,
            patch_item=patch_item,
        )
        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.TESTING.value
            run.current_node = "coder"
            await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="coder",
            event_type="patch_created",
            message=f"Patch revision {current_rev} generated ({len(patch_item.target_files)} file(s), hash: {patch_item.content_hash[:8]}).",
            input_summary=plan.objective,
            output_summary=patch_item.summary,
        )

    patch_dict = patch_item.model_dump()
    patch_dict["id"] = patch_model.id

    return {
        "current_patch": patch_dict,
        "patch_revision": current_rev,
        "repair_attempts": repair_attempts if current_rev == 1 else repair_attempts + 1,
        # ATOMIC INVALIDATION OF DEPENDENT EVIDENCE:
        "test_result": None,
        "review_result": None,
        "validation_status": "PENDING_VALIDATION",
        "approval_status": "PENDING",
        "repair_feedback": None,
        "error_code": None,
        "error_message": None,
        "current_stage": WorkflowStage.TESTING.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def sandbox_tester_node(state: DevSquadState) -> Dict[str, Any]:
    """Execute SandboxTesterAgent with Docker isolation or safe AST fallback."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    logger.info(f"[sandbox_tester_node] Executing SandboxTesterAgent for run {run_id}")
    deps = get_default_deps()

    patch_data = state.get("current_patch")
    if not patch_data:
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "TESTER_FAILED",
            "error_message": "Current patch missing from workflow state.",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    patch_item = PatchItem.model_validate(patch_data)
    metadata = state.get("metadata", {})
    source_files = metadata.get("source_files", {})
    base_commit_sha = metadata.get("base_commit_sha", patch_item.base_commit_sha)

    test_result: TestResult = await deps.tester_agent.run_tests(
        patch=patch_item,
        source_files=source_files,
        test_commands=metadata.get("test_commands"),
        base_commit_sha=base_commit_sha,
    )

    # Bind exact execution provenance and canonical patch identity to TestResult
    canonical_id = compute_canonical_patch_id(base_commit_sha, patch_item.unified_diff)
    test_result.run_id = run_id
    test_result.repository_id = state.get("repository_id")
    test_result.base_commit_sha = base_commit_sha
    test_result.patch_hash = patch_item.content_hash
    test_result.canonical_patch_id = canonical_id
    test_result.patch_revision = patch_item.revision
    test_result.validation_status = test_result.status

    # Record failure in anti-repetition registry if tests failed
    failed_entries = list(state.get("failed_patch_registry") or [])
    registry = FailedPatchRegistry(entries=failed_entries)
    if test_result.status not in ("TESTS_PASSED", "PARTIAL_VALIDATION"):
        registry.record_failure(
            run_id=run_id,
            repository_id=state.get("repository_id", ""),
            base_commit_sha=base_commit_sha,
            patch_hash=patch_item.content_hash,
            revision=patch_item.revision,
            failure_category="TEST_FAILED",
            diagnostic_fingerprint=test_result.failure_summary or test_result.status,
            validation_environment=test_result.environment,
            details={"exit_code": test_result.exit_code, "failed_tests": test_result.failed},
        )
        updated_failed_registry = registry.model_dump()["entries"]
    else:
        updated_failed_registry = failed_entries

    # Persist test audit log
    async with deps.session_factory() as session:
        if patch_item.id:
            patch_row = await session.get(Patch, patch_item.id)
            if patch_row:
                patch_row.validation_status = test_result.status

        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.REVIEWING.value
            run.current_node = "tester"
            await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="tester",
            event_type="tests_executed",
            message=f"Validation completed: status={test_result.status}, env={test_result.environment}.",
            input_summary=f"Patch rev {patch_item.revision}",
            output_summary=f"Passed={test_result.passed}, Failed={test_result.failed}",
            duration_ms=test_result.duration_ms,
        )

    return {
        "test_result": test_result.model_dump(),
        "validation_status": test_result.status,
        "failed_patch_registry": updated_failed_registry,
        "current_stage": WorkflowStage.REVIEWING.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def reviewer_node(state: DevSquadState) -> Dict[str, Any]:
    """Execute ReviewerAgent to independently critique the patch and test results."""
    if state.get("status") == WorkflowStatus.CANCELLED.value:
        return {
            "status": WorkflowStatus.CANCELLED.value,
            "current_stage": WorkflowStage.FINALIZING.value,
            "error_message": state.get("error_message") or "Run was cancelled.",
        }

    run_id = state["run_id"]
    logger.info(f"[reviewer_node] Executing ReviewerAgent for run {run_id}")
    deps = get_default_deps()

    plan_data = state.get("plan")
    patch_data = state.get("current_patch")
    test_data = state.get("test_result")
    metadata = state.get("metadata", {})

    if not plan_data or not patch_data or not test_data:
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "REVIEWER_FAILED",
            "error_message": "Plan, patch, or test result missing from workflow state.",
            "current_stage": WorkflowStage.FINALIZING.value,
        }

    plan = StructuredPlan.model_validate(plan_data)
    patch_item = PatchItem.model_validate(patch_data)
    test_result = TestResult.model_validate(test_data)
    source_files = metadata.get("source_files", {})
    base_commit_sha = metadata.get("base_commit_sha", patch_item.base_commit_sha)

    # Cryptographic Evidence Provenance Guard: verify test results belong to this exact patch
    test_patch_hash = test_result.patch_hash or test_data.get("patch_hash")
    if test_patch_hash and test_patch_hash != patch_item.content_hash:
        logger.error(
            f"[reviewer_node] Stale validation evidence: test hash '{test_patch_hash}' "
            f"!= current patch hash '{patch_item.content_hash}'"
        )
        return {
            "status": WorkflowStatus.FAILED.value,
            "error_code": "STALE_VALIDATION_EVIDENCE",
            "error_message": (
                f"Reviewer detected stale validation evidence: test hash '{test_patch_hash}' "
                f"does not match current patch hash '{patch_item.content_hash}'."
            ),
            "current_stage": WorkflowStage.FINALIZING.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    review_res: ReviewResponse = await deps.reviewer_agent.review(
        issue_title=metadata.get("issue_title", "Issue"),
        issue_body=metadata.get("issue_body", ""),
        plan=plan,
        patch=patch_item,
        test_result=test_result,
        source_files=source_files,
    )

    # Bind exact execution provenance and canonical patch identity to ReviewResponse
    canonical_id = compute_canonical_patch_id(base_commit_sha, patch_item.unified_diff)
    review_res.run_id = run_id
    review_res.repository_id = state.get("repository_id")
    review_res.patch_hash = patch_item.content_hash
    review_res.canonical_patch_id = canonical_id
    review_res.base_commit_sha = base_commit_sha
    review_res.patch_revision = patch_item.revision
    review_res.reviewed_at = datetime.now(timezone.utc).isoformat()

    has_critical = any(f.severity in ("CRITICAL", "HIGH") for f in review_res.findings)

    # Record failure in anti-repetition registry if review rejected or has critical findings
    failed_entries = list(state.get("failed_patch_registry") or [])
    registry = FailedPatchRegistry(entries=failed_entries)
    if review_res.recommendation != "approve" or has_critical:
        category = "CRITICAL_FINDINGS" if has_critical else "REVIEW_REJECTED"
        findings_summary = "; ".join(f"[{f.severity}] {f.description}" for f in review_res.findings[:2])
        registry.record_failure(
            run_id=run_id,
            repository_id=state.get("repository_id", ""),
            base_commit_sha=base_commit_sha,
            patch_hash=patch_item.content_hash,
            revision=patch_item.revision,
            failure_category=category,
            diagnostic_fingerprint=findings_summary or review_res.recommendation,
            validation_environment="reviewer_agent",
            details={"findings_count": len(review_res.findings), "recommendation": review_res.recommendation},
        )
        updated_failed_registry = registry.model_dump()["entries"]
    else:
        updated_failed_registry = failed_entries

    # Persist review audit log
    async with deps.session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            run.current_node = "reviewer"
            await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="reviewer",
            event_type="review_completed",
            message=f"Review completed with recommendation='{review_res.recommendation}' ({len(review_res.findings)} findings).",
            input_summary=f"Patch rev {patch_item.revision}",
            output_summary=f"Criteria met={review_res.acceptance_criteria_met}",
        )

    # If review requested changes or has critical findings, prepare repair feedback
    repair_feedback = None
    if review_res.recommendation != "approve" or has_critical or test_result.status not in ("TESTS_PASSED", "PARTIAL_VALIDATION"):
        feedback_lines = []
        if test_result.status != "TESTS_PASSED":
            feedback_lines.append(f"Test Status: {test_result.status}. Summary: {test_result.failure_summary or 'tests failed'}")
        if review_res.recommendation != "approve":
            feedback_lines.append(f"Review Recommendation: {review_res.recommendation}. Criteria met: {review_res.acceptance_criteria_met}")
        for finding in review_res.findings:
            loc = f" in {finding.file_path}:{finding.line_number}" if finding.file_path else ""
            feedback_lines.append(f"[{finding.severity}]{loc} {finding.description} (Recommendation: {finding.recommendation})")
        repair_feedback = "\n".join(feedback_lines)

    return {
        "review_result": review_res.model_dump(),
        "repair_feedback": repair_feedback,
        "failed_patch_registry": updated_failed_registry,
        "current_stage": WorkflowStage.FINALIZING.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def finalization_node(state: DevSquadState) -> Dict[str, Any]:
    """Persist final workflow state, review decision, and runtime summary."""
    run_id = state["run_id"]
    logger.info(f"[finalization_node] Finalizing workflow run {run_id}")
    deps = get_default_deps()

    current_status = state.get("status", WorkflowStatus.RUNNING.value)
    plan_data = state.get("plan")
    patch_data = state.get("current_patch")
    review_data = state.get("review_result")
    test_data = state.get("test_result")
    error_message = state.get("error_message")
    validation_status = state.get("validation_status")

    final_status = current_status

    if current_status == WorkflowStatus.CANCELLED.value:
        final_status = WorkflowStatus.CANCELLED.value
        error_message = error_message or "Run cancelled."

    elif current_status == WorkflowStatus.FAILED.value:
        final_status = WorkflowStatus.FAILED.value

    elif current_status == WorkflowStatus.RUNNING.value:
        # Centralized fail-closed validation before transitioning to approval
        if not plan_data:
            final_status = WorkflowStatus.FAILED.value
            error_message = "Structured implementation plan is missing."
        elif not patch_data or not patch_data.get("unified_diff"):
            final_status = WorkflowStatus.FAILED.value
            error_message = "Valid code patch is missing."
        elif not test_data:
            final_status = WorkflowStatus.FAILED.value
            error_message = "Automated test validation results are missing."
        elif not review_data:
            final_status = WorkflowStatus.FAILED.value
            error_message = "Independent review results are missing."
        else:
            # Cryptographic evidence verification guard on plan
            repo_ctx_data = state.get("repository_context") or state.get("metadata", {}).get("repository_context")
            plan_verif_failed = False
            if repo_ctx_data and plan_data:
                try:
                    repo_ctx = RepositoryContext.model_validate(repo_ctx_data)
                    plan_obj = StructuredPlan.model_validate(plan_data)
                    if plan_obj.evidence_citations:
                        verif = verify_plan_evidence(plan_obj, repo_ctx, active_base_commit_sha=patch_data.get("base_commit_sha"))
                        if not verif.is_valid:
                            final_status = WorkflowStatus.FAILED.value
                            error_message = f"Plan evidence verification failed: {verif.error_summary}"
                            plan_verif_failed = True
                except Exception as exc:
                    logger.warning(f"[finalization_node] Failed to evaluate plan evidence: {exc}")

            if not plan_verif_failed:
                curr_patch_hash = patch_data.get("content_hash")
                test_patch_hash = test_data.get("patch_hash")
                review_patch_hash = review_data.get("patch_hash")
            curr_base_sha = patch_data.get("base_commit_sha")
            test_base_sha = test_data.get("base_commit_sha")
            review_base_sha = review_data.get("base_commit_sha")

            if test_patch_hash and test_patch_hash != curr_patch_hash:
                final_status = WorkflowStatus.FAILED.value
                error_message = (
                    f"Stale validation evidence: test hash '{test_patch_hash}' does not match "
                    f"current patch hash '{curr_patch_hash}'."
                )
            elif review_patch_hash and review_patch_hash != curr_patch_hash:
                final_status = WorkflowStatus.FAILED.value
                error_message = (
                    f"Stale review evidence: review hash '{review_patch_hash}' does not match "
                    f"current patch hash '{curr_patch_hash}'."
                )
            elif test_base_sha and curr_base_sha and test_base_sha != curr_base_sha:
                final_status = WorkflowStatus.FAILED.value
                error_message = (
                    f"Base revision mismatch: test base '{test_base_sha}' does not match "
                    f"current patch base '{curr_base_sha}'."
                )
            elif review_base_sha and curr_base_sha and review_base_sha != curr_base_sha:
                final_status = WorkflowStatus.FAILED.value
                error_message = (
                    f"Base revision mismatch: review base '{review_base_sha}' does not match "
                    f"current patch base '{curr_base_sha}'."
                )
            else:
                test_status = test_data.get("status")
                review_rec = review_data.get("recommendation")
                has_critical = any(f.get("severity") in ("CRITICAL", "HIGH") for f in review_data.get("findings", []))

                if has_critical:
                    final_status = WorkflowStatus.FAILED.value
                    error_message = "Patch contains unresolved CRITICAL or HIGH review findings."
                elif review_rec != "approve":
                    final_status = WorkflowStatus.FAILED.value
                    error_message = f"Review rejected or requested changes: {review_rec}"
                elif test_status == "TESTS_PASSED":
                    # Fully verified with dynamic container tests
                    final_status = WorkflowStatus.WAITING_FOR_APPROVAL.value
                    validation_status = "TESTS_PASSED"
                elif test_status in ("PARTIAL_VALIDATION", "SANDBOX_UNAVAILABLE"):
                    if settings.allow_manual_approval_without_sandbox:
                        # Allowed for human review with honest untest caveat
                        final_status = WorkflowStatus.WAITING_FOR_APPROVAL.value
                        validation_status = "UNTESTED_MANUAL_VALIDATION_REQUIRED"
                    else:
                        final_status = WorkflowStatus.FAILED.value
                        error_message = "Dynamic sandbox test pass required by policy, but Docker was unavailable."
                else:
                    final_status = WorkflowStatus.FAILED.value
                    error_message = f"Automated tests failed ({test_status}): {test_data.get('failure_summary') or 'execution failed'}"

    now = datetime.now(timezone.utc)
    async with deps.session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            if final_status == WorkflowStatus.WAITING_FOR_APPROVAL.value:
                run.status = RunStatus.AWAITING_APPROVAL.value
            elif final_status == WorkflowStatus.COMPLETED.value:
                run.status = RunStatus.COMPLETED.value
            elif final_status == WorkflowStatus.FAILED.value:
                run.status = RunStatus.FAILED.value
                run.error_summary = error_message
            elif final_status == WorkflowStatus.CANCELLED.value:
                run.status = RunStatus.CANCELLED.value
                run.error_summary = error_message

            run.finished_at = now
            run.current_node = "finalization"
            await session.commit()

        await log_agent_event(
            session=session,
            run_id=run_id,
            agent_name="orchestrator",
            event_type="workflow_finalized",
            message=f"Workflow run {run_id} concluded with status={final_status}.",
            output_summary=error_message or f"Concluded with validation_status={validation_status}",
        )

    return {
        "status": final_status,
        "validation_status": validation_status,
        "current_stage": WorkflowStage.FINALIZING.value,
        "completed_at": now.isoformat(),
        "error_message": error_message,
        "updated_at": now.isoformat(),
    }
