"""
Reviewer Agent — AI-powered test result summarization using LangGraph.

Analyzes test execution results and generates quality reports with
failure analysis, root cause identification, and improvement recommendations.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.agent_tools.test_tools import get_test_results
from app.core.agent_config import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a test results reviewer. Analyze test execution results
and generate a comprehensive summary report.

Your review should include:
1. **Summary**: Overall pass/fail status with statistics
2. **Failure Analysis**: For each failed step, identify likely root cause
3. **Patterns**: Any recurring issues across steps
4. **Recommendations**: Specific improvements to prevent future failures
5. **Quality Score**: Rate the test execution quality (0-100)

Output your review as a JSON block:
```json
{
  "summary": {
    "total_steps": 5,
    "passed": 3,
    "failed": 2,
    "pass_rate": 0.6,
    "quality_score": 65
  },
  "failure_analysis": [
    {"step_number": 3, "root_cause": "...", "severity": "high"}
  ],
  "patterns": ["..."],
  "recommendations": ["..."],
  "overall_assessment": "..."
}
```
"""


def _parse_review_from_output(text: str) -> Dict[str, Any]:
    """Extract structured review from agent output."""
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return json.loads(text[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "summary": {"quality_score": 0},
        "overall_assessment": text[:1000],
        "parse_error": True,
    }


async def review_test_results(
    run_id: str,
    test_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Analyze test execution results and generate a summary report.

    Args:
        run_id: Test run ID to review
        test_results: Optional pre-loaded results. If None, agent fetches via tool.

    Returns:
        Dict with summary, failure_analysis, patterns, recommendations
    """
    llm = get_llm(temperature=0.2, max_tokens=4096)
    agent = create_react_agent(llm, tools=[get_test_results])

    if test_results:
        results_text = json.dumps(test_results, indent=2, ensure_ascii=False)
        prompt = f"""Review the following test execution results for run {run_id}:

{results_text}

Generate a comprehensive test review report."""
    else:
        prompt = f"""Review the test execution results for run {run_id}.
Use the get_test_results tool to fetch the data, then generate a comprehensive review report."""

    logger.info("Reviewer agent: reviewing run %s", run_id)

    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        },
        config={"configurable": {"thread_id": f"review-{uuid4()}"}},
    )

    messages = result.get("messages", [])
    final_text = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            final_text = msg.content
            break

    review = _parse_review_from_output(final_text)
    review["run_id"] = run_id

    logger.info(
        "Reviewer agent: completed review for run %s, quality_score=%s",
        run_id,
        review.get("summary", {}).get("quality_score", "N/A"),
    )

    return review
