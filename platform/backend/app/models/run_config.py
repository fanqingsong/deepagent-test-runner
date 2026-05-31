"""
RunConfig ORM Model

Reusable execution configuration templates for test runs and suites.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RunConfig(Base):
    __tablename__ = "run_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    browser_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    timeout_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    environment_vars: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    retry_policy: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    execution_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
        server_default=func.now(), onupdate=datetime.utcnow,
    )
