"""
Neo4j Async Client

Thin wrapper around the official `neo4j` async driver. Reads connection
configuration from settings/env and exposes small helpers used by the
graph builder and root cause service.

The driver is created lazily so that importing this module (and the whole
causal_graphrag package) never fails just because Neo4j is unreachable - the
rest of the application keeps working even if the optional graph feature is down.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Lazy, async wrapper around the Neo4j driver."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._uri = uri or settings.NEO4J_URI
        self._user = user or settings.NEO4J_USER
        self._password = password or settings.NEO4J_PASSWORD
        self._driver = None  # type: Any

    def _get_driver(self):
        """Create the async driver on first use."""
        if self._driver is None:
            # Imported lazily so a missing dependency doesn't break import time.
            from neo4j import AsyncGraphDatabase

            logger.info("Creating Neo4j async driver for %s", self._uri)
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
        return self._driver

    async def verify_connectivity(self) -> bool:
        """Return True if the database is reachable."""
        try:
            driver = self._get_driver()
            await driver.verify_connectivity()
            return True
        except Exception as exc:  # noqa: BLE001 - surface as boolean for health checks
            logger.warning("Neo4j connectivity check failed: %s", exc)
            return False

    async def run_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute a write query (no result needed)."""
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(query, params or {})

    async def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read/write query and return a list of record dicts."""
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = [record.data() async for record in result]
            return records

    async def run_batch(
        self, query: str, batch: List[Dict[str, Any]], key: str = "rows"
    ) -> None:
        """
        Execute a single query that consumes a list parameter via UNWIND.

        Args:
            query: A Cypher query that references `$<key>` and UNWINDs it.
            batch: The list of row dicts to pass.
            key: The parameter name holding the list (default "rows").
        """
        if not batch:
            return
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(query, {key: batch})

    async def close(self) -> None:
        """Close the driver if it was opened."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
