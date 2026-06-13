# External Dependency Abstraction

This document describes the external dependency abstraction layer that enables flexible integration of LLM providers and browser automation tools following SOLID principles.

## Overview

The abstraction layer provides interfaces for:

1. **LLM Clients** - Support multiple LLM providers (GLM, OpenAI, Anthropic, etc.)
2. **Browser Automation** - Support multiple browser tools (Playwright, Puppeteer, Selenium)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                        │
│  (Services, Workflows, Activities)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                            │
│  ILLMClient | IBrowserAutomation                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Implementation Layer                         │
│  GLMClient | MockLLMClient                                   │
│  PlaywrightAutomation | MockBrowserAutomation                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Dependencies                       │
│  GLM API | OpenAI API | Anthropic API                         │
│  Playwright | Puppeteer | Selenium                           │
└─────────────────────────────────────────────────────────────┘
```

## LLM Client Interface

### Interface Definition

File: `app/core/interfaces/llm_client_interface.py`

```python
from app.core.interfaces.llm_client_interface import ILLMClient, LLMResponse, LLMMessage
```

### Key Methods

#### generate_response
Generate a response from the LLM.

```python
response = await llm_client.generate_response(
    prompt="Generate a test case for user login",
    model="glm-4-plus",
    temperature=0.1,
    max_tokens=4096
)

print(response.content)  # Generated text
print(response.tokens_used)  # Token consumption
print(response.duration_ms)  # Generation time
```

#### generate_chat_response
Generate a response using chat-style messages.

```python
messages = [
    LLMMessage(role="system", content="You are a test case generator"),
    LLMMessage(role="user", content="Generate test for login flow")
]

response = await llm_client.generate_chat_response(
    messages=messages,
    model="glm-4-plus"
)
```

#### generate_structured_response
Generate a response matching a JSON schema.

```python
schema = {
    "type": "object",
    "properties": {
        "test_name": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}}
    }
}

result = await llm_client.generate_structured_response(
    prompt="Generate a test case",
    schema=schema
)
```

#### stream_response
Stream a response chunk by chunk.

```python
async for chunk in llm_client.stream_response("Tell me a story"):
    print(chunk.content, end="")
    if chunk.is_complete:
        print("\n[Stream complete]")
```

### Implementations

#### GLMClient

Production implementation for GLM (BigModel) API.

```python
from app.core.llm.glm_client import GLMClient

client = GLMClient(
    api_key="your-api-key",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    model="glm-4-plus"
)

response = await client.generate_response("Hello, GLM!")
```

#### MockLLMClient

Mock implementation for testing.

```python
from app.core.llm.mock_llm_client import MockLLMClient

# No actual API calls, deterministic responses
client = MockLLMClient(
    model="mock-model",
    delay_ms=100,  # Simulate API delay
    simulate_errors=False  # Enable for error testing
)

response = await client.generate_response("Test")
```

### Configuration

Environment variables:

```bash
# LLM Configuration
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-plus
```

### DI Container Registration

```python
from app.core.container import Container

container = Container()

# Production: GLM client
container.config.interfaces.use_mocks = False

# Testing: Mock client
container.config.interfaces.use_mocks = True

# Inject into services
llm_client = container.llm_client()
```

## Browser Automation Interface

### Interface Definition

File: `app/core/interfaces/browser_automation_interface.py`

```python
from app.core.interfaces.browser_automation_interface import (
    IBrowserAutomation,
    BrowserType,
    BrowserConfig
)
```

### Key Methods

#### start_browser / stop_browser
Manage browser lifecycle.

```python
await browser.start_browser(
    browser_type=BrowserType.CHROMIUM,
    config=BrowserConfig(headless=True, timeout=30000)
)

# ... perform operations ...

await browser.stop_browser()
```

#### navigate
Navigate to a URL.

```python
await browser.navigate("https://example.com")
```

#### execute_script
Execute a Playwright script.

```python
result = await browser.execute_script(
    script="await page.click('#button')",
    timeout=5000
)

print(result.status)  # "passed" or "failed"
print(result.step_results)  # List of step results
```

#### take_screenshot
Capture a screenshot.

```python
screenshot = await browser.take_screenshot(full_page=True)
# Returns bytes
```

#### get_page_content
Extract page content.

```python
content = await browser.get_page_content()

print(content.url)  # Page URL
print(content.title)  # Page title
print(content.links)  # List of links
print(content.forms)  # List of forms
```

### Implementations

#### PlaywrightAutomation

Production implementation using Playwright.

```python
from app.core.browser.playwright_automation import PlaywrightAutomation

browser = PlaywrightAutomation(
    config=BrowserConfig(
        headless=True,
        timeout=30000,
        viewport={"width": 1280, "height": 720}
    )
)

async with browser:
    await browser.navigate("https://example.com")
    content = await browser.get_page_content()
```

#### MockBrowserAutomation

Mock implementation for testing.

```python
from app.core.browser.mock_browser_automation import MockBrowserAutomation

browser = MockBrowserAutomation(
    config=BrowserConfig(),
    delay_ms=100,
    simulate_errors=False
)

await browser.start_browser()
await browser.navigate("https://example.com")
```

### Configuration

```python
from app.core.config import settings

# Playwright settings
PLAYWRIGHT_HEADLESS = True
TEST_TIMEOUT = 30000  # milliseconds
SCREENSHOT_DIR = "screenshots"
```

### DI Container Registration

```python
from app.core.container import Container

container = Container()

# Production: Playwright
container.config.interfaces.use_mocks = False

# Testing: Mock
container.config.interfaces.use_mocks = True

# Inject into services
browser = container.browser_automation()
```

## Usage Examples

### In Services

#### LLM Service

```python
from app.core.interfaces.llm_client_interface import ILLMClient
from app.services.llm_client_v2 import LLMClient

class TestCaseGenerator:
    def __init__(self, llm_client: ILLMClient):
        self.llm_client = llm_client

    async def generate_test_case(self, prompt: str) -> str:
        response = await self.llm_client.generate_response(prompt)
        return response.content
```

#### Browser Service

```python
from app.core.interfaces.browser_automation_interface import IBrowserAutomation
from app.services.script_validation_service_v2 import ScriptValidationService

class ScriptValidator:
    def __init__(self, browser: IBrowserAutomation):
        self.browser = browser

    async def validate_script(self, script: str) -> bool:
        await self.browser.start_browser()
        try:
            result = await self.browser.execute_script(script)
            return result.status == "passed"
        finally:
            await self.browser.stop_browser()
```

### In Tests

#### Unit Tests with Mocks

```python
import pytest
from app.core.llm.mock_llm_client import MockLLMClient

@pytest.mark.asyncio
async def test_test_case_generator():
    # Use mock client
    mock_client = MockLLMClient(delay_ms=0)
    generator = TestCaseGenerator(llm_client=mock_client)

    result = await generator.generate_test_case("Generate login test")

    assert "login" in result.lower()
```

#### Integration Tests with Real Implementation

```python
import pytest
from app.core.llm.glm_client import GLMClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_test_case_generator_integration():
    # Use real GLM client
    real_client = GLMClient()
    generator = TestCaseGenerator(llm_client=real_client)

    result = await generator.generate_test_case("Generate login test")

    assert "login" in result.lower()
```

## Migration Guide

### From Direct LLM Usage

**Before:**
```python
from app.core.agent_config import get_llm

llm = get_llm()
response = await llm.agenerate([[HumanMessage(content=prompt)]])
content = response.generations[0][0].text
```

**After:**
```python
from app.core.interfaces.llm_client_interface import ILLMClient

response = await llm_client.generate_response(prompt)
content = response.content
```

### From Direct Playwright Usage

**Before:**
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://example.com")
```

**After:**
```python
from app.core.interfaces.browser_automation_interface import IBrowserAutomation

await browser.start_browser()
await browser.navigate("https://example.com")
```

## Testing Strategies

### 1. Unit Tests
Use mock implementations to test business logic in isolation.

```python
def test_service_logic():
    mock_client = MockLLMClient()
    service = MyService(llm_client=mock_client)
    # Test service logic without external dependencies
```

### 2. Integration Tests
Use real implementations to test integration with external services.

```python
@pytest.mark.integration
async def test_real_llm():
    real_client = GLMClient()
    response = await real_client.generate_response("Test")
    assert response.content
```

### 3. Contract Tests
Verify implementations adhere to interface contracts.

```python
def test_implementation_contract():
    client = GLMClient()
    # Verify all interface methods are implemented
    assert hasattr(client, 'generate_response')
    assert callable(client.generate_response)
```

## Benefits

### 1. Flexibility
- Easily switch between LLM providers
- Easily switch between browser automation tools
- No changes to application code

### 2. Testability
- Mock implementations for unit tests
- No external dependencies in tests
- Deterministic test behavior

### 3. Maintainability
- Clear interface contracts
- Centralized error handling
- Consistent API across providers

### 4. Performance
- Can add caching at interface level
- Can add monitoring at interface level
- Can optimize per implementation

## Best Practices

1. **Always depend on interfaces, not implementations**
   ```python
   # Good
   def __init__(self, llm_client: ILLMClient):

   # Bad
   def __init__(self, llm_client: GLMClient):
   ```

2. **Use dependency injection**
   ```python
   # Good
   service = MyService(llm_client=container.llm_client())

   # Bad
   from app.core.llm.glm_client import GLMClient
   service = MyService(llm_client=GLMClient())
   ```

3. **Configure implementation via DI container**
   ```python
   # Good
   container.config.interfaces.use_mocks = True

   # Bad
   if settings.TESTING:
       client = MockLLMClient()
   else:
       client = GLMClient()
   ```

4. **Handle exceptions appropriately**
   ```python
   from app.core.interfaces.llm_client_interface import LLMTimeoutError

   try:
       response = await llm_client.generate_response(prompt)
   except LLMTimeoutError:
       # Handle timeout specifically
       pass
   ```

## Extending the Abstraction

### Adding a New LLM Provider

1. Implement the interface:
```python
from app.core.interfaces.llm_client_interface import ILLMClient

class OpenAIClient(ILLMClient):
    async def generate_response(self, prompt: str, **kwargs) -> LLMResponse:
        # OpenAI-specific implementation
        pass

    # Implement other interface methods...
```

2. Register in DI container:
```python
def _create_llm_client(use_mocks: bool = False, provider: str = "glm"):
    if provider == "openai":
        return OpenAIClient()
    elif provider == "glm":
        return GLMClient()
    else:
        return MockLLMClient()

container.llm_client = providers.Factory(
    _create_llm_client,
    provider=config.llm.provider
)
```

### Adding a New Browser Automation Tool

1. Implement the interface:
```python
from app.core.interfaces.browser_automation_interface import IBrowserAutomation

class SeleniumAutomation(IBrowserAutomation):
    async def start_browser(self, **kwargs) -> None:
        # Selenium-specific implementation
        pass

    # Implement other interface methods...
```

2. Register in DI container:
```python
container.browser_automation = providers.Factory(
    _create_browser_automation,
    provider=config.browser.provider
)
```

## Troubleshooting

### Issue: "Container not initialized"
**Solution:** Ensure `init_container()` is called during application startup.

### Issue: "Interface method not implemented"
**Solution:** Verify all abstract methods are implemented in concrete classes.

### Issue: "Mock returns unexpected results"
**Solution:** Configure MockLLMClient with appropriate `response_mode` and custom templates.

### Issue: "DI container doesn't find provider"
**Solution:** Ensure provider is registered in container and modules are wired.

## Further Reading

- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Interface Segregation Principle](https://en.wikipedia.org/wiki/Interface_segregation_principle)
- [dependency_injector Documentation](https://dependency-injector.readthedocs.io/)
