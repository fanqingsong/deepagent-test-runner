import pytest
from datetime import timezone, datetime

from app.services.schedule_manager import ScheduleManager
from app.models.schedule import Schedule


@pytest.mark.asyncio
async def test_get_active_schedules(db_session):
    """Test retrieving active schedules"""
    active_schedule = Schedule(
        name="Active Schedule",
        schedule_type="single",
        test_definition_id=1,
        cron_expression="0 9 * * *",
        is_active=True
    )

    inactive_schedule = Schedule(
        name="Inactive Schedule",
        schedule_type="single",
        test_definition_id=2,
        cron_expression="0 10 * * *",
        is_active=False
    )

    db_session.add(active_schedule)
    db_session.add(inactive_schedule)
    await db_session.commit()

    manager = ScheduleManager(db_session)
    active_schedules = await manager.get_active_schedules()

    assert len(active_schedules) == 1
    assert active_schedules[0].name == "Active Schedule"


def test_validate_cron_valid():
    """Test cron validation with valid expressions"""
    manager = ScheduleManager(None)

    assert manager.validate_cron("0 9 * * *") is True
    assert manager.validate_cron("*/5 * * * *") is True
    assert manager.validate_cron("0 9 * * 1") is True


def test_validate_cron_invalid():
    """Test cron validation with invalid expressions"""
    manager = ScheduleManager(None)

    assert manager.validate_cron("invalid") is False
    assert manager.validate_cron("60 * * * *") is False


def test_parse_cron_expression_invalid():
    """Test parsing invalid cron expression"""
    manager = ScheduleManager(None)

    with pytest.raises(ValueError):
        manager.parse_cron_expression("0 9 * *")


@pytest.mark.asyncio
async def test_update_next_run_time(db_session):
    """Test updating next run time"""
    schedule = Schedule(
        name="Test Schedule",
        schedule_type="single",
        test_definition_id=1,
        cron_expression="0 9 * * *",
        is_active=True
    )

    db_session.add(schedule)
    await db_session.commit()

    manager = ScheduleManager(db_session)
    await manager.update_next_run_time(schedule)

    assert schedule.next_run_time is not None
    assert schedule.next_run_time > datetime.now(timezone.utc)
