# Claude Code Agent SDK Integration

## Overview

The `claude_interpreter.py` module has been refactored to use the **Claude Code Agent SDK**, enabling Claude to autonomously execute browser automation tasks using Playwright.

## What Changed

### Before
- Used `anthropic` library to generate Playwright code
- Manually parsed and executed generated code
- Limited to pre-defined code patterns

### After
- Uses `claude-agent-sdk` for autonomous test execution
- Direct tool-based interaction with Playwright
- More flexible and powerful AI-driven execution

## Architecture

```
Test Step → Claude Code Agent SDK → Playwright Tools → Browser
```

The new architecture provides Claude with direct access to Playwright tools, allowing it to autonomously decide how to execute each test step.

## Installation

### 1. Install the SDK

```bash
pip install claude-agent-sdk
```

### 2. Update requirements.txt

The `requirements.txt` has been updated to include:
```
claude-agent-sdk==0.1.72
```

### 3. Set Environment Variables

Ensure the following environment variable is set:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Available Tools

Claude has access to the following Playwright tools:

1. **navigate(url)** - Navigate to a URL
2. **click(selector)** - Click an element
3. **fill(selector, value)** - Fill an input field
4. **wait_for_selector(selector, timeout?)** - Wait for an element
5. **wait_for_timeout(timeout)** - Wait for specific time
6. **screenshot(path?)** - Take a screenshot
7. **get_text_content(selector)** - Get text content

## Usage

### Basic Usage

```python
from app.services import get_claude_interpreter
from playwright.async_api import async_playwright

async def execute_test():
    interpreter = get_claude_interpreter()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Execute test step
        result = await interpreter.interpret_and_execute(
            page,
            "Navigate to https://example.com and click the login button"
        )

        print(result)
        # Output: {"success": true, "details": "Executed click: ...", "action": "click"}

        await browser.close()
```

### With Context

```python
result = await interpreter.interpret_and_execute(
    page,
    "Enter user@example.com in the email field",
    context={
        "step_number": 1,
        "environment": {"base_url": "https://example.com"}
    }
)
```

## Fallback Mechanism

If the Agent SDK is not available or fails, the system automatically falls back to a rule-based interpreter:

```python
# Fallback handles common patterns:
- "Navigate to <url>" → goto()
- "Click <element>" → click()
- "Enter <value> in <field>" → fill()
- "Wait <time> seconds" → wait_for_timeout()
- "Screenshot" → screenshot()
```

## How It Works

### 1. Test Step Input
```python
"Navigate to https://example.com and click the submit button"
```

### 2. Claude Interpretation
Claude analyzes the step using the Agent SDK and decides which tools to use.

### 3. Tool Execution
```python
TOOL: navigate
PARAMS: {"url": "https://example.com"}

TOOL: click
PARAMS: {"selector": "button[type='submit']"}
```

### 4. Result
```python
{
    "success": True,
    "details": "Executed click: {'success': True, 'action': 'clicked', ...}",
    "action": "click"
}
```

## Advantages

### 1. Autonomous Execution
Claude decides how to execute each step, not just following pre-defined patterns.

### 2. Natural Language Understanding
Better understanding of complex test descriptions.

### 3. Error Handling
Claude can handle errors and retry with different approaches.

### 4. Extensibility
Easy to add new tools and capabilities.

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
ANTHROPIC_BASE_URL=https://api.anthropic.com
API_TIMEOUT_MS=300000
```

### Tool Configuration

You can customize available tools by modifying the `_create_playwright_tools()` method:

```python
def _create_playwright_tools(self, page: Page) -> Dict[str, Any]:
    # Add custom tools here
    return {
        "custom_action": {
            "description": "Custom action description",
            "parameters": {
                "param1": "description"
            },
            "handler": self._custom_handler
        }
    }
```

## Troubleshooting

### Issue: "claude-agent-sdk not installed"

**Solution:**
```bash
pip install claude-agent-sdk
```

### Issue: "ANTHROPIC_API_KEY not found"

**Solution:**
Set the environment variable:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

### Issue: Agent SDK execution fails

**Solution:**
The system will automatically fall back to rule-based interpretation. Check logs for details.

## Migration from Old Implementation

### Old Code
```python
from anthropic import Anthropic

client = Anthropic(api_key=api_key)
response = client.messages.create(...)
code = extract_code(response)
execute_code(code)
```

### New Code
```python
from claude_agent_sdk import query

async for message in query(prompt=prompt, options=options):
    # Claude autonomously executes tools
    pass
```

## Future Enhancements

1. **Full MCP Integration**: Use Model Context Protocol for tool integration
2. **Multi-step Planning**: Claude can plan and execute complex multi-step scenarios
3. **Self-healing Tests**: Claude can adapt to UI changes automatically
4. **Visual Testing**: Integrate visual regression testing

## References

- [Claude Code Agent SDK Documentation](https://code.claude.com/docs/zh-CN/agent-sdk/quickstart)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [claude-agent-sdk on PyPI](https://pypi.org/project/claude-agent-sdk/)
- [claude-agent-sdk-python on GitHub](https://github.com/anthropics/claude-agent-sdk-python)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs for detailed error messages
3. Ensure all dependencies are installed correctly
4. Verify environment variables are set

---

**Note**: This implementation uses a hybrid approach combining Claude Code Agent SDK with direct Anthropic API calls for maximum compatibility and reliability.
