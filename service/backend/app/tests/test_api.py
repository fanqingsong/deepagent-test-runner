"""
Integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.schemas.test_suites import TestSuiteCreate, TestSuiteUpdate


@pytest.mark.asyncio
async def test_create_test_suite(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a new test suite via API"""
    suite_data = {
        "name": "API Test Suite",
        "description": "Test suite created via API",
        "test_definition_ids": [1, 2, 3, 4],
        "tags": {"category": "api", "priority": "high"}
    }

    response = await async_client.post("/api/v1/test-suites/", json=suite_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Test Suite"
    assert data["description"] == "Test suite created via API"
    assert data["test_definition_ids"] == [1, 2, 3, 4]
    assert data["tags"]["category"] == "api"
    assert data["tags"]["priority"] == "high"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_test_suite_minimal(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a test suite with minimal required fields"""
    suite_data = {
        "name": "Minimal Suite",
        "test_definition_ids": [5, 6]
    }

    response = await async_client.post("/api/v1/test-suites/", json=suite_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Suite"
    assert data["test_definition_ids"] == [5, 6]
    assert data["tags"] == {}  # Default empty dict


@pytest.mark.asyncio
async def test_create_test_suite_validation_error(async_client: AsyncClient):
    """Test creating a test suite with invalid data"""
    # Missing required field: test_definition_ids
    suite_data = {
        "name": "Invalid Suite"
    }

    response = await async_client.post("/api/v1/test-suites/", json=suite_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_test_suites(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing all test suites"""
    # Create test suites
    suite1 = TestSuite(
        name="Suite 1",
        description="First suite",
        test_definition_ids=[1, 2],
        tags={"order": "1"}
    )
    suite2 = TestSuite(
        name="Suite 2",
        description="Second suite",
        test_definition_ids=[3, 4],
        tags={"order": "2"}
    )
    db_session.add(suite1)
    db_session.add(suite2)
    await db_session.commit()

    # List suites
    response = await async_client.get("/api/v1/test-suites/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Check that suites are returned (newest first by creation date)
    suite_names = [suite["name"] for suite in data]
    assert "Suite 1" in suite_names
    assert "Suite 2" in suite_names


@pytest.mark.asyncio
async def test_list_test_suites_pagination(async_client: AsyncClient, db_session: AsyncSession):
    """Test pagination for listing test suites"""
    # Create multiple test suites
    for i in range(5):
        suite = TestSuite(
            name=f"Suite {i}",
            test_definition_ids=[i],
            tags={"index": str(i)}
        )
        db_session.add(suite)
    await db_session.commit()

    # Test skip and limit
    response = await async_client.get("/api/v1/test-suites/?skip=2&limit=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_test_suite(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific test suite"""
    # Create a test suite
    suite = TestSuite(
        name="Get Test Suite",
        description="Suite to retrieve",
        test_definition_ids=[10, 20, 30],
        tags={"type": "retrieval"}
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    # Get the suite
    response = await async_client.get(f"/api/v1/test-suites/{suite.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == suite.id
    assert data["name"] == "Get Test Suite"
    assert data["description"] == "Suite to retrieve"
    assert data["test_definition_ids"] == [10, 20, 30]
    assert data["tags"]["type"] == "retrieval"


@pytest.mark.asyncio
async def test_get_test_suite_not_found(async_client: AsyncClient):
    """Test getting a non-existent test suite"""
    response = await async_client.get("/api/v1/test-suites/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_test_suite(async_client: AsyncClient, db_session: AsyncSession):
    """Test updating a test suite"""
    # Create a test suite
    suite = TestSuite(
        name="Original Name",
        description="Original description",
        test_definition_ids=[1, 2, 3],
        tags={"version": "1"}
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    # Update the suite
    update_data = {
        "name": "Updated Name",
        "description": "Updated description",
        "tags": {"version": "2"}
    }
    response = await async_client.put(f"/api/v1/test-suites/{suite.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == suite.id
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"
    assert data["test_definition_ids"] == [1, 2, 3]  # Unchanged
    assert data["tags"]["version"] == "2"


@pytest.mark.asyncio
async def test_update_test_suite_partial(async_client: AsyncClient, db_session: AsyncSession):
    """Test partial update of a test suite"""
    # Create a test suite
    suite = TestSuite(
        name="Partial Update Suite",
        description="Original",
        test_definition_ids=[1, 2],
        tags={"status": "active"}
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    # Update only name
    update_data = {
        "name": "New Name Only"
    }
    response = await async_client.put(f"/api/v1/test-suites/{suite.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["description"] == "Original"  # Unchanged
    assert data["test_definition_ids"] == [1, 2]  # Unchanged
    assert data["tags"]["status"] == "active"  # Unchanged


@pytest.mark.asyncio
async def test_update_test_suite_not_found(async_client: AsyncClient):
    """Test updating a non-existent test suite"""
    update_data = {
        "name": "This should fail"
    }
    response = await async_client.put("/api/v1/test-suites/99999", json=update_data)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_test_suite(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a test suite"""
    # Create a test suite
    suite = TestSuite(
        name="Delete Me Suite",
        test_definition_ids=[1, 2],
        tags={"lifecycle": "temporary"}
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    suite_id = suite.id

    # Delete the suite
    response = await async_client.delete(f"/api/v1/test-suites/{suite_id}")

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await async_client.get(f"/api/v1/test-suites/{suite_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_test_suite_not_found(async_client: AsyncClient):
    """Test deleting a non-existent test suite"""
    response = await async_client.delete("/api/v1/test-suites/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ==================== Schedules API Tests ====================

@pytest.mark.asyncio
async def test_create_schedule_single(async_client: AsyncClient, db_session: AsyncSession, admin_token: str):
    """Test creating a schedule for a single test"""
    schedule_data = {
        "name": "Single Test Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *",
        "timezone": "UTC",
        "environment_overrides": {"ENV": "test"},
        "is_active": True,
        "allow_concurrent": False,
        "max_retries": 2,
        "retry_interval_seconds": 60
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.post("/api/v1/schedules/", json=schedule_data, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Single Test Schedule"
    assert data["schedule_type"] == "single"
    assert data["test_definition_id"] == 1
    assert data["cron_expression"] == "0 9 * * *"
    assert data["is_active"] is True
    assert data["max_retries"] == 2
    assert "id" in data
    assert "next_run_time" is not None


@pytest.mark.asyncio
async def test_create_schedule_suite(async_client: AsyncClient, db_session: AsyncSession, admin_token: str):
    """Test creating a schedule for a test suite"""
    # First create a test suite
    suite_data = {
        "name": "Test Suite for Schedule",
        "test_definition_ids": [1, 2, 3]
    }
    suite_response = await async_client.post("/api/v1/test-suites/", json=suite_data)
    suite_id = suite_response.json()["id"]

    # Create schedule for suite
    schedule_data = {
        "name": "Suite Schedule",
        "schedule_type": "suite",
        "test_suite_id": suite_id,
        "cron_expression": "0 0 * * 1",
        "timezone": "America/New_York"
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.post("/api/v1/schedules/", json=schedule_data, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["schedule_type"] == "suite"
    assert data["test_suite_id"] == suite_id


@pytest.mark.asyncio
async def test_create_schedule_tag_filter(async_client: AsyncClient, db_session: AsyncSession, admin_token: str):
    """Test creating a schedule with tag filtering"""
    schedule_data = {
        "name": "Tag Filter Schedule",
        "schedule_type": "tag_filter",
        "tag_filter": "priority:high",
        "cron_expression": "*/30 * * * *",
        "timezone": "UTC"
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.post("/api/v1/schedules/", json=schedule_data, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["schedule_type"] == "tag_filter"
    assert data["tag_filter"] == "priority:high"


@pytest.mark.asyncio
async def test_create_schedule_duplicate_name(async_client: AsyncClient):
    """Test creating schedule with duplicate name fails"""
    schedule_data = {
        "name": "Duplicate Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *"
    }

    # Create first schedule
    response1 = await async_client.post("/api/v1/schedules/", json=schedule_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await async_client.post("/api/v1/schedules/", json=schedule_data)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron(async_client: AsyncClient):
    """Test creating schedule with invalid cron expression"""
    schedule_data = {
        "name": "Invalid Cron Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "invalid-cron"
    }

    response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_schedule_missing_target(async_client: AsyncClient):
    """Test creating schedule without required target field"""
    schedule_data = {
        "name": "Missing Target Schedule",
        "schedule_type": "single",
        # Missing test_definition_id
        "cron_expression": "0 9 * * *"
    }

    response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_schedules(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing all schedules"""
    # Create multiple schedules
    for i in range(3):
        schedule_data = {
            "name": f"Schedule {i}",
            "schedule_type": "single",
            "test_definition_id": i + 1,
            "cron_expression": f"{i} 9 * * *"
        }
        await async_client.post("/api/v1/schedules/", json=schedule_data)

    # List schedules
    response = await async_client.get("/api/v1/schedules/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_schedules_with_filters(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing schedules with filters"""
    # Create active and inactive schedules
    active_data = {
        "name": "Active Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *",
        "is_active": True
    }
    await async_client.post("/api/v1/schedules/", json=active_data)

    inactive_data = {
        "name": "Inactive Schedule",
        "schedule_type": "single",
        "test_definition_id": 2,
        "cron_expression": "0 10 * * *",
        "is_active": False
    }
    await async_client.post("/api/v1/schedules/", json=inactive_data)

    # Filter by active status
    response = await async_client.get("/api/v1/schedules/?is_active=true")
    assert response.status_code == 200
    data = response.json()
    for schedule in data:
        assert schedule["is_active"] is True


@pytest.mark.asyncio
async def test_list_schedules_pagination(async_client: AsyncClient):
    """Test schedule list pagination"""
    # Create multiple schedules
    for i in range(5):
        schedule_data = {
            "name": f"Paginated Schedule {i}",
            "schedule_type": "single",
            "test_definition_id": i + 1,
            "cron_expression": f"{i} * * * *"
        }
        await async_client.post("/api/v1/schedules/", json=schedule_data)

    # Get first page
    response = await async_client.get("/api/v1/schedules/?skip=0&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_count_schedules(async_client: AsyncClient):
    """Test counting schedules"""
    # Create schedules
    for i in range(3):
        schedule_data = {
            "name": f"Count Schedule {i}",
            "schedule_type": "single",
            "test_definition_id": i + 1,
            "cron_expression": f"{i} 9 * * *",
            "is_active": i % 2 == 0
        }
        await async_client.post("/api/v1/schedules/", json=schedule_data)

    # Count all
    response = await async_client.get("/api/v1/schedules/count")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] >= 3

    # Count active only
    response = await async_client.get("/api/v1/schedules/count?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_get_schedule_presets(async_client: AsyncClient):
    """Test getting schedule presets"""
    response = await async_client.get("/api/v1/schedules/presets")

    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) > 0

    # Check preset structure
    preset = data["presets"][0]
    assert "type" in preset
    assert "name" in preset
    assert "cron" in preset
    assert "description" in preset


@pytest.mark.asyncio
async def test_get_schedule_by_id(async_client: AsyncClient):
    """Test getting a specific schedule"""
    # Create schedule
    schedule_data = {
        "name": "Get By ID Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *"
    }
    create_response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    schedule_id = create_response.json()["id"]

    # Get schedule
    response = await async_client.get(f"/api/v1/schedules/{schedule_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == schedule_id
    assert data["name"] == "Get By ID Schedule"


@pytest.mark.asyncio
async def test_get_schedule_not_found(async_client: AsyncClient):
    """Test getting non-existent schedule"""
    response = await async_client.get("/api/v1/schedules/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_schedule(async_client: AsyncClient):
    """Test updating a schedule"""
    # Create schedule
    schedule_data = {
        "name": "Original Name",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *",
        "max_retries": 0
    }
    create_response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    schedule_id = create_response.json()["id"]

    # Update schedule
    update_data = {
        "name": "Updated Name",
        "max_retries": 3
    }
    response = await async_client.put(f"/api/v1/schedules/{schedule_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["max_retries"] == 3


@pytest.mark.asyncio
async def test_update_schedule_not_found(async_client: AsyncClient):
    """Test updating non-existent schedule"""
    update_data = {"name": "Updated"}
    response = await async_client.put("/api/v1/schedules/99999", json=update_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_toggle_schedule(async_client: AsyncClient):
    """Test toggling schedule active status"""
    # Create active schedule
    schedule_data = {
        "name": "Toggle Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *",
        "is_active": True
    }
    create_response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    schedule_id = create_response.json()["id"]

    # Deactivate
    response = await async_client.patch(
        f"/api/v1/schedules/{schedule_id}/toggle",
        json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Reactivate
    response = await async_client.patch(
        f"/api/v1/schedules/{schedule_id}/toggle",
        json={"is_active": True}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_delete_schedule(async_client: AsyncClient):
    """Test deleting a schedule"""
    # Create schedule
    schedule_data = {
        "name": "Delete Schedule",
        "schedule_type": "single",
        "test_definition_id": 1,
        "cron_expression": "0 9 * * *"
    }
    create_response = await async_client.post("/api/v1/schedules/", json=schedule_data)
    schedule_id = create_response.json()["id"]

    # Delete schedule
    response = await async_client.delete(f"/api/v1/schedules/{schedule_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await async_client.get(f"/api/v1/schedules/{schedule_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_schedule_not_found(async_client: AsyncClient):
    """Test deleting non-existent schedule"""
    response = await async_client.delete("/api/v1/schedules/99999")
    assert response.status_code == 404
