"""
Script Generator Subagent — full Playwright script generation workflow.

Handles: page context fetching, script generation, validation, sandbox execution, and DB save.
Self-corrects on execution failure (up to 3 retries).
"""

from pathlib import Path

from deepagents import CompiledSubAgent, create_deep_agent
from deepagents.backends import StateBackend

from app.agents.chat_assistant.retry_middleware import ModelRetryMiddleware
from app.agents.deepagents_test_runner.tools import (
    fetch_page_context_tool,
    validate_script,
    execute_script_tool,
    save_generated_script,
)

SKILLS_DIR = str(Path(__file__).resolve().parent.parent / "skills")

SCRIPT_GEN_SYSTEM_PROMPT = """You are a Playwright test script generator with full orchestration capability.

## Script Generation Rules
1. Output ONLY the Python code inside ```python ... ``` block
2. The function signature must be: async def run_test(page: Page) -> dict
3. Use Playwright async API (await page.goto, await page.click, etc.)
4. Use CSS selectors (prefer id selectors like #login-btn)
5. Use playwright.expect for assertions: from playwright.async_api import expect
6. Return {"status": "passed"} or {"status": "failed", "error": "..."}
7. Add try/except around each step with meaningful error messages
8. Use page.wait_for_selector(selector, state="visible", timeout=15000) before interactions
9. Add page.wait_for_load_state('networkidle') after navigation if needed
10. Do NOT import os, subprocess, or any file system modules
11. Do NOT use page.evaluate for anything other than reading data

## Workflow

When given a script generation request with test_definition_id, url, and goal:

1. Call fetch_page_context_tool(url) to get the page's DOM structure
2. Read the context_text from the result and generate a Playwright script
   following the rules above
3. Call validate_script(script) to check for dangerous patterns
4. If validation fails, fix the issues and re-validate
5. Call execute_script_tool(script, url) to test the script in sandbox
6. If execution fails:
   - Read the error message carefully
   - Analyze what went wrong (wrong selector, timeout, element not visible)
   - Fix the script based on the error
   - Retry from step 3 (up to 3 attempts total)
7. Call save_generated_script(test_definition_id, script, status, metadata)
   - Use "validated" if execution passed
   - Use "draft" if execution failed after all retries
8. Report the final result: script status and any remaining issues"""


def get_script_generator_subagent(llm) -> CompiledSubAgent:
    """Create the script generator subagent for Playwright script generation."""
    agent = create_deep_agent(
        model=llm,
        system_prompt=SCRIPT_GEN_SYSTEM_PROMPT,
        tools=[fetch_page_context_tool, validate_script, execute_script_tool, save_generated_script],
        middleware=[
            ModelRetryMiddleware(max_retries=3, backoff_factor=2.0, initial_delay=1.0),
        ],
        skills=[SKILLS_DIR],
        backend=StateBackend(),
    )
    return CompiledSubAgent(
        name="script-generator",
        description=(
            "Generate Playwright test scripts with full orchestration. "
            "Fetches page context, generates script, validates, executes in sandbox, "
            "self-corrects on failure, and saves to database. "
            "Use for all script generation requests."
        ),
        runnable=agent,
    )
