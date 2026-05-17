"""
Planner Agent — AI-powered test plan generation using LangGraph.

Replaces AutonomousTestPlanner. Generates structured test plans from natural
language goals using a LangGraph react agent.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.agent_tools.test_tools import save_test_plan
from app.core.agent_config import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert test automation planner. Given a test goal and
target URL, generate a detailed, executable test plan.

Requirements:
1. Generate 3-8 specific, actionable test steps
2. Each step must be clear enough for browser automation (e.g., "Click the 'Login' button")
3. Include verification criteria for each step
4. Consider potential failures and edge cases

You MUST output your plan as a JSON block in this exact format:
```json
{
  "plan_id": "<unique-id>",
  "steps": [
    {
      "step_number": 1,
      "description": "Navigate to login page",
      "type": "navigation",
      "verification": "Page title contains 'Login'",
      "confidence": 0.95,
      "fallback_strategies": ["wait_for_page_load"]
    }
  ],
  "estimated_duration": 120,
  "risk_factors": ["dynamic_content"],
  "success_criteria": ["user_logged_in"]
}
```

Always include the JSON block in your response."""


def _parse_plan_from_output(text: str, plan_id: str) -> Dict[str, Any]:
    """Extract structured plan from agent output."""
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            plan_data = json.loads(text[start:end].strip())
            plan_data["plan_id"] = plan_id
            plan_data.setdefault("steps", [])
            plan_data.setdefault("estimated_duration", 120)
            plan_data.setdefault("risk_factors", [])
            plan_data.setdefault("success_criteria", [])
            for step in plan_data["steps"]:
                step.setdefault("confidence", 0.8)
                step.setdefault("fallback_strategies", [])
            return plan_data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse plan JSON: %s", e)

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        plan_data = json.loads(text[start:end])
        plan_data["plan_id"] = plan_id
        return plan_data
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "plan_id": plan_id,
        "steps": [
            {"step_number": 1, "description": "Navigate to target URL", "type": "navigation", "confidence": 0.9},
            {"step_number": 2, "description": "Verify page loads correctly", "type": "verification", "confidence": 0.8},
        ],
        "estimated_duration": 60,
        "risk_factors": ["ai_parse_failure"],
        "success_criteria": ["test_completed"],
        "fallback_generated": True,
    }


async def generate_test_plan(
    goal: str,
    url: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a structured test plan from a natural language goal.

    Same interface as AutonomousTestPlanner.generate_test_plan().

    Args:
        goal: Natural language test goal/requirement
        url: Target URL for testing
        context: Additional context (environment variables, etc.)

    Returns:
        Dict with plan_id, steps[], estimated_duration, risk_factors, success_criteria
    """
    context = context or {}
    plan_id = str(uuid.uuid4())

    llm = get_llm(temperature=0.3, max_tokens=4096)
    agent = create_react_agent(llm, tools=[save_test_plan])

    prompt = f"""Generate a test plan for the following requirement:

**Goal:** {goal}
**Target URL:** {url}
**Context:** {json.dumps(context, indent=2) if context else 'None'}

Output the plan as JSON."""

    logger.info("Planner agent: generating plan for goal: %s", goal[:100])

    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        },
        config={"configurable": {"thread_id": f"plan-{plan_id}"}},
    )

    messages = result.get("messages", [])
    final_text = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            final_text = msg.content
            break

    plan = _parse_plan_from_output(final_text, plan_id)

    logger.info(
        "Planner agent: generated plan %s with %d steps",
        plan_id,
        len(plan.get("steps", [])),
    )

    return plan
