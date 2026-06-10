#!/usr/bin/env python3
"""
Restart Monitoring Schedule Script

Checks if the monitoring schedule exists and restarts it if needed.
Run this script from the backend directory.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/app')

from app.temporal.client import (
    get_monitoring_schedule_status,
    start_monitoring_schedule,
    stop_monitoring_schedule,
)


async def main():
    print("Checking monitoring schedule status...")

    # Check current status
    status = await get_monitoring_schedule_status()
    print(f"Current status: {status}")

    if not status.get("exists"):
        print("Schedule does not exist, creating new one...")
        result = await start_monitoring_schedule()
        print(f"Created: {result}")
    else:
        print("Schedule exists, recreating...")
        await stop_monitoring_schedule()
        result = await start_monitoring_schedule()
        print(f"Recreated: {result}")

    # Verify
    new_status = await get_monitoring_schedule_status()
    print(f"New status: {new_status}")


if __name__ == "__main__":
    asyncio.run(main())
