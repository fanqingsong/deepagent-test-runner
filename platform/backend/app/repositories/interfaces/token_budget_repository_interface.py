"""
Token Budget Repository Interface

Abstract interface for TokenBudget repository operations following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class ITokenBudgetRepository(ABC):
    """
    Abstract interface for TokenBudget repository operations.

    This interface defines the contract for TokenBudget data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        budget: Any,
        db_session: Any
    ) -> Any:
        """
        Create a new token budget.

        Args:
            budget: TokenBudgetCreate schema with budget data
            db_session: Database session

        Returns:
            Created TokenBudget object

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, budget_id: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a token budget by its primary key ID.

        Args:
            budget_id: Primary key ID
            db_session: Database session

        Returns:
            TokenBudget object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_scope(
        self,
        scope_type: str,
        scope_id: Optional[int],
        db_session: Any
    ) -> Optional[Any]:
        """
        Retrieve a token budget by its scope.

        Args:
            scope_type: Scope type (organization, suite, test, user)
            scope_id: ID of the scoped entity
            db_session: Database session

        Returns:
            TokenBudget object or None if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_active_budgets(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve all active token budgets.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of active TokenBudget objects
        """
        pass

    @abstractmethod
    async def get_by_scope_type(
        self,
        scope_type: str,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_parent_budgets(
        self,
        budget_id: int,
        db_session: Any
    ) -> List[Any]:
        """
        Retrieve all parent budgets in the hierarchy.

        Args:
            budget_id: Budget ID to start from
            db_session: Database session

        Returns:
            List of parent TokenBudget objects in hierarchy order
        """
        pass

    @abstractmethod
    async def get_child_budgets(
        self,
        budget_id: int,
        db_session: Any,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve all child budgets of a parent.

        Args:
            budget_id: Parent budget ID
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of child TokenBudget objects
        """
        pass

    @abstractmethod
    async def get_exhausted_budgets(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve all exhausted token budgets.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of exhausted TokenBudget objects
        """
        pass

    @abstractmethod
    async def get_budgets_near_limit(
        self,
        threshold: float = 80.0,
        db_session: Any = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def update(
        self,
        budget_id: int,
        updates: Dict[str, Any],
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def update_usage(
        self,
        budget_id: int,
        tokens_used: int,
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def reset_period(
        self,
        budget_id: int,
        new_period_start: datetime,
        new_period_end: Optional[datetime],
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def delete(self, budget_id: int, db_session: Any) -> bool:
        """
        Delete a token budget by its ID.

        Args:
            budget_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(self, db_session: Any, status: Optional[str] = None) -> int:
        """
        Count total token budgets.

        Args:
            db_session: Database session
            status: Optional status filter

        Returns:
            Total count of token budgets
        """
        pass

    @abstractmethod
    async def exists_by_scope(
        self,
        scope_type: str,
        scope_id: Optional[int],
        db_session: Any
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
        pass
