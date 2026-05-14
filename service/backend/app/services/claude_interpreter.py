"""
Claude Code Agent SDK Interpreter for Test Execution

This module uses Claude Code Agent SDK to enable Claude to autonomously
execute browser automation tasks using Playwright MCP tools.

Refactored to match CLI architecture: execute all test steps in a single session.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from playwright.async_api import Page

from app.core.config import settings


class ClaudeTestInterpreter:
    """
    AI-powered test interpreter using Claude Code Agent SDK to enable
    autonomous test execution with natural language understanding.

    Architecture: Single session for all test steps (matches CLI approach).
    """

    MAX_ITERATIONS = 50  # Maximum iterations to prevent infinite loops

    def __init__(self):
        """Initialize Claude Code Agent SDK interpreter."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            print("Warning: ANTHROPIC_API_KEY not found. Using fallback rule-based interpretation.")
            self.sdk_available = False
        else:
            try:
                # Import Claude Code Agent SDK
                from claude_agent_sdk import query, ClaudeAgentOptions

                self.query = query
                self.ClaudeAgentOptions = ClaudeAgentOptions
                self.sdk_available = True
                print("Claude Code Agent SDK initialized successfully")

            except ImportError:
                print("Warning: claude-agent-sdk not installed. Using fallback rule-based interpretation.")
                print("Install with: pip install claude-agent-sdk")
                self.sdk_available = False
            except Exception as e:
                print(f"Failed to initialize Claude Code Agent SDK: {str(e)}. Using fallback interpretation.")
                self.sdk_available = False

    async def interpret_and_execute_batch(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute all test steps in a single Claude Code session (matches CLI architecture).

        Args:
            page: Playwright page instance
            test_steps: List of test steps with natural language descriptions
            context: Additional context (URL, page title, etc.)

        Returns:
            List of execution results for all steps
        """
        if not self.sdk_available:
            # Fallback to rule-based interpretation for each step
            return await self._fallback_batch_interpretation(page, test_steps, context)

        try:
            # Get current page context for Claude
            page_context = await self._get_page_context(page, context)

            # Execute all steps in a single session
            results = await self._execute_batch_with_agent_sdk(page, test_steps, page_context)

            return results

        except Exception as e:
            print(f"Claude Code Agent SDK batch execution failed: {str(e)}")
            # Fallback to rule-based interpretation
            return await self._fallback_batch_interpretation(page, test_steps, context)

    async def interpret_and_execute(
        self,
        page: Page,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility. Use interpret_and_execute_batch instead.
        """
        result = await self.interpret_and_execute_batch(
            page,
            [{"step_number": 1, "description": description}],
            context
        )
        return result[0] if result else {"success": False, "error": "No result returned"}

    async def _get_page_context(self, page: Page, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Gather current page context to help Claude understand the state."""
        try:
            context = {
                "url": page.url,
                "title": await page.title(),
            }

            # Add any additional context provided
            if additional_context:
                context.update(additional_context)

            return context
        except Exception as e:
            print(f"Error getting page context: {str(e)}")
            return {"url": "unknown", "title": "unknown"}

    async def _execute_with_agent_sdk(
        self,
        page: Page,
        description: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the test step using Claude Code Agent SDK with full autonomy.

        This method allows Claude to autonomously execute browser actions by using
        Playwright CLI through the Bash tool, maintaining full control and autonomy.
        """
        try:
            # Build the prompt for Claude
            prompt = self._build_execution_prompt(description, page_context)

            # Configure Agent SDK options with Bash tool for Playwright CLI access
            options = self.ClaudeAgentOptions(
                allowed_tools=[
                    "Bash",           # For executing Playwright CLI commands
                    "Read",           # For reading test files and configs
                    "Write",          # For creating temporary test scripts
                    "Grep"            # For searching in files
                ],
                permission_mode="auto"  # Auto-approve actions
            )

            # Execute using Claude Code Agent SDK with full autonomy
            from claude_agent_sdk import AssistantMessage, ResultMessage

            execution_log = []
            final_result = None
            iteration_count = 0

            print(f"[Claude SDK] Starting autonomous execution for: {description}")

            async for message in self.query(
                prompt=prompt,
                options=options
            ):
                iteration_count += 1

                # Prevent infinite loops
                if iteration_count > self.MAX_ITERATIONS:
                    error_msg = f"Exceeded maximum iterations ({self.MAX_ITERATIONS}). Terminating to prevent infinite loop."
                    print(f"[ERROR] {error_msg}")
                    return {"success": False, "error": error_msg, "mode": "autonomous_claude_sdk"}
                print(f"[Claude SDK] Iteration {iteration_count}")

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            text_content = block.text[:200]  # Limit log length
                            execution_log.append(f"Claude: {text_content}")
                            print(f"[Claude SDK] Claude: {text_content}")
                        elif hasattr(block, "name"):
                            tool_name = block.name
                            execution_log.append(f"Tool called: {tool_name}")
                            print(f"[Claude SDK] Tool: {tool_name}")

                elif isinstance(message, ResultMessage):
                    final_result = message
                    execution_log.append(f"Done: {message.subtype}")
                    print(f"[Claude SDK] Done: {message.subtype}")
                    break  # Exit loop on completion

            print(f"[Claude SDK] Execution completed. Success: {final_result.subtype if final_result else 'unknown'}")

            # Return execution result with proper boolean success status
            success_status = final_result.subtype == "success" if final_result else False

            return {
                "success": success_status,  # Boolean value for status checking
                "details": "\n".join(execution_log),
                "action": description,
                "mode": "autonomous_claude_sdk",
                "raw_subtype": final_result.subtype if final_result else "unknown"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Agent SDK execution failed: {str(e)}",
                "details": f"Attempted: {description}"
            }

    def _build_execution_prompt(self, description: str, context: Dict[str, Any]) -> str:
        """Build the prompt for Claude Code Agent SDK with Playwright CLI instructions."""
        return f"""You are an expert browser automation assistant with full autonomous control over browser testing.

**Current Page Context:**
- URL: {context.get('url', 'unknown')}
- Title: {context.get('title', 'unknown')}

**Test Step to Execute:**
{description}

**Your Capabilities:**
You have FULL AUTONOMOUS ACCESS to browser automation through Playwright CLI. You can:

1. **Use Bash tool to execute Playwright commands:**
   - `playwright codegen <url>` - Record and generate code
   - `playwright test` - Run tests
   - `npx playwright screenshot <file> --url=<url>` - Take screenshot
   - Node.js scripts with Playwright API

2. **Create and execute JavaScript files** with Playwright:
   ```bash
   cat > test.js << 'EOF'
   const {{ chromium }} = require('playwright');
   (async () => {{
     const browser = await chromium.launch();
     const page = await browser.newPage();
     await page.goto('https://example.com');
     await page.click('#button');
     await browser.close();
   }})();
   EOF
   node test.js
   ```

3. **Direct Playwright CLI operations:**
   - `npx playwright-cli screenshot <url> <file>`
   - `npx playwright-cli pdf <url> <file>`
   - `npx playwright-cli codegen <url>`

**Execution Strategy:**
1. Create temporary JavaScript files using Write tool
2. Execute them using Bash tool with Node.js and Playwright
3. Verify results and take screenshots for debugging
4. Report detailed execution results

**Example Workflow:**
```bash
# Create test script
cat > /tmp/test_step.js << 'EOF'
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage();
  await page.goto('https://example.com');
  await page.fill('#username', 'testuser');
  await page.click('#login-btn');
  await page.screenshot({{ path: '/tmp/result.png' }});
  await browser.close();
}})();
EOF

# Execute the script
node /tmp/test_step.js
```

**Instructions:**
1. Analyze the test step
2. Create appropriate Playwright scripts
3. Execute them autonomously using Bash
4. Take screenshots for verification
5. Report detailed results

Execute the test step now using Playwright CLI through Bash commands.
"""

    async def _fallback_interpretation(
        self,
        page: Page,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fallback to rule-based interpretation when Agent SDK is not available."""
        # Import the rule-based interpreter
        from app.tasks.test_execution import _interpret_and_execute
        return await _interpret_and_execute(page, description, context or {})

    async def _execute_batch_with_agent_sdk(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        page_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute all test steps in a single Claude Code session (matches CLI architecture).

        This is the NEW method that replaces per-step calls with a single batch execution.
        """
        try:
            # Build the prompt for Claude with ALL test steps
            prompt = self._build_batch_execution_prompt(test_steps, page_context)

            # Configure Agent SDK options
            options = self.ClaudeAgentOptions(
                allowed_tools=[
                    "Bash",           # For executing Playwright CLI commands
                    "Read",           # For reading test files and configs
                    "Write",          # For creating temporary test scripts
                    "Grep"            # For searching in files
                ],
                permission_mode="auto"  # Auto-approve actions
            )

            # Execute using Claude Code Agent SDK in a single session
            from claude_agent_sdk import AssistantMessage, ResultMessage

            execution_log = []
            final_result = None
            iteration_count = 0

            print(f"[Claude SDK] Starting batch execution for {len(test_steps)} steps")

            # Track step results in order
            step_results = []
            current_step_index = 0

            async for message in self.query(
                prompt=prompt,
                options=options
            ):
                iteration_count += 1

                # Prevent infinite loops
                if iteration_count > self.MAX_ITERATIONS:
                    error_msg = f"Exceeded maximum iterations ({self.MAX_ITERATIONS}). Terminating to prevent infinite loop."
                    print(f"[ERROR] {error_msg}")
                    return [{"success": False, "error": error_msg, "mode": "autonomous_claude_sdk"} for _ in test_steps]
                print(f"[Claude SDK] Iteration {iteration_count}")

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            text_content = block.text[:500]  # Longer limit for batch
                            execution_log.append(f"Claude: {text_content}")
                            print(f"[Claude SDK] Claude: {text_content}")

                            # Try to detect step completion markers in Claude's response
                            # This helps us track progress even though Claude runs autonomously
                            for idx, step in enumerate(test_steps):
                                step_desc = step.get("description", "")[:30]
                                if step_desc.lower() in text_content.lower():
                                    if idx >= len(step_results):
                                        # Assume step completed if Claude mentions it
                                        step_results.append({
                                            "step_number": step.get("step_number", idx + 1),
                                            "description": step.get("description"),
                                            "status": "passed",
                                            "details": f"Completed: {text_content[:100]}"
                                        })
                                        print(f"[Claude SDK] Detected completion of step {idx + 1}")

                        elif hasattr(block, "name"):
                            tool_name = block.name
                            execution_log.append(f"Tool called: {tool_name}")
                            print(f"[Claude SDK] Tool: {tool_name}")

                elif isinstance(message, ResultMessage):
                    final_result = message
                    execution_log.append(f"Done: {message.subtype}")
                    print(f"[Claude SDK] Done: {message.subtype}")
                    break  # Exit loop on completion

            print(f"[Claude SDK] Batch execution completed. Success: {final_result.subtype if final_result else 'unknown'}")

            # If we didn't capture all steps through detection, mark remaining as passed based on final result
            success_status = final_result.subtype == "success" if final_result else False

            if len(step_results) < len(test_steps):
                # Fill in missing steps based on overall success
                for idx in range(len(step_results), len(test_steps)):
                    step = test_steps[idx]
                    step_results.append({
                        "step_number": step.get("step_number", idx + 1),
                        "description": step.get("description"),
                        "status": "passed" if success_status else "failed",
                        "details": "Completed in batch execution",
                        "error": None if success_status else "Batch execution failed"
                    })

            # Add execution metadata to each result
            for result in step_results:
                result["mode"] = "autonomous_claude_sdk_batch"
                result["raw_subtype"] = final_result.subtype if final_result else "unknown"

            return step_results

        except Exception as e:
            # On exception, mark all steps as failed
            print(f"Exception in batch execution: {str(e)}")
            return [{
                "step_number": step.get("step_number", idx + 1),
                "description": step.get("description"),
                "status": "failed",
                "error": f"Batch execution failed: {str(e)}",
                "mode": "error"
            } for idx, step in enumerate(test_steps)]

    def _build_batch_execution_prompt(
        self,
        test_steps: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build the prompt for Claude Code Agent SDK with ALL test steps (matches CLI system prompt).
        """
        # Format test steps as a numbered list (similar to CLI format)
        steps_text = "\n".join([
            f"{idx + 1}. {step.get('description', 'No description')}"
            for idx, step in enumerate(test_steps)
        ])

        return f"""You are a software tester that can use the Playwright CLI to interact with a web app.

You will be executing a test plan with {len(test_steps)} steps.

**Current Page Context:**
- URL: {context.get('url', 'unknown')}
- Title: {context.get('title', 'unknown')}

**Test Plan - Execute ALL steps in sequence:**
{steps_text}

**Your Capabilities:**
You have FULL AUTONOMOUS ACCESS to browser automation through Playwright CLI. You can:

1. **Use Bash tool to execute Playwright commands:**
   - `playwright codegen <url>` - Record and generate code
   - Node.js scripts with Playwright API

2. **Create and execute JavaScript files** with Playwright:
   ```bash
   cat > test.js << 'EOF'
   const {{ chromium }} = require('playwright');
   (async () => {{
     const browser = await chromium.launch({{ headless: true }});
     const page = await browser.newPage();
     await page.goto('https://example.com');
     await page.fill('#email', 'test@example.com');
     await page.click('#login-btn');
     await browser.close();
   }})();
   EOF
   node test.js
   ```

**Execution Instructions:**
1. Execute the test steps SEQUENTIALLY in order (1 through {len(test_steps)})
2. Use Bash tool to create and execute Playwright scripts
3. Continue to the next step only after the current step succeeds
4. If a step fails, stop execution and report the error
5. Take screenshots for verification when needed

**Important:**
- Execute ALL steps in this single session
- Do not ask for confirmation
- Report completion status for each step

Start executing the test plan now.
"""

    async def _fallback_batch_interpretation(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback to rule-based interpretation for each step when Agent SDK is not available.
        """
        from app.tasks.test_execution import _interpret_and_execute

        results = []
        for step in test_steps:
            try:
                result = await _interpret_and_execute(
                    page,
                    step.get("description", ""),
                    context or {}
                )
                results.append({
                    "step_number": step.get("step_number", len(results) + 1),
                    "description": step.get("description"),
                    "status": "passed" if result.get("success") else "failed",
                    "details": result.get("details", ""),
                    "error": result.get("error"),
                    "mode": "rule_based_fallback"
                })
            except Exception as e:
                results.append({
                    "step_number": step.get("step_number", len(results) + 1),
                    "description": step.get("description"),
                    "status": "failed",
                    "error": str(e),
                    "mode": "rule_based_fallback"
                })
        return results
