"""DevSquad LangGraph Orchestration Layer Package."""

from app.orchestration.state import (
    DevSquadState,
    WorkflowStage,
    WorkflowStatus,
    create_initial_state,
)
from app.orchestration.graph import (
    build_devsquad_graph,
    compile_devsquad_graph,
)
from app.orchestration.nodes import (
    NodeDependencies,
    get_default_deps,
    set_default_deps,
)
from app.orchestration.routing import (
    route_after_coder,
    route_after_context,
    route_after_planner,
    route_after_reviewer,
    route_after_tester,
    route_after_validation,
)
from app.orchestration.checkpointer import (
    DEFAULT_CHECKPOINT_DB_PATH,
    get_async_checkpointer,
)
from app.orchestration.service import (
    DevSquadOrchestrator,
)
from app.orchestration.exceptions import (
    CheckpointError,
    OrchestrationError,
    RunNotResumableError,
    StateTransitionError,
    UnauthorizedRunAccessError,
)

_global_orchestrator = DevSquadOrchestrator()


def get_orchestrator() -> DevSquadOrchestrator:
    """Return the global orchestrator service instance."""
    return _global_orchestrator


__all__ = [
    "DevSquadState",
    "WorkflowStage",
    "WorkflowStatus",
    "create_initial_state",
    "build_devsquad_graph",
    "compile_devsquad_graph",
    "NodeDependencies",
    "get_default_deps",
    "set_default_deps",
    "route_after_coder",
    "route_after_context",
    "route_after_planner",
    "route_after_reviewer",
    "route_after_tester",
    "route_after_validation",
    "DEFAULT_CHECKPOINT_DB_PATH",
    "get_async_checkpointer",
    "DevSquadOrchestrator",
    "get_orchestrator",
    "CheckpointError",
    "OrchestrationError",
    "RunNotResumableError",
    "StateTransitionError",
    "UnauthorizedRunAccessError",
]
