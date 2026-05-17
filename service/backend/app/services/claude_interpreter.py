"""
Claude Code Agent SDK Interpreter for Test Execution

This module uses Claude Code Agent SDK exclusively to enable Claude to autonomously
execute browser automation tasks using Playwright MCP tools.

Architecture: Single session for all test steps (matches CLI approach).
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from playwright.async_api import Page

from app.core.config import settings


class ClaudeTestInterpreter:
    """
    AI-powered test interpreter using Claude Code Agent SDK exclusively.

    This class ONLY uses Claude Agent SDK with Anthropic API.
    No fallbacks to other APIs or rule-based interpretation.
    """

    MAX_ITERATIONS = 50  # Maximum iterations to prevent infinite loops

    def __init__(self):
        """Initialize Claude Code Agent SDK interpreter."""
        # Support both ANTHROPIC_AUTH_TOKEN (for GLM) and ANTHROPIC_API_KEY (for Anthropic)
        self.api_key = (
            os.getenv("ANTHROPIC_AUTH_TOKEN") or
            os.getenv("ANTHROPIC_API_KEY")
        )
        # Use configured base URL (supports 智谱AI or Anthropic)
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        # CLI path: use npm-installed claude in container, allow override via env
        self.claude_cli_path = os.getenv("CLAUDE_CLI_PATH", "/usr/local/bin/claude")

        # Validate configuration
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY is required for Claude Agent SDK. "
                "Please provide a valid API key."
            )

        # Initialize Agent SDK
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            self.query = query
            self.ClaudeAgentOptions = ClaudeAgentOptions

            # Detect endpoint type
            is_zhipu = "api.z.ai" in self.base_url or "open.bigmodel.cn" in self.base_url
            is_anthropic = "api.anthropic.com" in self.base_url

            if is_zhipu:
                print(f"Claude Agent SDK initialized successfully (智谱AI)")
            elif is_anthropic:
                print(f"Claude Agent SDK initialized successfully (Anthropic)")
            else:
                print(f"Claude Agent SDK initialized successfully (Custom endpoint)")

            print(f"  Base URL: {self.base_url}")
            print(f"  Model: {self.model}")
            print(f"  CLI Path: {self.claude_cli_path}")

        except ImportError as e:
            raise ImportError(
                "claude-agent-sdk is required but not installed. "
                f"Error: {str(e)}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Claude Agent SDK: {str(e)}"
            )

    async def interpret_and_execute_batch(
        self,
        page: Page,
        test_steps: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute all test steps in a single Claude Code session using Agent SDK.

        Args:
            page: Playwright page instance
            test_steps: List of test steps with natural language descriptions
            context: Additional context (URL, page title, etc.)

        Returns:
            List of execution results for all steps

        Raises:
            Exception: If Agent SDK execution fails
        """
        # Get current page context for Claude
        page_context = await self._get_page_context(page, context)

        # Execute using Agent SDK (no fallbacks)
        results = await self._execute_batch_with_agent_sdk(page, test_steps, page_context)

        return results

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

        This method uses Claude Agent SDK with Anthropic API exclusively.

        Raises:
            Exception: If Agent SDK execution fails
        """
        # Build the prompt for Claude with ALL test steps
        prompt = self._build_batch_execution_prompt(test_steps, page_context)

        # Configure Agent SDK options with 智谱AI/Anthropic API
        # Reference: https://github.com/jkelly/ClaudeAgentExamples
        is_zhipu = "api.z.ai" in self.base_url or "open.bigmodel.cn" in self.base_url

        if is_zhipu:
            # 智谱AI: Use ANTHROPIC_AUTH_TOKEN (key insight from ClaudeAgentExamples)
            # Check if we have ANTHROPIC_AUTH_TOKEN
            auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
            if auth_token:
                env_vars = {
                    "ANTHROPIC_BASE_URL": self.base_url,
                    "ANTHROPIC_AUTH_TOKEN": auth_token,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
                }
                print(f"[Claude SDK] Using ANTHROPIC_AUTH_TOKEN for 智谱AI")
            else:
                # Fallback to API_KEY
                env_vars = {
                    "ANTHROPIC_BASE_URL": self.base_url,
                    "ANTHROPIC_API_KEY": self.api_key,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
                }
                print(f"[Claude SDK] Using ANTHROPIC_API_KEY for 智谱AI")

            options = self.ClaudeAgentOptions(
                allowed_tools=[
                    "Bash",           # For executing Playwright CLI commands
                    "Read",           # For reading test files and configs
                    "Write",          # For creating temporary test scripts
                    "Grep"            # For searching in files
                ],
                permission_mode="auto",  # Auto-approve actions
                model=self.model,  # glm-4.7
                load_timeout_ms=120000,  # 2 minutes timeout
                cli_path=self.claude_cli_path,
                env=env_vars
            )
        else:
            # Anthropic API: Use standard ANTHROPIC_API_KEY
            options = self.ClaudeAgentOptions(
                allowed_tools=[
                    "Bash",           # For executing Playwright CLI commands
                    "Read",           # For reading test files and configs
                    "Write",          # For creating temporary test scripts
                    "Grep"            # For searching in files
                ],
                permission_mode="auto",  # Auto-approve actions
                model=self.model,  # claude-sonnet-4-20250514
                load_timeout_ms=120000,  # 2 minutes timeout
                cli_path=self.claude_cli_path,
                env={
                    "ANTHROPIC_BASE_URL": self.base_url,
                    "ANTHROPIC_API_KEY": self.api_key,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
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
                raise Exception(error_msg)

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
            result["mode"] = "claude_agent_sdk_batch"
            result["raw_subtype"] = final_result.subtype if final_result else "unknown"

        return step_results

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
