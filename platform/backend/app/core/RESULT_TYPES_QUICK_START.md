# Simple Result Types - Quick Start Guide

## 🚀 Quick Import

```python
from app.core.simple_result_types import (
    # Basic types
    success, error, Success, Error,
    # Helpers
    not_found, validation_error, permission_denied,
    # Service types
    service_success, service_error, ServiceSuccess, ServiceError,
    # Service helpers
    service_not_found, service_validation_error, service_permission_denied,
    # Utilities
    fold, map_result, get_or_else, get_or_raise,
    # Type guards
    is_success, is_error
)
```

## 📝 Basic Usage

### Success Result
```python
result = success(data={"id": 123, "name": "Test"})
if result.is_success():
    data = result.get_data()
```

### Error Result
```python
result = error("Operation failed", code="OPERATION_FAILED")
if result.is_error():
    error_msg = result.get_error()
```

## 🔧 Common Helper Functions

### Not Found
```python
result = not_found("User", "123")
# Returns: Error with code "NOT_FOUND", HTTP 404
```

### Validation Error
```python
result = validation_error("Invalid data", {"email": "Required"})
# Returns: Error with code "VALIDATION_ERROR", HTTP 400
```

### Permission Denied
```python
result = permission_denied("Access denied", "admin:write")
# Returns: Error with code "PERMISSION_DENIED", HTTP 403
```

## 🎯 Service Layer Usage

### Basic Service Pattern
```python
class UserService:
    def get_user(self, user_id: int) -> ServiceSuccess:
        if user_id <= 0:
            return service_not_found("User", str(user_id))
        
        user_data = {"id": user_id, "name": f"User {user_id}"}
        return service_success(user_data)
    
    def create_user(self, data: dict) -> ServiceSuccess:
        if not data.get("email"):
            return service_validation_error("Email required", {"email": "Missing"})
        
        return service_success({"id": 123, **data})
```

### Using Service Results
```python
service = UserService()
result = service.get_user(123)

if result.is_success():
    user = result.get_data()
    print(f"Found: {user['name']}")
else:
    print(f"Error: {result.get_error()}")
    print(f"HTTP Status: {result.get_http_status()}")
```

## 🔄 Utility Functions

### Pattern Matching with Fold
```python
def handle_result(result):
    return fold(
        result,
        on_success=lambda data: f"✓ Success: {data}",
        on_error=lambda error: f"✗ Error: {error}"
    )

print(handle_result(success(42)))   # ✓ Success: 42
print(handle_result(error("fail"))) # ✗ Error: fail
```

### Transform with Map
```python
result = map_result(success(5), lambda x: x * 2)
# Success with data = 10

result = map_result(error("fail"), lambda x: x * 2)
# Error (unchanged)
```

### Safe Data Extraction
```python
# Get data or default
value = get_or_else(success(42), default=0)    # 42
value = get_or_else(error("err"), default=0)   # 0

# Get data or raise exception
value = get_or_raise(success(42))              # 42
value = get_or_raise(error("err"))             # Raises ValueError
```

## 🌐 HTTP Status Mapping

Service errors automatically map to HTTP status codes:

```python
service_not_found("User", "123")           # 404
service_validation_error("Invalid", {})      # 400
service_permission_denied("Denied", "admin") # 403
service_error("Conflict", "CONFLICT")       # 409
service_error("Failed", "OPERATION_FAILED") # 500
```

## 🎨 Type Safety

### Generic Types
```python
# Typed success results
int_result: Success[int] = Success(data=42)
str_result: Success[str] = Success(data="test")
dict_result: Success[Dict[str, Any]] = Success(data={"key": "value"})

# Typed service results
service_result: ServiceSuccess[User] = service_success(user_data)
```

### Type Guards
```python
result: Result = success("test")

if is_success(result):
    # Type narrowed to Success
    data: str = result.get_data()

if is_error(result):
    # Type narrowed to Error
    error: str = result.get_error()
```

## 🔗 API Integration

### Simple API Handler
```python
def api_get_user(user_id: int):
    service = UserService()
    result = service.get_user(user_id)
    
    if result.is_success():
        return {
            "status": "success",
            "data": result.get_data(),
            "http_status": 200
        }
    else:
        return {
            "status": "error",
            "message": result.get_error(),
            "http_status": result.get_http_status()
        }
```

## 🛠️ Common Patterns

### Error Recovery
```python
def risky_operation(value):
    if value < 0:
        return error("Negative value")
    return success(value * 2)

def recover(result):
    if result.is_error():
        return success(0)  # Recovery value
    return result

result = risky_operation(-1)
result = recover(result)
# Now has data = 0
```

### Chaining Operations
```python
def process_chain():
    result = success(5)
    result = map_result(result, lambda x: x * 2)
    result = map_result(result, lambda x: x + 10)
    # Success with data = 20
    return result
```

### Combining Results
```python
def combine_service_results(user_id):
    user = get_user(user_id)
    posts = get_user_posts(user_id)
    stats = get_user_stats(user_id)
    
    if all([user.is_success(), posts.is_success(), stats.is_success()]):
        return service_success({
            "user": user.get_data(),
            "posts": posts.get_data(),
            "stats": stats.get_data()
        })
    else:
        return service_error("Failed to load data")
```

## 📚 Complete Example

```python
from app.core.simple_result_types import *

class BlogService:
    def create_post(self, user_id: int, post_data: dict) -> ServiceSuccess:
        # Validate user exists
        if user_id <= 0:
            return service_not_found("User", str(user_id))
        
        # Validate post data
        if not post_data.get("title"):
            return service_validation_error("Title required", {"title": "Missing"})
        
        if not post_data.get("content"):
            return service_validation_error("Content required", {"content": "Missing"})
        
        # Check permissions
        if not self._can_create_post(user_id):
            return service_permission_denied("Premium required", "post:create")
        
        # Create post
        new_post = {
            "id": 456,
            "user_id": user_id,
            "title": post_data["title"],
            "content": post_data["content"],
            "created_at": "2024-01-01"
        }
        
        return service_success(new_post, status="created")

# Usage
service = BlogService()
result = service.create_post(123, {"title": "My Post", "content": "Hello"})

if result.is_success():
    post = result.get_data()
    print(f"✓ Post created: {post['id']}")
else:
    print(f"✗ Error: {result.get_error()}")
    print(f"   HTTP Status: {result.get_http_status()}")
```

## 🎯 Best Practices

1. **Always return typed results**: Use `ServiceSuccess[T]` for type safety
2. **Use helper functions**: Prefer `service_not_found()` over manual construction
3. **Chain operations**: Use `map_result()` for data transformations
4. **Handle errors gracefully**: Use `fold()` for pattern matching
5. **Check HTTP status**: Use `get_http_status()` for API responses
6. **Type guards**: Use `is_success()`/`is_error()` for type narrowing

## 🔍 Debugging

### Check Result Type
```python
if result.is_success():
    print("Success!")
elif result.is_error():
    print(f"Error: {result.get_error()}")
```

### Get Full Error Details
```python
if isinstance(result, ServiceError):
    print(f"Error Code: {result.error_code}")
    print(f"Message: {result.get_error()}")
    print(f"HTTP Status: {result.get_http_status()}")
    print(f"Details: {result.details}")
```

### Serialize for Logging
```python
if isinstance(result, Error):
    error_dict = result.to_dict()
    print(f"Error occurred: {error_dict}")
```

## 📖 Additional Resources

- Full implementation: `/app/core/simple_result_types.py`
- Comprehensive tests: `/app/tests/core/test_simple_result_types.py`
- Usage examples: `/app/core/simple_result_types_examples.py`
- Full documentation: `/app/core/SIMPLE_RESULT_TYPES.md`

---

**Start using result types in your services today!** 🚀
