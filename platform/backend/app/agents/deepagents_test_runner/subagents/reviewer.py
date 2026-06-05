"""
Reviewer Sub-Agent — AI-powered test result analysis using Deep Agents.

Analyzes test execution results and generates comprehensive quality reports
with failure analysis, root cause identification, and improvement recommendations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# Load system prompt
def _load_system_prompt() -> str:
    """Load the reviewer system prompt from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "reviewer_system.md"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Failed to load reviewer prompt: %s", e)
        return "You are a test results reviewer. Analyze test results and generate quality reports."


# Tools for the reviewer sub-agent

@tool
def get_test_results(run_id: str) -> Dict[str, Any]:
    """Fetch test execution results for a specific run.

    Args:
        run_id: The test run ID to fetch results for

    Returns:
        Dict containing test results with step details
    """
    # In the Deep Agents architecture, results are read from the filesystem
    results_path = Path(f"/tmp/test_runs/{run_id}/test_results.json")
    try:
        if results_path.exists():
            with open(results_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": f"No results found for run {run_id}"}
    except Exception as e:
        logger.error("Failed to read test results: %s", e)
        return {"error": str(e)}


@tool
def write_report(report: str, run_id: str) -> str:
    """Write the review report to the filesystem.

    Args:
        report: The JSON report content to write
        run_id: The test run ID for the report

    Returns:
        Confirmation message with file path
    """
    report_path = Path(f"/tmp/test_runs/{run_id}/review_report.json")
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Review report written to %s", report_path)
        return f"Report written to {report_path}"
    except Exception as e:
        logger.error("Failed to write report: %s", e)
        return f"Failed to write report: {e}"


# Create the reviewer sub-agent configuration
def create_reviewer_subagent() -> Dict[str, Any]:
    """Create the reviewer sub-agent configuration for Deep Agents.

    Returns:
        Dict with sub-agent configuration
    """
    return {
        "name": "reviewer",
        "description": "Review and analyze test execution results. Use this agent to generate quality reports with failure analysis and recommendations.",
        "system_prompt": _load_system_prompt(),
        "tools": [get_test_results, write_report],
    }


# Standalone invocation function for testing
async def review_test_results(run_id: str) -> Dict[str, Any]:
    """Review test results for a specific run (standalone function).

    This function can be used independently without the full Deep Agents orchestration.
    It reads results from the filesystem and generates a review report.

    Args:
        run_id: Test run ID to review

    Returns:
        Dict with review data including summary, failure_analysis, patterns, recommendations
    """
    from deepagents import create_deep_agent

    # Read existing results
    results = get_test_results.invoke({"run_id": run_id})
    if "error" in results:
        return {
            "run_id": run_id,
            "error": results["error"],
            "summary": {"quality_score": 0, "total_steps": 0},
        }

    # Create a minimal agent for this specific review task
    from app.core.agent_config import get_llm
    model = get_llm(temperature=0.2, max_tokens=4096)
    agent = create_deep_agent(
        model=model,
        tools=[get_test_results, write_report],
        system_prompt=_load_system_prompt(),
        backend=None,  # No filesystem backend needed for standalone
    )

    # Invoke the agent
    prompt = f"""Review the test execution results for run {run_id}.

Current results:
{json.dumps(results, indent=2, ensure_ascii=False)}

Generate a comprehensive review report and write it using the write_report tool."""

    try:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        # Parse the report from the result
        report_path = f"/tmp/test_runs/{run_id}/review_report.json"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                review = json.load(f)
            review["run_id"] = run_id
            return review
        except Exception:
            return {
                "run_id": run_id,
                "error": "Failed to parse generated report",
                "summary": {"quality_score": 0},
            }
    except Exception as e:
        logger.error("Reviewer agent failed: %s", e)
        return {
            "run_id": run_id,
            "error": str(e),
            "summary": {"quality_score": 0},
        }
