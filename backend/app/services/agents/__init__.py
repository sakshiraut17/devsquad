"""DevSquad Multi-Agent Services Package."""

from app.services.agents.planner import PlannerAgent
from app.services.agents.coder import CoderAgent, PatchGenerationResponse
from app.services.agents.tester import SandboxTesterAgent
from app.services.agents.reviewer import ReviewerAgent
from app.services.agents.diff_utils import (
    PatchError,
    PatchHunkMismatchError,
    apply_unified_diff,
    parse_unified_diff_files,
    split_multi_file_unified_diff,
    validate_unified_diff_safety,
)
from app.services.agents.repair import (
    RepairCycleState,
    RevisionRecord,
    log_agent_event,
    record_patch_revision,
)

__all__ = [
    "PlannerAgent",
    "CoderAgent",
    "PatchGenerationResponse",
    "SandboxTesterAgent",
    "ReviewerAgent",
    "PatchError",
    "PatchHunkMismatchError",
    "apply_unified_diff",
    "parse_unified_diff_files",
    "split_multi_file_unified_diff",
    "validate_unified_diff_safety",
    "RepairCycleState",
    "RevisionRecord",
    "log_agent_event",
    "record_patch_revision",
]
