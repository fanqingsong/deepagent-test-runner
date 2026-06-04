"""
Supervisor Graph — LangGraph StateGraph for orchestrating test sub-agents.

Builds a compiled graph with conditional routing that chains planner,
executor, and reviewer nodes based on the execution mode.
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.test_runner.supervisor_state import SupervisorState
from app.agents.test_runner.nodes import (
    error_handler_node,
    executor_node,
    page_fetcher_node,
    planner_node,
    result_builder_node,
    reviewer_node,
    script_executor_node,
    script_generator_node,
)

logger = logging.getLogger(__name__)


# --- Routing functions ---


def route_from_start(state: SupervisorState) -> str:
    """Determine first node based on mode."""
    execution_mode = state.get("execution_mode", "nl_steps")
    if execution_mode == "script":
        if state.get("playwright_script") and state.get("script_status") == "validated":
            return "script_executor_node"
        return "page_fetcher_node"
    mode = state.get("mode", "execute_only")
    if mode == "full_pipeline" and state.get("goal"):
        return "planner_node"
    return "executor_node"


def route_after_planner(state: SupervisorState) -> str:
    """Route after planner completes — on error always go to error_handler."""
    if state.get("plan_error"):
        return "error_handler_node"
    return "executor_node"


def route_after_executor(state: SupervisorState) -> str:
    """Route after executor completes — on error always go to error_handler."""
    if state.get("execution_error"):
        return "error_handler_node"
    mode = state.get("mode", "execute_only")
    if mode == "plan_and_execute":
        return "result_builder_node"
    return "reviewer_node"


def route_after_reviewer(state: SupervisorState) -> Literal["result_builder_node"]:
    """Route after reviewer — always go to result builder (reviewer failure is non-fatal)."""
    return "result_builder_node"


def route_after_error(state: SupervisorState) -> str:
    """Route after error handler — retry failed phase or go to result builder."""
    failed_phase = state.get("failed_phase")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    if retry_count <= max_retries and failed_phase:
        return failed_phase
    return "result_builder_node"


def route_after_script_executor(state: SupervisorState) -> str:
    """Route after script executor — retry generation or build result."""
    script_status = state.get("script_status", "failed")
    if script_status == "validated":
        return "result_builder_node"
    attempt = state.get("script_attempt", 0)
    max_attempts = state.get("max_script_attempts", 3)
    if attempt < max_attempts:
        return "script_generator_node"
    return "result_builder_node"


def route_after_page_fetcher(state: SupervisorState) -> str:
    """Route after page fetcher — proceed to generation or fail."""
    if state.get("script_status") == "failed":
        return "result_builder_node"
    return "script_generator_node"


def route_after_script_generator(state: SupervisorState) -> str:
    """Route after script generator — execute or fail."""
    if state.get("script_status") == "failed":
        return "result_builder_node"
    return "script_executor_node"


# --- Graph builder ---


def build_pipeline_graph() -> StateGraph:
    """Build and compile the supervisor pipeline graph.

    Topology:
        START -> router -> [planner_node]? -> executor_node -> [reviewer_node]? -> result_builder_node -> END
                                    |                    |                        |
                                    +-> error_handler    +-> error_handler       (non-fatal)
                                                              |
                                                        result_builder_node -> END
    """
    graph = StateGraph(SupervisorState)

    # Add nodes — existing NL pipeline
    graph.add_node("planner_node", planner_node)
    graph.add_node("executor_node", executor_node)
    graph.add_node("reviewer_node", reviewer_node)
    graph.add_node("error_handler_node", error_handler_node)
    graph.add_node("result_builder_node", result_builder_node)

    # Add nodes — script generation pipeline
    graph.add_node("page_fetcher_node", page_fetcher_node)
    graph.add_node("script_generator_node", script_generator_node)
    graph.add_node("script_executor_node", script_executor_node)

    # Entry: route based on mode
    graph.add_conditional_edges(START, route_from_start)

    # NL pipeline edges (unchanged)
    graph.add_conditional_edges("planner_node", route_after_planner)
    graph.add_conditional_edges("executor_node", route_after_executor)
    graph.add_conditional_edges("reviewer_node", route_after_reviewer)
    graph.add_conditional_edges("error_handler_node", route_after_error)

    # Script generation pipeline edges
    graph.add_conditional_edges("page_fetcher_node", route_after_page_fetcher)
    graph.add_conditional_edges("script_generator_node", route_after_script_generator)
    graph.add_conditional_edges("script_executor_node", route_after_script_executor)

    # Result builder is terminal
    graph.add_edge("result_builder_node", END)

    compiled = graph.compile()
    logger.info("Supervisor pipeline graph compiled successfully")
    return compiled
