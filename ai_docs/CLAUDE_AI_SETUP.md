# Claude AI Integration Setup Guide

## Overview

The Claude Code Test Runner now supports AI-powered test execution using Claude's advanced natural language understanding capabilities. This allows you to write test steps in plain English and have Claude automatically generate and execute the appropriate browser automation code.

## Features

- 🧠 **True Natural Language Understanding**: Claude understands complex instructions beyond simple patterns
- 🎯 **Intelligent Element Detection**: Claude can intelligently identify UI elements based on context
- 🔄 **Adaptive Execution**: Claude adjusts its approach based on page structure and content
- 📸 **Smart Screenshots**: Automatic screenshot capture for debugging failed steps
- 🛡️ **Graceful Fallback**: Falls back to rule-based interpretation if Claude API is unavailable

## Setup

### 1. Get Anthropic API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key

### 2. Configure Environment

Add your API key to the `.env` file:

```bash
# Claude AI API Key
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

### 3. Restart Services

```bash
docker compose build scheduler-service scheduler-worker
docker compose up -d scheduler-service scheduler-worker
```

## Usage Examples

### Simple Navigation
**Natural Language**: "Navigate to https://example.com"
**Claude Understanding**: Identifies this as a navigation action and generates:
```python
await page.goto("https://example.com")
await page.wait_for_load_state("networkidle")
```

### Complex Form Interaction
**Natural Language**: "Enter my email address user@example.com in the email field"
**Claude Understanding**: 
- Recognizes this as a form filling action
- Identifies "email" as the field type
- Extracts "user@example.com" as the value
- Generates appropriate selector and fill operation

### Smart Element Detection
**Natural Language**: "Click the blue submit button at the bottom of the form"
**Claude Understanding**:
- Understands "submit button" refers to a submit-type button
- Considers "blue" and "bottom of the form" as contextual hints
- Generates intelligent selector strategies

### Conditional Actions
**Natural Language**: "Wait for the login button to appear, then click it"
**Claude Understanding**:
- Breaks this into two operations
- First waits for the element to be present
- Then performs the click action

## Advanced Features

### Context-Aware Execution
Claude receives context about the current page state:
- Current URL
- Page title
- Previous steps executed
- Environment variables

This helps Claude make more intelligent decisions about element selection and interaction strategies.

### Error Recovery
When Claude's suggested action fails, the system:
1. Logs the error details
2. Provides Claude with error context
3. Requests alternative approach
4. Falls back to rule-based interpretation if needed

### Screenshot Capture
Automatic screenshots are captured:
- Before each step (for context)
- After failures (for debugging)
- When explicitly requested ("Take a screenshot")

## API Cost Considerations

- **Claude 3.5 Sonnet** is used for optimal performance/cost balance
- Typical cost: ~$0.0003 per test step
- Cache is used where possible to minimize redundant API calls
- Fallback to rule-based interpretation when API is unavailable

## Monitoring and Debugging

### View Claude's Interpretation
Check test execution results to see how Claude interpreted each step:

```json
{
  "step_number": 1,
  "description": "Navigate to example.com",
  "status": "passed",
  "details": "Navigated to https://example.com (Claude interpreted)"
}
```

### Enable Debug Logging
Set environment variable for detailed logging:

```bash
DEBUG_CLAUDE_INTERPRETATION=true
```

### Screenshot Directory
Screenshots are saved to: `/app/screenshots/`
View them with:
```bash
docker exec cc-test-scheduler-worker ls -la /app/screenshots/
```

## Comparison: Rule-Based vs Claude AI

### Rule-Based (Previous)
```python
# "Click the submit button"
if "click" in description.lower():
    if "submit" in description.lower():
        selector = "button[type='submit']"
        await page.click(selector)
```
**Limitations**: Only matches predefined patterns

### Claude AI (Current)
```python
# "Click the submit button"
# Claude analyzes:
# - Intent: Click action
# - Target: Submit button
# - Context: Current page structure
# - Strategy: Try multiple selector approaches if needed
```
**Advantages**: Understands intent, handles variations, adapts to context

## Writing Effective Test Steps

### ✅ Good Examples
- "Click the login button" → Clear, specific action
- "Enter password123 in the password field" → Explicit value and field
- "Wait for the dashboard to load" → Clear success criteria
- "Navigate to the settings page" → Specific destination

### ❌ Avoid
- "Do the login thing" → Too vague
- "Click stuff" → Lacks specificity
- "Fix the form" → Not an actionable test step

## Troubleshooting

### Claude API Not Working
**Symptom**: Tests use rule-based fallback
**Solution**:
1. Check API key is set correctly
2. Verify API key has credits
3. Check network connectivity
4. Review logs: `docker compose logs scheduler-worker`

### High API Costs
**Symptom**: Unexpected usage
**Solutions**:
1. Use specific, unambiguous instructions
2. Enable caching for repeated steps
3. Consider rule-based fallback for simple operations

### Incorrect Interpretation
**Symptom**: Claude misunderstands intent
**Solutions**:
1. Rephrase the step more explicitly
2. Add more context to the description
3. Use technical terms when appropriate (button, input, etc.)

## Future Enhancements

Planned improvements:
- 🎯 **Visual Understanding**: Claude will analyze page screenshots
- 🧪 **Test Generation**: Claude will suggest test cases based on user stories
- 📊 **Smart Reporting**: Claude will analyze failures and suggest fixes
- 🔄 **Self-Healing**: Claude will automatically adapt to UI changes

## Support

For issues or questions:
1. Check logs: `docker compose logs scheduler-worker --tail=50`
2. Review test execution results in the dashboard
3. Consult Claude API documentation
4. Open an issue on GitHub

## License

This integration uses Anthropic's Claude API. Separate API terms and costs apply.
