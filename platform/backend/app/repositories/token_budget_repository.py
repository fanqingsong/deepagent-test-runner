"""
Token Budget Repository Implementation

SQLAlchemy implementation of TokenBudget repository following async patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.token_budget import TokenBudget
from app.repositories.interfaces.token_budget_repository_interface import ITokenBudgetRepository

logger = logging.getLogger(__name__)


class SQLAlchemyTokenBudgetRepository(ITokenBudgetRepository):
    """
    SQLAlchemy implementation of TokenBudget repository.

    Handles all database operations for TokenBudget model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = TokenBudget

    async def create(
        self,
        budget: Any,
        db_session: AsyncSession
    ) -> TokenBudget:
        """
        Create a new token budget.

        Args:
            budget: TokenBudgetCreate schema with budget data
            db_session: Database session

        Returns:
            Created TokenBudget object

        Raises:
            ValueError: If budget already exists for scope
        """
        # Check if budget already exists for this scope
        existing = await self.get_by_scope(
            budget.scope_type,
            budget.scope_id,
            db_session
        )
        if existing:
            raise ValueError(
                f"Budget already exists for scope_type='{budget.scope_type}', scope_id={budget.scope_id}"
            )

        # Create new budget
        new_budget = TokenBudget(
            name=budget.name,
            description=budget.description,
            scope_type=budget.scope_type,
            scope_id=budget.scope_id,
            parent_budget_id=budget.parent_budget_id,
            period_type=budget.period_type,
            period_start=budget.period_start,
            period_end=budget.period_end,
            total_tokens=budget.total_tokens,
            used_tokens=0,
            remaining_tokens=budget.total_tokens,
            priority=budget.priority,
            enforcement_mode=budget.enforcement_mode,
            status=budget.status,
            inherit_from_parent=budget.inherit_from_parent,
            inherit_strategy=budget.inherit_strategy,
            alert_thresholds=budget.alert_thresholds,
            config_data=budget.config_data
        )

        try:
            db_session.add(new_budget)
            await db_session.flush()
            await db_session.refresh(new_budget)

            logger.info(f"Created token budget {new_budget.id} with scope '{new_budget.scope_type}:{new_budget.scope_id}'")
            return new_budget

        except Exception as e:
            logger.error(f"Error creating token budget: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(self, budget_id: int, db_session: AsyncSession) -> Optional[TokenBudget]:
        """
        Retrieve a token budget by its primary key ID.

        Args:
            budget_id: Primary key ID
            db_session: Database session

        Returns:
            TokenBudget object or None if not found
        """
        try:
            stmt = select(TokenBudget).where(TokenBudget.id == budget_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving token budget by id {budget_id}: {e}")
            raise

    async def get_by_scope(
        self,
        scope_type: str,
        scope_id: Optional[int],
        db_session: AsyncSession
    ) -> Optional[TokenBudget]:
        """
        Retrieve a token budget by its scope.

        Args:
            scope_type: Scope type (organization, suite, test, user)
            scope_id: ID of the scoped entity
            db_session: Database session

        Returns:
            TokenBudget object or None if not found
        """
        try:
            stmt = select(TokenBudget).where(
                and_(
                    TokenBudget.scope_type == scope_type,
                    TokenBudget.scope_id == scope_id
                )
            )
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving token budget by scope '{scope_type}:{scope_id}': {e}")
            raise

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[TokenBudget]:
        """
        Retrieve all token budgets with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            status: Optional status filter

        Returns:
            List of TokenBudget objects, ordered by created_at DESC
        """
        try:
            stmt = select(TokenBudget)

            if status:
                stmt = stmt.where(TokenBudget.status == status)

            stmt = stmt.order_by(desc(TokenBudget.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving all token budgets: {e}")
            raise

    async def get_active_budgets(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenBudget]:
        """
        Retrieve all active token budgets.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of active TokenBudget objects
        """
        try:
            stmt = select(TokenBudget).where(
                TokenBudget.status == "active"
            ).order_by(desc(TokenBudget.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving active token budgets: {e}")
            raise

    async def get_by_scope_type(
        self,
        scope_type: str,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenBudget]:
        """
        Retrieve token budgets by scope type.

        Args:
            scope_type: Scope type (organization, suite, test, user)
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TokenBudget objects with the specified scope type
        """
        try:
            stmt = select(TokenBudget).where(
                TokenBudget.scope_type == scope_type
            ).order_by(desc(TokenBudget.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving token budgets by scope type '{scope_type}': {e}")
            raise

    async def get_parent_budgets(
        self,
        budget_id: int,
        db_session: AsyncSession
    ) -> List[TokenBudget]:
        """
        Retrieve all parent budgets in the hierarchy.

        Args:
            budget_id: Budget ID to start from
            db_session: Database session

        Returns:
            List of parent TokenBudget objects in hierarchy order
        """
        try:
            parents = []
            current_budget = await self.get_by_id(budget_id, db_session)

            while current_budget and current_budget.parent_budget_id:
                parent_budget = await self.get_by_id(current_budget.parent_budget_id, db_session)
                if parent_budget:
                    parents.append(parent_budget)
                    current_budget = parent_budget
                else:
                    break

            return parents

        except Exception as e:
            logger.error(f"Error retrieving parent budgets for budget {budget_id}: {e}")
            raise

    async def get_child_budgets(
        self,
        budget_id: int,
        db_session: AsyncSession,
        limit: int = 100
    ) -> List[TokenBudget]:
        """
        Retrieve all child budgets of a parent.

        Args:
            budget_id: Parent budget ID
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of child TokenBudget objects
        """
        try:
            stmt = select(TokenBudget).where(
                TokenBudget.parent_budget_id == budget_id
            ).order_by(desc(TokenBudget.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving child budgets for budget {budget_id}: {e}")
            raise

    async def get_exhausted_budgets(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenBudget]:
        """
        Retrieve all exhausted token budgets.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of exhausted TokenBudget objects
        """
        try:
            stmt = select(TokenBudget).where(
                TokenBudget.status == "exhausted"
            ).order_by(desc(TokenBudget.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving exhausted budgets: {e}")
            raise

    async def get_budgets_near_limit(
        self,
        threshold: float = 80.0,
        db_session: AsyncSession = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenBudget]:
        """
        Retrieve budgets that are near their usage limit.

        Args:
            threshold: Usage percentage threshold (default 80%)
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TokenBudget objects near their limit
        """
        try:
            # Calculate budgets where usage percentage >= threshold
            stmt = select(TokenBudget).where(
                and_(
                    TokenBudget.total_tokens > 0,
                    (TokenBudget.used_tokens * 100.0 / TokenBudget.total_tokens) >= threshold
                )
            ).order_by(desc(TokenBudget.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            budgets = list(result.scalars().all())

            # Filter in Python to ensure accuracy
            return [b for b in budgets if b.usage_percentage >= threshold]

        except Exception as e:
            logger.error(f"Error retrieving budgets near limit: {e}")
            raise

    async def update(
        self,
        budget_id: int,
        updates: Dict[str, Any],
        db_session: AsyncSession
    ) -> TokenBudget:
        """
        Update a token budget.

        Args:
            budget_id: Primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated TokenBudget object

        Raises:
            ValueError: If budget not found
        """
        budget = await self.get_by_id(budget_id, db_session)
        if not budget:
            raise ValueError(f"Token budget {budget_id} not found")

        # Update allowed fields
        allowed_fields = {
            'name', 'description', 'period_type', 'period_start', 'period_end',
            'total_tokens', 'priority', 'enforcement_mode', 'status',
            'inherit_from_parent', 'inherit_strategy', 'alert_thresholds',
            'metadata'
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(budget, field):
                setattr(budget, field, value)

        # Recalculate remaining if total_tokens changed
        if 'total_tokens' in updates:
            budget.remaining_tokens = budget.total_tokens - budget.used_tokens

        budget.updated_at = datetime.utcnow()

        try:
            await db_session.flush()
            await db_session.refresh(budget)

            logger.info(f"Updated token budget {budget_id}")
            return budget

        except Exception as e:
            logger.error(f"Error updating token budget {budget_id}: {e}")
            await db_session.rollback()
            raise

    async def update_usage(
        self,
        budget_id: int,
        tokens_used: int,
        db_session: AsyncSession
    ) -> TokenBudget:
        """
        Update usage for a token budget.

        Args:
            budget_id: Budget ID
            tokens_used: Number of tokens to add to used count
            db_session: Database session

        Returns:
            Updated TokenBudget object

        Raises:
            ValueError: If budget not found
        """
        budget = await self.get_by_id(budget_id, db_session)
        if not budget:
            raise ValueError(f"Token budget {budget_id} not found")

        # Update usage using model method
        budget.update_usage(tokens_used)
        budget.updated_at = datetime.utcnow()

        try:
            await db_session.flush()
            await db_session.refresh(budget)

            logger.info(f"Updated usage for token budget {budget_id}, added {tokens_used} tokens")
            return budget

        except Exception as e:
            logger.error(f"Error updating usage for token budget {budget_id}: {e}")
            await db_session.rollback()
            raise

    async def reset_period(
        self,
        budget_id: int,
        new_period_start: datetime,
        new_period_end: Optional[datetime],
        db_session: AsyncSession
    ) -> TokenBudget:
        """
        Reset the period for a token budget.

        Args:
            budget_id: Budget ID
            new_period_start: Start of new period
            new_period_end: End of new period (optional)
            db_session: Database session

        Returns:
            Updated TokenBudget object

        Raises:
            ValueError: If budget not found
        """
        budget = await self.get_by_id(budget_id, db_session)
        if not budget:
            raise ValueError(f"Token budget {budget_id} not found")

        # Reset period using model method
        budget.reset_period(new_period_start, new_period_end)

        try:
            await db_session.flush()
            await db_session.refresh(budget)

            logger.info(f"Reset period for token budget {budget_id}")
            return budget

        except Exception as e:
            logger.error(f"Error resetting period for token budget {budget_id}: {e}")
            await db_session.rollback()
            raise

    async def delete(self, budget_id: int, db_session: AsyncSession) -> bool:
        """
        Delete a token budget by its ID.

        Args:
            budget_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        try:
            budget = await self.get_by_id(budget_id, db_session)
            if not budget:
                return False

            db_session.delete(budget)
            await db_session.flush()

            logger.info(f"Deleted token budget {budget_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting token budget {budget_id}: {e}")
            await db_session.rollback()
            raise

    async def count(self, db_session: AsyncSession, status: Optional[str] = None) -> int:
        """
        Count total token budgets.

        Args:
            db_session: Database session
            status: Optional status filter

        Returns:
            Total count of token budgets
        """
        try:
            stmt = select(func.count()).select_from(TokenBudget)

            if status:
                stmt = stmt.where(TokenBudget.status == status)

            result = await db_session.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting token budgets: {e}")
            raise

    async def exists_by_scope(
        self,
        scope_type: str,
        scope_id: Optional[int],
        db_session: AsyncSession
    ) -> bool:
        """
        Check if a budget exists for a scope.

        Args:
            scope_type: Scope type
            scope_id: ID of the scoped entity
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count()).select_from(TokenBudget).where(
                and_(
                    TokenBudget.scope_type == scope_type,
                    TokenBudget.scope_id == scope_id
                )
            )
            result = await db_session.execute(stmt)
            count = result.scalar() or 0
            return count > 0

        except Exception as e:
            logger.error(f"Error checking if budget exists for scope '{scope_type}:{scope_id}': {e}")
            raise
