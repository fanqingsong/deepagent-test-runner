---
name: playwright-expertise
description: Playwright async API patterns for browser automation test scripts — selectors, waits, assertions, form interactions, error handling
---

# Playwright Test Script Expertise

## Script Structure

All scripts must follow this signature:
```python
async def run_test(page: Page) -> dict:
    # ... test steps ...
    return {"status": "passed"}
    # or: return {"status": "failed", "error": "reason"}
```

## Selector Priority

1. **ID selector** (preferred): `#login-btn`, `#email-input`
2. **Name attribute**: `[name="username"]`, `[name="password"]`
3. **Data-testid**: `[data-testid="submit-button"]`
4. **Text content** (last resort): `text=Login`, `text=Submit`

Never use brittle selectors like `nth-child`, positional XPaths, or full DOM paths.

## Wait Patterns

Always wait before interacting:
```python
await page.wait_for_selector("#login-btn", state="visible", timeout=15000)
await page.click("#login-btn")
```

After navigation:
```python
await page.goto(url, wait_until="domcontentloaded")
await page.wait_for_load_state("networkidle")
```

Never use `time.sleep()` or `page.wait_for_timeout()` for synchronization.

## Assertion Patterns

Use Playwright's expect:
```python
from playwright.async_api import expect

await expect(page.locator("#welcome")).to_be_visible(timeout=10000)
await expect(page).to_have_title(re.compile("Dashboard"))
```

## Common Interactions

### Text Input
```python
await page.fill("#email", "user@example.com")
```

### Button Click
```python
await page.wait_for_selector("#submit", state="visible", timeout=15000)
await page.click("#submit")
```

### Dropdown
```python
await page.select_option("#country", value="CN")
```

### Checkbox
```python
await page.check("#agree-terms")
```

### File Upload
```python
await page.set_input_files("#file-input", "/path/to/file.pdf")
```

## Error Handling

Wrap each step in try/except:
```python
try:
    await page.wait_for_selector("#result", state="visible", timeout=15000)
    text = await page.text_content("#result")
    if "success" not in text.lower():
        return {"status": "failed", "error": f"Unexpected result: {text}"}
except Exception as e:
    return {"status": "failed", "error": f"Step failed: {str(e)}"}
```

## Multi-step Test Pattern

```python
async def run_test(page: Page) -> dict:
    try:
        # Step 1: Navigate
        await page.goto("https://example.com/login", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # Step 2: Fill form
        await page.wait_for_selector("#email", state="visible", timeout=15000)
        await page.fill("#email", "test@example.com")
        await page.fill("#password", "testpass123")

        # Step 3: Submit
        await page.click("#login-btn")
        await page.wait_for_load_state("networkidle")

        # Step 4: Verify
        await page.wait_for_selector("#dashboard", state="visible", timeout=15000)
        return {"status": "passed"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
```

## Security Rules

- Never import `os`, `subprocess`, `sys`, `shutil`, `socket`, `http`
- Never use `exec()`, `eval()`, `compile()`
- Only use `page.evaluate()` for reading data, never for side effects
- Always use `timeout=15000` for `wait_for_selector` calls
