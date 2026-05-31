# service/backend/app/temporal/client.py
from temporalio.client import Client
from app.temporal.settings import settings
from typing import Optional

_client: Optional[Client] = None

async def get_temporal_client() -> Client:
    """
    Get or create the Temporal client singleton.

    Returns:
        Client: Connected Temporal client instance

    Raises:
        RuntimeError: If client connection fails
    """
    global _client

    if _client is None:
        try:
            _client = await Client.connect(
                settings.host_url,
                namespace=settings.namespace
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Temporal server at {settings.host_url}: {e}"
            )

    return _client

async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _client

    if _client is not None:
        await _client.close()
        _client = None
