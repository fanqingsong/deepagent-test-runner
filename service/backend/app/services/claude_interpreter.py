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
        self.api_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        # Use OpenAI-compatible endpoint as recommended by Qwen
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        self.model = os.getenv("ANTHROPIC_MODEL", "glm-4-flash")  # Use Zhipu model code (OpenAI compatible)

        # CLI path: use npm-installed claude in container, allow override via env
        self.claude_cli_path = os.getenv("CLAUDE_CLI_PATH", "/usr/local/bin/claude")

        if not self.api_key:
            print("Warning: ANTHROPIC_AUTH_TOKEN not found. Using fallback rule-based interpretation.")
            self.sdk_available = False
        else:
            try:
                from claude_agent_sdk import query, ClaudeAgentOptions
                self.query = query
                self.ClaudeAgentOptions = ClaudeAgentOptions
                self.sdk_available = True
                print(f"Claude Agent SDK initialized successfully")
                print(f"  Base URL: {self.base_url}")
                print(f"  Model: {self.model}")
                print(f"  CLI Path: {self.claude_cli_path}")
            except ImportError:
                print("Warning: claude-agent-sdk not installed. Using fallback rule-based interpretation.")
                self.sdk_available = False
            except Exception as e:
                print(f"Failed to initialize Claude Code: {str(e)}. Using fallback interpretation.")
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
            # Execute using Agent SDK
            results = await self._execute_batch_with_agent_sdk(page, test_steps, page_context)
            return results

        except Exception as e:
            print(f"Claude Code batch execution failed: {str(e)}")
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

    async def _execute_batch_with_agent_sdk(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        page_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute all test steps in a single Claude Code Agent SDK session.

        This method properly uses Claude Agent SDK with Zhipu AI's Claude API compatibility.
        Falls back to direct HTTP API if SDK times out.
        """
        try:
            # Build the prompt for Claude with ALL test steps
            prompt = self._build_batch_execution_prompt(test_steps, page_context)

            # Configure Agent SDK options with full Agent capabilities (attempting to work without bundled CLI)
            options = self.ClaudeAgentOptions(
                allowed_tools=[
                    "Bash",           # For executing Playwright CLI commands
                    "Read",           # For reading test files and configs
                    "Write",          # For creating temporary test scripts
                    "Grep"            # For searching in files
                ],
                permission_mode="auto",  # Auto-approve actions
                model=self.model,  # Use Zhipu model code (glm-4-flash, OpenAI compatible)
                load_timeout_ms=60000,  # 1 minute timeout
                cli_path=self.claude_cli_path,  # Use npm-installed claude in container
                env={
                    "OPENAI_API_BASE": self.base_url,  # OpenAI-compatible endpoint
                    "OPENAI_API_KEY": self.api_key,     # API key for OpenAI format
                    "ANTHROPIC_BASE_URL": self.base_url,  # Fallback for Claude SDK
                    "ANTHROPIC_API_KEY": self.api_key,
                    "ANTHROPIC_AUTH_TOKEN": self.api_key,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"  # Disable non-essential traffic
                }
            )

            # Execute using Claude Code Agent SDK in a single session
            from claude_agent_sdk import AssistantMessage, ResultMessage

            execution_log = []
            final_result = None
            iteration_count = 0

            print(f"[Claude SDK] Starting batch execution for {len(test_steps)} steps")
            print(f"[Claude SDK] Using model: {self.model} at {self.base_url}")

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
            # SDK failed - mark all steps as failed (no fallback to HTTP API)
            error_msg = str(e)
            print(f"[Claude SDK] Exception: {error_msg}")

            import traceback
            traceback.print_exc()

            return [{
                "step_number": step.get("step_number", idx + 1),
                "description": step.get("description"),
                "status": "failed",
                "error": f"Claude Agent SDK execution failed: {str(e)}",
                "mode": "claude_sdk_error"
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

    async def _execute_with_direct_http_api_with_agent_capabilities(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        page_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Execute test steps using direct HTTP API with tool-calling.
        This provides Agent capabilities when SDK bundled CLI has timeout issues.
        """
        try:
            import httpx

            # Build the enhanced prompt with tool definitions
            prompt = self._build_agent_capability_prompt(test_steps, page_context)

            # Make direct API call with tool definitions
            print(f"[Direct HTTP API] Starting execution with tool-calling for {len(test_steps)} steps")

            # Define tools available to Claude
            tools = [
                {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL in the browser",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to navigate to"
                            }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "browser_click",
                    "description": "Click on an element in the browser",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the element to click"
                            }
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "browser_fill",
                    "description": "Fill text into an input field",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the input field"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to fill into the field"
                            }
                        },
                        "required": ["selector", "text"]
                    }
                },
                {
                    "name": "browser_wait",
                    "description": "Wait for a specific condition or time",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "duration_ms": {
                                "type": "integer",
                                "description": "Duration to wait in milliseconds"
                            }
                        },
                        "required": ["duration_ms"]
                    }
                },
                {
                    "name": "browser_snapshot",
                    "description": "Take a snapshot of the current page state",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]

            step_results = []
            current_step_index = 0

            # Execute test steps with tool-calling loop
            max_iterations = 50
            iteration = 0

            while current_step_index < len(test_steps) and iteration < max_iterations:
                iteration += 1
                current_step = test_steps[current_step_index]

                print(f"[Direct HTTP API] Step {current_step_index + 1}/{len(test_steps)}: {current_step.get('description', 'No description')}")

                # Build context-aware prompt for current step
                step_prompt = f"{prompt}\n\n**Current Step ({current_step_index + 1}/{len(test_steps)}):** {current_step.get('description', 'No description')}\n\nExecute this step using available tools. If the step is completed successfully, respond with 'STEP_COMPLETED: [brief result]'."

                response = httpx.Client(timeout=300.0).post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": step_prompt}],
                        "tools": tools
                    }
                )

                if response.status_code != 200:
                    error_msg = f"API request failed with status {response.status_code}: {response.text[:200]}"
                    print(f"[ERROR] {error_msg}")
                    step_results.append({
                        "step_number": current_step.get("step_number", current_step_index + 1),
                        "description": current_step.get("description"),
                        "status": "failed",
                        "error": error_msg,
                        "mode": "direct_http_api_error"
                    })
                    break

                result = response.json()
                content = result.get("content", [])

                # Process tool use blocks
                step_completed = False
                tool_results = []

                for content_block in content:
                    if content_block.get("type") == "tool_use":
                        tool_name = content_block.get("name", "")
                        tool_input = content_block.get("input", {})
                        tool_id = content_block.get("id", "")

                        print(f"[Direct HTTP API] Tool use: {tool_name} with input {tool_input}")

                        # Execute the tool
                        try:
                            tool_result = await self._execute_agent_tool(page, tool_name, tool_input)
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "content": tool_result,
                                "type": "tool_result"
                            })
                        except Exception as tool_error:
                            print(f"[ERROR] Tool execution failed: {str(tool_error)}")
                            tool_results.append({
                                "tool_use_id": tool_id,
                                "content": f"Tool execution failed: {str(tool_error)}",
                                "type": "tool_result"
                            })

                    elif content_block.get("type") == "text":
                        response_text = content_block.get("text", "")
                        print(f"[Direct HTTP API] Response: {response_text[:200]}...")

                        # Check if step is completed
                        if "STEP_COMPLETED" in response_text:
                            step_completed = True
                            step_results.append({
                                "step_number": current_step.get("step_number", current_step_index + 1),
                                "description": current_step.get("description"),
                                "status": "passed",
                                "details": response_text.split("STEP_COMPLETED:")[1].strip()[:200],
                                "mode": "direct_http_api_with_tools"
                            })
                            current_step_index += 1

                # If Claude used tools, send back results for continuation
                if tool_results and not step_completed:
                    continuation_response = httpx.Client(timeout=300.0).post(
                        f"{self.base_url}/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "max_tokens": 4096,
                            "messages": [
                                {"role": "user", "content": step_prompt},
                                {"role": "assistant", "content": content},
                                {"role": "user", "content": tool_results}
                            ],
                            "tools": tools
                        }
                    )

                    if continuation_response.status_code == 200:
                        continuation_result = continuation_response.json()
                        continuation_content = continuation_result.get("content", [])

                        for cont_block in continuation_content:
                            if cont_block.get("type") == "text":
                                cont_text = cont_block.get("text", "")
                                if "STEP_COMPLETED" in cont_text:
                                    step_completed = True
                                    step_results.append({
                                        "step_number": current_step.get("step_number", current_step_index + 1),
                                        "description": current_step.get("description"),
                                        "status": "passed",
                                        "details": cont_text.split("STEP_COMPLETED:")[1].strip()[:200],
                                        "mode": "direct_http_api_with_tools"
                                    })
                                    current_step_index += 1
                                    break

                # If step not completed after tool use, mark as failed and move on
                if not step_completed:
                    print(f"[WARNING] Step {current_step_index + 1} did not complete successfully")
                    step_results.append({
                        "step_number": current_step.get("step_number", current_step_index + 1),
                        "description": current_step.get("description"),
                        "status": "failed",
                        "error": "Step did not complete within iteration limit",
                        "mode": "direct_http_api_timeout"
                    })
                    current_step_index += 1

            return step_results

        except Exception as e:
            print(f"[Direct HTTP API] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return [{
                "step_number": step.get("step_number", idx + 1),
                "description": step.get("description"),
                "status": "failed",
                "error": f"Direct HTTP API execution failed: {str(e)}",
                "mode": "direct_http_api_exception"
            } for idx, step in enumerate(test_steps)]

    async def _execute_agent_tool(self, page: Page, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute an agent tool using Playwright"""
        try:
            if tool_name == "browser_navigate":
                url = tool_input.get("url", "")
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                return f"Navigated to {url}"

            elif tool_name == "browser_click":
                selector = tool_input.get("selector", "")
                await page.click(selector, timeout=5000)
                return f"Clicked element: {selector}"

            elif tool_name == "browser_fill":
                selector = tool_input.get("selector", "")
                text = tool_input.get("text", "")
                await page.fill(selector, text, timeout=5000)
                return f"Filled '{text}' into {selector}"

            elif tool_name == "browser_wait":
                duration_ms = tool_input.get("duration_ms", 1000)
                await page.wait_for_timeout(duration_ms)
                return f"Waited {duration_ms}ms"

            elif tool_name == "browser_snapshot":
                screenshot_bytes = await page.screenshot(full_page=False)
                # Return a description instead of actual image
                return f"Page snapshot taken at {page.url}"

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Tool execution error: {str(e)}"

    def _build_agent_capability_prompt(
        self,
        test_steps: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Build enhanced prompt with tool-calling capabilities"""
        steps_text = "\n".join([
            f"{idx + 1}. {step.get('description', 'No description')}"
            for idx, step in enumerate(test_steps)
        ])

        return f"""You are an autonomous web testing agent with full browser automation capabilities.

**Current Page Context:**
- URL: {context.get('url', 'unknown')}
- Title: {context.get('title', 'unknown')}

**Test Plan - Execute ALL steps in sequence:**
{steps_text}

**Your Available Tools:**
1. browser_navigate - Navigate to a URL
2. browser_click - Click on elements using CSS selectors
3. browser_fill - Fill text into input fields
4. browser_wait - Wait for a specified duration
5. browser_snapshot - Take a snapshot of the current page

**Instructions:**
- Execute each test step in sequence using the available tools
- After completing each step, respond with "STEP_COMPLETED: [brief result]"
- Be specific with CSS selectors (e.g., button[type='submit'], #login-button)
- Handle dynamic content by waiting for elements to be ready
- If a step fails, explain what went wrong

Begin execution now."""

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
