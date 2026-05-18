"""
Supervisor State — shared state schema for the LangGraph supervisor graph.

Defines the TypedDict that flows through all graph nodes, carrying test
planning, execution, and review data between the planner, executor, and
reviewer sub-agents.
"""

import operator
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import AnyMessage
from typing import TypedDict


class SupervisorState(TypedDict):
    """Shared state flowing through the supervisor graph."""

    # --- Input fields ---
    mode: str  # "full_pipeline" | "execute_only" | "plan_and_execute"
    goal: Optional[str]  # Natural language test goal (for planning)
    target_url: Optional[str]  # Target URL (for planning)
    test_definition_id: Optional[int]  # Test definition ID
    run_id: str  # Test run identifier
    environment: Dict[str, Any]  # Environment variables

    # --- Planning output ---
    plan: Optional[Dict[str, Any]]  # Generated test plan with steps[]
    plan_error: Optional[str]  # Planning failure message

    # --- Execution output ---
    test_steps: Optional[List[Dict[str, Any]]]  # Steps fed to executor
    step_results: Optional[List[Dict[str, Any]]]  # Raw executor output
    execution_error: Optional[str]  # Execution failure message

    # --- Review output ---
    review: Optional[Dict[str, Any]]  # Reviewer report
    review_error: Optional[str]  # Review failure message

    # --- Final result ---
    final_result: Optional[Dict[str, Any]]  # Aggregated result for DB storage

    # --- Error/retry control ---
    retry_count: int  # Number of retries attempted
    max_retries: int  # Maximum retries allowed (default: 1)
    current_phase: Optional[str]  # "planning" | "executing" | "reviewing" | "done" | "error"
    failed_phase: Optional[str]  # Node name to retry: "planner_node" | "executor_node"

    # --- LangGraph message history ---
    messages: Annotated[List[AnyMessage], operator.add]
