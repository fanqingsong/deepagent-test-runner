# service/backend/app/temporal/__init__.py
from app.temporal.settings import settings
from app.temporal.client import get_temporal_client, close_temporal_client

__all__ = ["settings", "get_temporal_client", "close_temporal_client"]