"""ReviewerAgent: Performs independent, multi-dimensional code reviews on proposed patches."""

import logging
from typing import Dict, List, Optional

from app.schemas.patch import PatchItem
from app.schemas.plan import StructuredPlan
from app.schemas.review import ReviewFinding, ReviewResponse
from app.schemas.test_result import TestResult
from app.services.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger("devsquad.reviewer")

REVIEWER_SYSTEM_PROMPT = """You are the Lead Application Security Architect and Independent Code Reviewer for DevSquad.

Your task is to independently critique a proposed code patch against the original issue, structured plan, and validation results.

Evaluation Dimensions:
1. Correctness: Does the diff genuinely fix the issue described?
2. Acceptance Criteria: Does it satisfy every criterion in the plan?
3. Security: Check for injection, path traversal, authentication bypass, secret exposure, or unsafe operations.
4. Regressions & Edge Cases: Identify any scenarios where existing functionality could break.
5. Scope Expansion: Flag any extraneous, unrequested refactoring or scope creep.
6. Test Evidence: Consider the sandbox test or AST validation results. If sandbox was unavailable, note unverified runtime behavior.

Severity Levels:
- CRITICAL: Immediate security vulnerability or severe data corruption/loss.
- HIGH: Functional breakage, unhandled edge cases causing crash, major spec violation.
- MEDIUM: Subtle bug, partial spec omission, performance degradation.
- LOW: Minor stylistic deviation, missing comment, sub-optimal naming.
- INFO: Informational observation or suggested future enhancement.

Recommendation Rules:
- 'approve': No CRITICAL or HIGH findings, acceptance criteria met.
- 'request_changes': Repairable issues found (HIGH or MEDIUM findings).
- 'reject': Fundamentally flawed approach or CRITICAL vulnerabilities requiring a new strategy.

Remember: Your recommendation is purely advisory for the human maintainer. You cannot authorize pull requests or production deployments.
"""


class ReviewerAgent:
    """Asynchronous agent that performs independent multi-perspective code reviews."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def review(
        self,
        issue_title: str,
        issue_body: str,
        plan: StructuredPlan,
        patch: PatchItem,
        test_result: TestResult,
        source_files: Dict[str, str],
        constraints: Optional[List[str]] = None,
    ) -> ReviewResponse:
        """Conduct independent code review and return structured findings and recommendation."""
        logger.info(
            f"ReviewerAgent evaluating patch revision {patch.revision} (hash: {patch.content_hash[:8]})"
        )

        user_prompt_parts = [
            "# ORIGINAL ISSUE",
            f"**Title**: {issue_title}",
            f"**Description**:\n<UNTRUSTED_ISSUE>\n{issue_body}\n</UNTRUSTED_ISSUE>",
            "\n# STRUCTURED PLAN OBJECTIVE & CRITERIA",
            f"**Objective**: {plan.objective}",
            "**Acceptance Criteria**:",
        ]
        for ac in plan.acceptance_criteria:
            user_prompt_parts.append(f"- {ac}")

        user_prompt_parts.extend([
            "\n# PROPOSED CODE PATCH",
            f"**Revision**: {patch.revision}",
            f"**Summary**: {patch.summary}",
            f"**Target Files**: {', '.join(patch.target_files)}",
            f"**Diff**:\n```diff\n{patch.unified_diff}\n```",
            "\n# VALIDATION / TEST RESULTS",
            f"**Status**: {test_result.status}",
            f"**Environment**: {test_result.environment}",
            f"**Exit Code**: {test_result.exit_code}",
            f"**Passed**: {test_result.passed}, **Failed**: {test_result.failed}",
            f"**Stdout Summary**: {test_result.stdout[:500]}",
            f"**Stderr Summary**: {test_result.stderr[:500]}",
            f"**Limitations**: {', '.join(test_result.security_limitations)}",
        ])

        if constraints:
            user_prompt_parts.append("\n# CONSTRAINTS:")
            for c in constraints:
                user_prompt_parts.append(f"- {c}")

        user_prompt = "\n".join(user_prompt_parts)

        # Generate structured review
        response: LLMResponse[ReviewResponse] = await self.llm_provider.generate_structured(
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ReviewResponse,
            temperature=0.0,
        )

        review_res: ReviewResponse = response.data

        # Enforce consistency: if test_result was PARTIAL_VALIDATION or SANDBOX_UNAVAILABLE,
        # ensure runtime unverified limitation is logged in unresolved_risks
        if "PARTIAL" in test_result.status or "UNAVAILABLE" in test_result.status:
            sandbox_note = "Full dynamic test suite was not executed (Docker sandbox was unavailable); runtime edge cases remain unverified."
            if sandbox_note not in review_res.unresolved_risks:
                review_res.unresolved_risks.append(sandbox_note)

        # Enforce consistency: if any finding is CRITICAL, recommendation cannot be "approve"
        has_critical = any(f.severity == "CRITICAL" for f in review_res.findings)
        has_high = any(f.severity == "HIGH" for f in review_res.findings)
        if (has_critical or has_high) and review_res.recommendation == "approve":
            logger.warning("Overriding review recommendation from 'approve' to 'request_changes' due to high-severity findings.")
            review_res.recommendation = "request_changes"

        logger.info(
            f"ReviewerAgent review completed for rev {patch.revision}: recommendation='{review_res.recommendation}', "
            f"{len(review_res.findings)} findings. Latency: {response.usage.latency_ms}ms"
        )
        return review_res
