"""
Autonomous Test Planning Service

AI-powered test planning and adaptive execution decision-making.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import TestDefinition, TestStep


class AutonomousTestPlanner:
    """
    AI-powered test planning and adaptive execution.

    This service handles:
    - Generating test plans from natural language goals
    - Making real-time execution decisions
    - Recovering from errors during test execution
    - Managing plan approval and modification workflows
    """

    def __init__(self):
        self.api_key = (
            getattr(settings, 'ANTHROPIC_AUTH_TOKEN', None) or
            getattr(settings, 'ANTHROPIC_API_KEY', None)
        )
        self.base_url = getattr(settings, 'ANTHROPIC_BASE_URL', 'https://api.anthropic.com')

    async def generate_test_plan(
        self,
        goal: str,
        url: str,
        context: Dict[str, Any],
        page_screenshot: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive test plan from user goal.

        Args:
            goal: Natural language test goal/requirement
            url: Target URL for testing
            context: Additional context (environment variables, etc.)
            page_screenshot: Optional base64 screenshot for context
            db: Optional database session for logging

        Returns:
            Dict containing:
                - plan_id: Unique identifier for this plan
                - steps: List of structured test steps
                - estimated_duration: Estimated execution time in seconds
                - risk_factors: List of potential issues
                - success_criteria: List of conditions for successful test
        """
        plan_id = str(uuid.uuid4())

        # Build planning prompt
        planning_prompt = self._build_planning_prompt(goal, url, context, page_screenshot)

        try:
            # Use Anthropic API to generate plan
            generated_plan = await self._call_claude_api(planning_prompt)

            # Parse and structure the response
            structured_plan = self._parse_generated_plan(generated_plan, plan_id)

            # Store plan metadata if database session provided
            if db:
                await self._log_plan_generation(db, plan_id, goal, structured_plan)

            return structured_plan

        except Exception as e:
            # Fallback to basic plan generation
            return self._generate_fallback_plan(goal, url, plan_id)

    def _build_planning_prompt(
        self,
        goal: str,
        url: str,
        context: Dict[str, Any],
        page_screenshot: Optional[str] = None
    ) -> str:
        """Build prompt for AI test planning."""
        prompt = f"""You are an expert test automation planner. Given a test goal, generate a detailed, executable test plan.

**Test Goal:**
{goal}

**Target URL:**
{url}

**Additional Context:**
{json.dumps(context, indent=2)}

**Your Task:**
Generate a comprehensive test plan with 3-8 specific, actionable steps. Each step should:
1. Be clear and specific (e.g., "Click the 'Login' button" not "Interact with UI")
2. Include verification criteria
3. Consider potential failures and edge cases
4. Be executable by browser automation tools

**Response Format (JSON):**
{{
    "steps": [
        {{
            "step_number": 1,
            "description": "Navigate to login page",
            "type": "navigation",
            "verification": "Page title contains 'Login'",
            "confidence": 0.95,
            "fallback_strategies": ["wait_for_page_load", "check_alternative_url"]
        }}
    ],
    "estimated_duration": 120,
    "risk_factors": ["dynamic_content", "authentication_required"],
    "success_criteria": ["user_logged_in", "dashboard_visible"]
}}

Generate the plan now:"""

        return prompt

    async def _call_claude_api(self, prompt: str) -> str:
        """Call Claude API for plan generation."""
        import httpx

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        data = {
            "model": getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]

    def _parse_generated_plan(self, generated_text: str, plan_id: str) -> Dict[str, Any]:
        """Parse AI-generated plan into structured format."""
        try:
            # Try to extract JSON from the response
            start_idx = generated_text.find('{')
            end_idx = generated_text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = generated_text[start_idx:end_idx]
                plan_data = json.loads(json_str)

                # Add plan_id
                plan_data["plan_id"] = plan_id

                # Validate structure
                if "steps" not in plan_data:
                    raise ValueError("Plan must contain steps")

                # Ensure required fields
                for step in plan_data["steps"]:
                    step.setdefault("confidence", 0.8)
                    step.setdefault("fallback_strategies", [])

                plan_data.setdefault("estimated_duration", 120)
                plan_data.setdefault("risk_factors", [])
                plan_data.setdefault("success_criteria", [])

                return plan_data

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to basic parsing
            pass

        return self._parse_fallback_response(generated_text, plan_id)

    def _parse_fallback_response(self, text: str, plan_id: str) -> Dict[str, Any]:
        """Parse non-JSON response into basic plan structure."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        steps = []
        step_number = 1

        for line in lines:
            # Skip obvious non-step lines
            if any(marker in line.lower() for marker in ['plan', 'step', 'test', 'note', 'risk']):
                continue

            # If line looks like a step
            if len(line) > 10 and not line.startswith('-'):
                steps.append({
                    "step_number": step_number,
                    "description": line,
                    "type": "action",
                    "verification": "Manual verification required",
                    "confidence": 0.7,
                    "fallback_strategies": ["retry_on_failure"]
                })
                step_number += 1

        return {
            "plan_id": plan_id,
            "steps": steps if steps else self._get_default_steps(),
            "estimated_duration": len(steps) * 30,
            "risk_factors": ["unknown_environment"],
            "success_criteria": ["test_completed"]
        }

    def _get_default_steps(self) -> List[Dict[str, Any]]:
        """Get default test steps as fallback."""
        return [
            {
                "step_number": 1,
                "description": "Navigate to target URL",
                "type": "navigation",
                "verification": "Page loads successfully",
                "confidence": 0.9,
                "fallback_strategies": ["retry_with_timeout"]
            },
            {
                "step_number": 2,
                "description": "Verify page elements",
                "type": "verification",
                "verification": "Key elements are visible",
                "confidence": 0.8,
                "fallback_strategies": ["wait_for_elements"]
            }
        ]

    def _generate_fallback_plan(self, goal: str, url: str, plan_id: str) -> Dict[str, Any]:
        """Generate basic fallback plan when API fails."""
        return {
            "plan_id": plan_id,
            "steps": self._get_default_steps(),
            "estimated_duration": 60,
            "risk_factors": ["api_unavailable"],
            "success_criteria": ["test_completed"],
            "fallback_generated": True,
            "original_goal": goal
        }

    async def approve_plan(
        self,
        plan_id: str,
        modifications: Optional[List[Dict]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Finalize plan with optional user modifications.

        Args:
            plan_id: Plan identifier from generate_test_plan
            modifications: Optional list of step modifications
            db: Optional database session

        Returns:
            Updated plan with modifications applied
        """
        # In a real implementation, you would fetch the plan from storage
        # For now, return basic approval response
        return {
            "plan_id": plan_id,
            "status": "approved",
            "modifications_applied": modifications or [],
            "approved_at": "2024-01-01T00:00:00Z"
        }

    async def make_execution_decision(
        self,
        current_step: Dict,
        page_state: Dict,
        execution_history: List[Dict],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Real-time decision making during test execution.

        Args:
            current_step: The step that just executed
            page_state: Current browser/page state
            execution_history: Previous step results
            db: Optional database session

        Returns:
            Decision dict with:
                - action: "continue" | "retry" | "skip" | "abort"
                - reason: Explanation for the decision
                - modifications: Optional changes for retry
        """
        step_success = current_step.get("success", True)
        confidence = current_step.get("confidence", 0.8)

        if step_success:
            return {
                "action": "continue",
                "reason": "Step completed successfully",
                "modifications": {}
            }

        # Analyze failure and decide on recovery strategy
        error_type = current_step.get("error_type", "unknown")
        fallback_strategies = current_step.get("fallback_strategies", [])

        if error_type == "timeout" and "wait_longer" in fallback_strategies:
            return {
                "action": "retry",
                "reason": "Element not found, will wait longer",
                "modifications": {"timeout": 10000}
            }

        if error_type == "element_not_found" and execution_history:
            # Check if we can skip this step
            critical_steps = [s for s in execution_history if s.get("critical", False)]
            if len(critical_steps) < len(execution_history) / 2:
                return {
                    "action": "skip",
                    "reason": "Non-critical step failed, continuing",
                    "modifications": {}
                }

        # Default to abort on critical failures
        return {
            "action": "abort",
            "reason": f"Critical step failed: {error_type}",
            "modifications": {}
        }

    async def recover_from_error(
        self,
        error: str,
        context: Dict,
        remaining_steps: List[Dict],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Generate recovery strategy for test execution errors.

        Args:
            error: Error message or type
            context: Current execution context
            remaining_steps: Steps yet to be executed
            db: Optional database session

        Returns:
            Recovery strategy with actions to take
        """
        recovery_strategies = {
            "timeout": {
                "action": "retry_with_increased_timeout",
                "timeout_multiplier": 2.0,
                "max_retries": 3
            },
            "element_not_found": {
                "action": "try_alternative_selectors",
                "fallback_to_text": True,
                "wait_for_visibility": True
            },
            "network_error": {
                "action": "retry_with_backoff",
                "initial_delay": 1000,
                "max_delay": 10000
            },
            "authentication_failed": {
                "action": "skip_to_next_test",
                "mark_as_blocked": True
            }
        }

        # Determine error type
        error_type = "unknown"
        for known_type in recovery_strategies.keys():
            if known_type in error.lower():
                error_type = known_type
                break

        strategy = recovery_strategies.get(
            error_type,
            {
                "action": "log_and_continue",
                "mark_as_warning": True
            }
        )

        return {
            "error_type": error_type,
            "recovery_strategy": strategy,
            "can_continue": strategy.get("action") in ["retry_with_increased_timeout", "try_alternative_selectors", "retry_with_backoff", "log_and_continue"],
            "estimated_recovery_time": strategy.get("initial_delay", 0) + strategy.get("timeout_multiplier", 1) * 5000
        }

    async def _log_plan_generation(
        self,
        db: AsyncSession,
        plan_id: str,
        goal: str,
        plan: Dict[str, Any]
    ):
        """Log plan generation to database for analytics."""
        # This would store plan generation metadata
        # Implementation depends on your analytics requirements
        pass

# Singleton instance
_autonomous_planner = None

def get_autonomous_planner() -> AutonomousTestPlanner:
    """Get or create singleton instance of AutonomousTestPlanner."""
    global _autonomous_planner
    if _autonomous_planner is None:
        _autonomous_planner = AutonomousTestPlanner()
    return _autonomous_planner