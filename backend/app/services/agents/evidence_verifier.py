"""Deterministic evidence verification engine for Grounded Planning."""
import logging
from typing import Dict, List, Optional

from app.core.security import is_safe_relative_path
from app.schemas.evidence import (
    EvidenceReference,
    PlanVerificationIssue,
    PlanVerificationResult,
)
from app.schemas.plan import StructuredPlan
from app.schemas.repository_context import ContextFile, RepositoryContext

logger = logging.getLogger("devsquad.evidence_verifier")


def verify_plan_evidence(
    plan: StructuredPlan,
    repo_context: Optional[RepositoryContext],
    active_base_commit_sha: Optional[str] = None,
    active_repo_owner: Optional[str] = None,
    active_repo_name: Optional[str] = None,
) -> PlanVerificationResult:
    """
    Deterministically verify all evidence citations and proposed target files in a StructuredPlan
    against the verified, immutable RepositoryContext snapshot.

    Acceptance Rules:
    1. Repository Identity: Citations must reference the active repository and base commit SHA.
    2. File Existence: Every cited file must exist in the verified context's selected_files.
    3. Cryptographic Hash: Cited file_sha256 must strictly match the stored file SHA-256.
    4. Line Span: Start and end lines must be valid (1 <= start_line <= end_line <= total_lines).
    5. Excerpt Integrity: Quoted excerpts must match the actual source content within the cited line span.
    6. Truncation Guard: Citations from truncated files are flagged with warnings.
    7. Target Files Grounding: Proposed target files must exist in context or be acknowledged as new files.
    """
    issues: List[PlanVerificationIssue] = []
    warnings: List[str] = []
    verified_count = 0

    if not repo_context:
        if plan.evidence_citations:
            issues.append(
                PlanVerificationIssue(
                    code="MISSING_REPOSITORY_CONTEXT",
                    message="Plan contains evidence citations but no verified RepositoryContext was provided for verification.",
                )
            )
            return PlanVerificationResult(
                is_valid=False,
                verified_citations_count=0,
                issues=issues,
                error_summary="No RepositoryContext available to verify citations.",
            )
        # Plan without citations and without context (e.g. lightweight synthetic)
        return PlanVerificationResult(
            is_valid=True,
            verified_citations_count=0,
            issues=[],
            warnings=["No RepositoryContext provided for verification."],
        )

    # Context file index: path -> ContextFile
    context_files: Dict[str, ContextFile] = {f.path: f for f in repo_context.selected_files}
    expected_base_sha = (active_base_commit_sha or repo_context.base_commit_sha).strip()
    expected_owner = (active_repo_owner or repo_context.repo_owner).strip() if (active_repo_owner or repo_context.repo_owner) else None
    expected_name = (active_repo_name or repo_context.repo_name).strip() if (active_repo_name or repo_context.repo_name) else None

    # 1. Verify Each Evidence Citation
    for idx, citation in enumerate(plan.evidence_citations):
        # A. Path safety
        if not is_safe_relative_path(citation.file_path):
            issues.append(
                PlanVerificationIssue(
                    code="UNSAFE_FILE_PATH",
                    message=f"Citation [{idx}] path '{citation.file_path}' fails path safety validation.",
                    citation_index=idx,
                    file_path=citation.file_path,
                )
            )
            continue

        # B. Repository Identity & Commit SHA Verification
        if citation.base_commit_sha != expected_base_sha:
            issues.append(
                PlanVerificationIssue(
                    code="COMMIT_MISMATCH",
                    message=(
                        f"Citation [{idx}] references commit '{citation.base_commit_sha}' which does not "
                        f"match expected base commit '{expected_base_sha}'."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                    details={"citation_sha": citation.base_commit_sha, "expected_sha": expected_base_sha},
                )
            )
            continue

        if citation.repo_owner and expected_owner and citation.repo_owner != expected_owner:
            issues.append(
                PlanVerificationIssue(
                    code="REPOSITORY_MISMATCH",
                    message=(
                        f"Citation [{idx}] repo_owner '{citation.repo_owner}' does not match "
                        f"active repository owner '{expected_owner}'."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                )
            )
            continue

        if citation.repo_name and expected_name and citation.repo_name != expected_name:
            issues.append(
                PlanVerificationIssue(
                    code="REPOSITORY_MISMATCH",
                    message=(
                        f"Citation [{idx}] repo_name '{citation.repo_name}' does not match "
                        f"active repository name '{expected_name}'."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                )
            )
            continue

        # C. File Existence in Verified Context
        if citation.file_path not in context_files:
            issues.append(
                PlanVerificationIssue(
                    code="FILE_NOT_IN_CONTEXT",
                    message=(
                        f"Citation [{idx}] cites file '{citation.file_path}' which was not retrieved or "
                        "ranked in verified repository context."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                )
            )
            continue

        ctx_file = context_files[citation.file_path]

        # D. Content SHA-256 Verification
        if citation.file_sha256 != ctx_file.sha256 and citation.file_sha256 != ctx_file.content_hash:
            issues.append(
                PlanVerificationIssue(
                    code="FILE_HASH_MISMATCH",
                    message=(
                        f"Citation [{idx}] file_sha256 '{citation.file_sha256}' does not match "
                        f"the verified context hash '{ctx_file.sha256}' for '{citation.file_path}'."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                    details={"citation_hash": citation.file_sha256, "context_hash": ctx_file.sha256},
                )
            )
            continue

        # E. Line Span In-Bounds Check
        file_lines = ctx_file.content.splitlines()
        total_lines = len(file_lines)

        if total_lines == 0:
            if citation.start_line != 1 or citation.end_line != 1:
                issues.append(
                    PlanVerificationIssue(
                        code="OUT_OF_BOUNDS_LINE_SPAN",
                        message=(
                            f"Citation [{idx}] line span {citation.start_line}..{citation.end_line} is invalid "
                            f"for empty file '{citation.file_path}' (0 lines)."
                        ),
                        citation_index=idx,
                        file_path=citation.file_path,
                    )
                )
                continue
        elif citation.start_line < 1 or citation.end_line > total_lines:
            issues.append(
                PlanVerificationIssue(
                    code="OUT_OF_BOUNDS_LINE_SPAN",
                    message=(
                        f"Citation [{idx}] line span {citation.start_line}..{citation.end_line} is out of bounds "
                        f"for '{citation.file_path}' (valid range: 1..{total_lines})."
                    ),
                    citation_index=idx,
                    file_path=citation.file_path,
                    details={"start_line": citation.start_line, "end_line": citation.end_line, "total_lines": total_lines},
                )
            )
            continue

        # F. Supporting Excerpt Integrity Check
        if citation.excerpt and citation.excerpt.strip():
            actual_span_lines = file_lines[citation.start_line - 1 : citation.end_line]
            actual_span_text = "\n".join(actual_span_lines)

            # Whitespace-insensitive token comparison
            norm_quoted = " ".join(citation.excerpt.strip().split())
            norm_actual = " ".join(actual_span_text.strip().split())

            if norm_quoted not in norm_actual and norm_actual not in norm_quoted:
                issues.append(
                    PlanVerificationIssue(
                        code="EXCERPT_MISMATCH",
                        message=(
                            f"Citation [{idx}] excerpt does not match actual content in '{citation.file_path}' "
                            f"at lines {citation.start_line}..{citation.end_line}."
                        ),
                        citation_index=idx,
                        file_path=citation.file_path,
                        details={"quoted": citation.excerpt[:80], "actual": actual_span_text[:80]},
                    )
                )
                continue

        # G. Truncation Warning
        if ctx_file.is_truncated:
            warnings.append(
                f"Citation [{idx}] in '{citation.file_path}' is derived from a truncated file and may be partial evidence."
            )

        verified_count += 1

    # 2. Verify Target Files Grounding
    all_target_files = set(plan.target_files)
    for step in plan.steps:
        all_target_files.update(step.target_files)

    for tf in all_target_files:
        if not is_safe_relative_path(tf):
            issues.append(
                PlanVerificationIssue(
                    code="UNSAFE_TARGET_FILE",
                    message=f"Target file '{tf}' fails path safety validation.",
                    file_path=tf,
                )
            )
            continue

        if tf not in context_files:
            # Check if acknowledged in assumptions, uncertainties, or explicitly marked new file
            acknowledged = (
                any(tf in a for a in plan.assumptions)
                or any(tf in u for u in plan.uncertainties)
                or any("create" in s.description.lower() or "add" in s.description.lower() for s in plan.steps if tf in s.target_files)
            )
            if not acknowledged:
                issues.append(
                    PlanVerificationIssue(
                        code="UNGROUNDED_TARGET_FILE",
                        message=(
                            f"Target file '{tf}' was not retrieved in repository context and is not documented "
                            "as a newly created file in assumptions or uncertainties."
                        ),
                        file_path=tf,
                    )
                )

    is_valid = len(issues) == 0
    error_summary = None
    if not is_valid:
        error_summary = "; ".join(i.message for i in issues[:3])
        if len(issues) > 3:
            error_summary += f" (and {len(issues) - 3} more issues)"

    return PlanVerificationResult(
        is_valid=is_valid,
        verified_citations_count=verified_count,
        issues=issues,
        warnings=warnings,
        error_summary=error_summary,
    )


def is_plan_invalidated_by_context(
    plan: StructuredPlan,
    repo_context: RepositoryContext,
) -> bool:
    """
    Check whether changes to the repository context snapshot invalidate an existing verified plan.
    Returns True if any verified citation now points to a mismatched commit or modified file hash.
    """
    if not plan.is_verified or not plan.evidence_citations:
        return False

    context_files = {f.path: f for f in repo_context.selected_files}

    for citation in plan.evidence_citations:
        if citation.base_commit_sha != repo_context.base_commit_sha:
            return True
        if citation.file_path not in context_files:
            return True
        ctx_file = context_files[citation.file_path]
        if citation.file_sha256 != ctx_file.sha256:
            return True

    return False
