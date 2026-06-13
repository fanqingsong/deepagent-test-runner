"""
Simple Result Types - Usage Examples

This file demonstrates how to use the simple result wrapper types in service layers.
"""

from app.core.simple_result_types import (
    success, error, not_found, validation_error, permission_denied,
    service_success, service_error, service_not_found,
    service_validation_error, service_permission_denied,
    fold, map_result, get_or_else, get_or_raise,
    Success, Error, ServiceSuccess, ServiceError
)


# Example 1: Basic Service Function
def get_user_by_id(user_id: int) -> ServiceSuccess:
    """Example service function returning success."""
    user_data = {
        "id": user_id,
        "name": "John Doe",
        "email": "john@example.com"
    }
    return service_success(user_data)


def handle_get_user():
    """Example handling service result."""
    result = get_user_by_id(123)

    if result.is_success():
        user = result.get_data()
        print(f"Found user: {user['name']}")
        return user
    else:
        print(f"Error: {result.get_error()}")
        return None


# Example 2: Error Handling
def get_user_not_found(user_id: int) -> ServiceError:
    """Example service function returning error."""
    return service_not_found("User", str(user_id))


def handle_error_result():
    """Example handling error result."""
    result = get_user_not_found(999)

    if result.is_error():
        print(f"User not found: {result.get_error()}")
        print(f"HTTP Status: {result.get_http_status()}")
        print(f"Details: {result.details}")


# Example 3: Validation
def validate_user_data(data: dict) -> ServiceSuccess:
    """Example validation function."""
    errors = {}

    if not data.get("email"):
        errors["email"] = "Email is required"

    if not data.get("name"):
        errors["name"] = "Name is required"

    if errors:
        return service_validation_error("Validation failed", errors)

    return service_success(data)


def handle_validation():
    """Example handling validation result."""
    # Valid data
    valid_data = {"email": "test@example.com", "name": "Test User"}
    result = validate_user_data(valid_data)

    if result.is_success():
        print("Validation passed!")
    else:
        print(f"Validation failed: {result.get_error()}")

    # Invalid data
    invalid_data = {"email": "", "name": ""}
    result = validate_user_data(invalid_data)

    if result.is_error():
        print(f"Validation errors: {result.details['field_errors']}")


# Example 4: Using Helper Functions
def check_permission(user_id: int, resource: str) -> ServiceSuccess:
    """Example permission check."""
    if user_id != 1:
        return service_permission_denied("Admin access required", "admin:read")

    return service_success({"granted": True, "resource": resource})


def handle_permission():
    """Example handling permission result."""
    result = check_permission(2, "admin_panel")

    if result.is_error():
        print(f"Permission denied: {result.get_error()}")
        print(f"Required permission: {result.details.get('required_permission')}")


# Example 5: Using Utility Functions
def process_data_chain():
    """Example using map_result for chaining operations."""

    def validate(data):
        if data < 0:
            return error("Negative values not allowed")
        return success(data)

    def double(value):
        return success(value * 2)

    def add_ten(value):
        return success(value + 10)

    # Chain operations
    result = success(5)
    result = map_result(result, double)
    result = map_result(result, add_ten)

    if result.is_success():
        print(f"Chain result: {result.get_data()}")  # Should be 20
    else:
        print(f"Chain failed: {result.get_error()}")


# Example 6: Using Fold
def use_fold_example():
    """Example using fold for pattern matching."""

    def process_result(result):
        return fold(
            result,
            on_success=lambda data: f"Success with data: {data}",
            on_error=lambda error: f"Error occurred: {error}"
        )

    success_result = success("test data")
    error_result = error("something went wrong")

    print(process_result(success_result))
    print(process_result(error_result))


# Example 7: Error Recovery
def error_recovery_example():
    """Example showing error recovery patterns."""

    def risky_operation(value):
        if value < 0:
            return error("Negative value")
        return success(value * 2)

    def recover(result):
        if result.is_error():
            return success(0)  # Default recovery value
        return result

    # Success case
    result1 = risky_operation(5)
    result1 = recover(result1)
    print(f"Recovered success: {result1.get_data()}")  # 10

    # Failure case with recovery
    result2 = risky_operation(-1)
    result2 = recover(result2)
    print(f"Recovered error: {result2.get_data()}")  # 0


# Example 8: Real Service Pattern
class UserService:
    """Example service class using result types."""

    def get_user(self, user_id: int) -> ServiceSuccess:
        """Get user by ID."""
        # Simulate database lookup
        if user_id <= 0:
            return service_not_found("User", str(user_id))

        user_data = {"id": user_id, "name": f"User {user_id}"}
        return service_success(user_data)

    def create_user(self, data: dict) -> ServiceSuccess:
        """Create new user."""
        # Validate
        if not data.get("email"):
            return service_validation_error("Email required", {"email": "Missing"})

        if not data.get("name"):
            return service_validation_error("Name required", {"name": "Missing"})

        # Simulate creation
        new_user = {"id": 123, **data}
        return service_success(new_user, status="created")

    def update_user(self, user_id: int, data: dict) -> ServiceSuccess:
        """Update user."""
        # Check if user exists
        if user_id <= 0:
            return service_not_found("User", str(user_id))

        # Simulate update
        updated_user = {"id": user_id, **data}
        return service_success(updated_user, status="updated")

    def delete_user(self, user_id: int) -> ServiceSuccess:
        """Delete user."""
        # Check permission
        if user_id == 1:
            return service_permission_denied("Cannot delete admin user", "user:delete")

        # Simulate deletion
        return service_success({"deleted": True, "id": user_id})


def example_service_usage():
    """Example using the UserService."""
    service = UserService()

    # Create user
    create_result = service.create_user({"email": "test@example.com", "name": "Test"})
    if create_result.is_success():
        print(f"User created: {create_result.get_data()}")
    else:
        print(f"Create failed: {create_result.get_error()}")

    # Get user
    get_result = service.get_user(123)
    if get_result.is_success():
        user = get_result.get_data()
        print(f"Found user: {user['name']}")

    # Not found case
    not_found_result = service.get_user(-1)
    if not_found_result.is_error():
        print(f"Not found: {not_found_result.get_error()}")

    # Permission denied
    delete_result = service.delete_user(1)
    if delete_result.is_error():
        print(f"Permission denied: {delete_result.get_error()}")


# Example 9: Combining Multiple Results
def combine_results_example():
    """Example combining multiple service results."""

    def get_user_data(user_id):
        return service_success({"id": user_id, "name": f"User {user_id}"})

    def get_user_posts(user_id):
        return service_success([
            {"id": 1, "title": "Post 1"},
            {"id": 2, "title": "Post 2"}
        ])

    def get_user_stats(user_id):
        return service_success({"posts_count": 2, "likes": 10})

    # Combine results
    user_id = 123
    user_result = get_user_data(user_id)
    posts_result = get_user_posts(user_id)
    stats_result = get_user_stats(user_id)

    if all([user_result.is_success(), posts_result.is_success(), stats_result.is_success()]):
        combined_data = {
            "user": user_result.get_data(),
            "posts": posts_result.get_data(),
            "stats": stats_result.get_data()
        }
        print(f"Combined data: {combined_data}")
        return service_success(combined_data)
    else:
        errors = [r for r in [user_result, posts_result, stats_result] if r.is_error()]
        return service_error(f"Multiple errors: {len(errors)}")


# Example 10: Using with API Routes
def api_handler_example():
    """Example showing how to use with API routes."""

    def api_get_user(user_id: int):
        """API handler for getting user."""
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

    # Success response
    success_response = api_get_user(123)
    print(f"Success response: {success_response}")

    # Error response
    error_response = api_get_user(-1)
    print(f"Error response: {error_response}")


if __name__ == "__main__":
    print("=" * 60)
    print("SIMPLE RESULT TYPES - USAGE EXAMPLES")
    print("=" * 60)

    print("\n1. Basic Service Function:")
    handle_get_user()

    print("\n2. Error Handling:")
    handle_error_result()

    print("\n3. Validation:")
    handle_validation()

    print("\n4. Permission Check:")
    handle_permission()

    print("\n5. Data Processing Chain:")
    process_data_chain()

    print("\n6. Using Fold:")
    use_fold_example()

    print("\n7. Error Recovery:")
    error_recovery_example()

    print("\n8. Real Service Pattern:")
    example_service_usage()

    print("\n9. Combining Results:")
    combine_results_example()

    print("\n10. API Handler Pattern:")
    api_handler_example()

    print("\n" + "=" * 60)
    print("EXAMPLES COMPLETED")
    print("=" * 60)
