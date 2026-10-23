"""LangGraph StateGraph assembly and compilation for DevSquad multi-agent workflow."""

import logging
from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes import (
    coder_node,
    context_preparation_node,
    finalization_node,
    planner_node,
    reviewer_node,
    sandbox_tester_node,
    security_guardian_node,
    validate_input_node,
)
from app.orchestration.routing import (
    route_after_coder,
    route_after_context,
    route_after_planner,
    route_after_reviewer,
    route_after_security,
    route_after_tester,
    route_after_validation,
)
from app.orchestration.state import DevSquadState

logger = logging.getLogger("devsquad.graph")


def build_devsquad_graph() -> StateGraph:
    """Construct the DevSquad StateGraph with all agent nodes and conditional routing."""
    builder = StateGraph(DevSquadState)

    # Register workflow nodes
    builder.add_node("validate_input_node", validate_input_node)
    builder.add_node("context_preparation_node", context_preparation_node)
    builder.add_node("planner_node", planner_node)
    builder.add_node("coder_node", coder_node)
    builder.add_node("security_guardian_node", security_guardian_node)
    builder.add_node("sandbox_tester_node", sandbox_tester_node)
    builder.add_node("reviewer_node", reviewer_node)
    builder.add_node("finalization_node", finalization_node)

    # Flow sequence
    builder.add_edge(START, "validate_input_node")
    builder.add_conditional_edges("validate_input_node", route_after_validation)
    builder.add_conditional_edges("context_preparation_node", route_after_context)
    builder.add_conditional_edges("planner_node", route_after_planner)
    builder.add_conditional_edges("coder_node", route_after_coder)
    builder.add_conditional_edges("security_guardian_node", route_after_security)
    builder.add_conditional_edges("sandbox_tester_node", route_after_tester)
    builder.add_conditional_edges("reviewer_node", route_after_reviewer)
    builder.add_edge("finalization_node", END)

    return builder


def compile_devsquad_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """Compile the state graph with the given persistent or in-memory checkpointer."""
    builder = build_devsquad_graph()
    return builder.compile(checkpointer=checkpointer)
