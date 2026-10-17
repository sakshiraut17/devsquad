"""Seed script to populate devsquad.db with realistic preview data for frontend inspection."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.security import compute_sha256
from app.db.models.agent_log import AgentLog
from app.db.models.approval_record import ApprovalRecord
from app.db.models.issue import Issue
from app.db.models.patch import Patch
from app.db.models.repository import Repository
from app.db.models.run import Run, RunStatus
from app.db.models.user import User
from app.db.session import async_session_factory


SAMPLE_DIFF = """diff --git a/inventory.py b/inventory.py
--- a/inventory.py
+++ b/inventory.py
@@ -5,3 +5,3 @@
 def calculate_discounted_price(unit_price: float, quantity: int) -> float:
-    if quantity > 10:
+    if quantity >= 10:
         return unit_price * quantity * 0.90
"""


async def seed_data():
    """Populate database with sample maintainer, repositories, issues, and runs."""
    async with async_session_factory() as session:
        # 1. Maintainer User
        result = await session.execute(
            select(User).where(User.email == "maintainer@devsquad.ai")
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="maintainer@devsquad.ai",
                display_name="DevSquad Principal Maintainer",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"Created maintainer user: {user.email} (ID: {user.id})")

        # 2. Repository 1: devsquad/store-service
        repo1_res = await session.execute(
            select(Repository).where(Repository.full_name == "devsquad/store-service")
        )
        repo1 = repo1_res.scalar_one_or_none()
        if not repo1:
            repo1 = Repository(
                owner_id=user.id,
                github_repository_id=10101,
                full_name="devsquad/store-service",
                default_branch="main",
                description="Core e-commerce store service and inventory calculation engine.",
                is_active=True,
            )
            session.add(repo1)
            await session.flush()
            print(f"Created repository: {repo1.full_name}")

        # 3. Repository 2: devsquad/auth-service
        repo2_res = await session.execute(
            select(Repository).where(Repository.full_name == "devsquad/auth-service")
        )
        repo2 = repo2_res.scalar_one_or_none()
        if not repo2:
            repo2 = Repository(
                owner_id=user.id,
                github_repository_id=10102,
                full_name="devsquad/auth-service",
                default_branch="main",
                description="OAuth2 and session token service with HMAC-SHA256 signatures.",
                is_active=True,
            )
            session.add(repo2)
            await session.flush()
            print(f"Created repository: {repo2.full_name}")

        # 4. Issues for repo1
        i1_res = await session.execute(
            select(Issue).where(
                Issue.repository_id == repo1.id,
                Issue.github_issue_number == 14,
            )
        )
        issue1 = i1_res.scalar_one_or_none()
        if not issue1:
            issue1 = Issue(
                repository_id=repo1.id,
                github_issue_number=14,
                title="Bulk discount threshold applies strictly at 10 items",
                body="Specification requires 10% discount for orders >= 10 items. Current code checks quantity > 10, incorrectly denying discount on exact 10 items.",
                state="open",
                labels=["bug", "pricing", "high-priority"],
                html_url="https://github.com/devsquad/store-service/issues/14",
            )
            session.add(issue1)
            await session.flush()
            print(f"Created issue #{issue1.github_issue_number}: {issue1.title}")

        i2_res = await session.execute(
            select(Issue).where(
                Issue.repository_id == repo1.id,
                Issue.github_issue_number == 19,
            )
        )
        issue2 = i2_res.scalar_one_or_none()
        if not issue2:
            issue2 = Issue(
                repository_id=repo1.id,
                github_issue_number=19,
                title="Inventory stock count underflows when concurrent checkouts happen",
                body="Race condition in stock decrements causes negative inventory balance during flash sales.",
                state="open",
                labels=["concurrency", "critical"],
                html_url="https://github.com/devsquad/store-service/issues/19",
            )
            session.add(issue2)
            await session.flush()
            print(f"Created issue #{issue2.github_issue_number}: {issue2.title}")

        # 5. Run 1: Awaiting Human Approval (Scenario A verification)
        r1_res = await session.execute(
            select(Run).where(
                Run.repository_id == repo1.id,
                Run.issue_id == issue1.id,
                Run.status == RunStatus.AWAITING_APPROVAL.value,
            )
        )
        run1 = r1_res.scalar_one_or_none()
        if not run1:
            run1 = Run(
                repository_id=repo1.id,
                issue_id=issue1.id,
                status=RunStatus.AWAITING_APPROVAL.value,
                current_node="awaiting_approval",
                retry_count=0,
                started_at=datetime.now(timezone.utc),
            )
            session.add(run1)
            await session.flush()

            # Patch for Run 1
            patch_hash = compute_sha256(SAMPLE_DIFF)
            patch1 = Patch(
                run_id=run1.id,
                revision=1,
                unified_diff=SAMPLE_DIFF,
                target_files=["inventory.py"],
                summary="Fix bulk discount off-by-one boundary condition (>= 10).",
                content_hash=patch_hash,
                validation_status="passed",
            )
            session.add(patch1)
            await session.flush()

            # Agent logs for Run 1
            logs = [
                AgentLog(
                    run_id=run1.id,
                    agent_name="context_ranker",
                    event_type="context_ranked",
                    message="Ranked 3 files within 12,000 token budget. Top relevance: inventory.py (0.94)",
                    duration_ms=45,
                ),
                AgentLog(
                    run_id=run1.id,
                    agent_name="planner",
                    event_type="plan_generated",
                    message="StructuredPlan generated with 3 verification criteria and target file inventory.py.",
                    duration_ms=120,
                ),
                AgentLog(
                    run_id=run1.id,
                    agent_name="coder",
                    event_type="patch_synthesized",
                    message="Synthesized unified diff modifying comparison operator to '>='.",
                    duration_ms=210,
                ),
                AgentLog(
                    run_id=run1.id,
                    agent_name="tester",
                    event_type="tests_passed",
                    message="Subprocess execution: pytest tests/test_inventory.py returned dynamic Exit Code 0 (3 passed in 0.06s).",
                    duration_ms=640,
                ),
                AgentLog(
                    run_id=run1.id,
                    agent_name="reviewer",
                    event_type="patch_approved",
                    message="Reviewer recommendation: APPROVE. Zero critical findings, patch is minimal and safe.",
                    duration_ms=88,
                ),
            ]
            session.add_all(logs)
            print(f"Created Awaiting Approval Run: {run1.id} with Patch: {patch1.id}")

        # 6. Run 2: Failed Run with Bounded Repairs (Scenario B verification)
        r2_res = await session.execute(
            select(Run).where(
                Run.repository_id == repo1.id,
                Run.issue_id == issue2.id,
                Run.status == RunStatus.FAILED.value,
            )
        )
        run2 = r2_res.scalar_one_or_none()
        if not run2:
            run2 = Run(
                repository_id=repo1.id,
                issue_id=issue2.id,
                status=RunStatus.FAILED.value,
                current_node="end",
                retry_count=3,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                error_summary="Maximum repair attempts (3) exceeded without passing test suite.",
            )
            session.add(run2)
            await session.flush()

            # Failed Patch
            flawed_diff = """diff --git a/stock.py b/stock.py
--- a/stock.py
+++ b/stock.py
@@ -1,3 +1,3 @@
-def lock_stock():
+def lock_stock_v2():
     pass
"""
            patch2 = Patch(
                run_id=run2.id,
                revision=3,
                unified_diff=flawed_diff,
                target_files=["stock.py"],
                summary="Attempted atomic lock patch that failed concurrency stress test.",
                content_hash=compute_sha256(flawed_diff),
                validation_status="failed",
            )
            session.add(patch2)

            logs2 = [
                AgentLog(
                    run_id=run2.id,
                    agent_name="tester",
                    event_type="tests_failed",
                    message="Execution returned Exit Code 1: AssertionError: assert 95 == 100",
                    duration_ms=750,
                ),
                AgentLog(
                    run_id=run2.id,
                    agent_name="repair_gatekeeper",
                    event_type="repair_exhausted",
                    message="Repair attempts exceeded maximum allowed bound (3). Terminating workflow fail-closed.",
                    duration_ms=12,
                ),
            ]
            session.add_all(logs2)
            print(f"Created Failed Run: {run2.id}")

        await session.commit()
        print("Preview data successfully seeded into database.")


if __name__ == "__main__":
    asyncio.run(seed_data())
