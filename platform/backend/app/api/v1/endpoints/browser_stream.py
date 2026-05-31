"""
WebSocket endpoint for real-time browser stream during test execution.

Subscribes to Redis pub/sub channel `browser_stream:{job_id}` and forwards
frame metadata (screenshot path, url, title) to connected WebSocket clients.
"""

import json
import logging
import os

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)

LIVE_SCREENSHOT_PATH = "/app/screenshots/{job_id}/live.jpg"


async def browser_stream_handler(websocket: WebSocket, job_id: str) -> None:
    """Handle WebSocket connection for live browser stream."""
    await websocket.accept()
    logger.info("Browser stream WebSocket connected for job %s", job_id)

    # Send initial frame if live.jpg already exists (missed while not connected)
    live_path = LIVE_SCREENSHOT_PATH.format(job_id=job_id)
    if os.path.exists(live_path):
        try:
            initial = json.dumps({
                "type": "frame",
                "path": f"/screenshots/{job_id}/live.jpg",
                "url": "",
                "title": "",
                "timestamp": 0,
            })
            await websocket.send_text(initial)
        except Exception:
            pass

    redis_url = settings.REDIS_URL
    channel_name = f"browser_stream:{job_id}"

    r = aioredis.from_url(redis_url)
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe(channel_name)

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)

    except WebSocketDisconnect:
        logger.info("Browser stream WebSocket disconnected for job %s", job_id)
    except Exception as e:
        logger.warning("Browser stream error for job %s: %s", job_id, e)
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
        await r.close()
        logger.info("Browser stream cleaned up for job %s", job_id)
