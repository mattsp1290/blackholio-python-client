"""
Table subscription interface for SpacetimeDB client.

Provides an abstract interface for subscribing to SpacetimeDB tables and handling
real-time updates across different server languages.
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Dict, Any, Optional
from enum import Enum


class SubscriptionState(Enum):
    """Subscription state enumeration."""
    INACTIVE = "inactive"
    SUBSCRIBING = "subscribing"
    ACTIVE = "active"
    FAILED = "failed"


class SubscriptionInterface(ABC):
    """Abstract interface for SpacetimeDB table subscriptions."""

    @abstractmethod
    async def subscribe_to_tables(self, table_names: List[str]) -> bool:
        """
        Subscribe to specific tables for real-time updates.
        
        Args:
            table_names: List of table names to subscribe to
            
        Returns:
            True if subscription successful, False otherwise
        """
        pass

    @abstractmethod
    async def unsubscribe_from_tables(self, table_names: List[str]) -> bool:
        """
        Unsubscribe from specific tables.
        
        Args:
            table_names: List of table names to unsubscribe from
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        pass

    @abstractmethod
    async def unsubscribe_all(self) -> bool:
        """
        Unsubscribe from all tables.
        
        Returns:
            True if unsubscription successful, False otherwise
        """
        pass

    @abstractmethod
    def get_subscribed_tables(self) -> List[str]:
        """
        Get list of currently subscribed tables.
        
        Returns:
            List of subscribed table names
        """
        pass

    @abstractmethod
    def get_subscription_state(self, table_name: str) -> SubscriptionState:
        """
        Get subscription state for a specific table.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            Current subscription state for the table
        """
        pass

    @abstractmethod
    def on_table_insert(self, table_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for table insert events.
        
        Args:
            table_name: Name of the table to watch
            callback: Function to call when rows are inserted
        """
        pass

    @abstractmethod
    def on_table_update(self, table_name: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]) -> None:
        """
        Register a callback for table update events.
        
        Args:
            table_name: Name of the table to watch
            callback: Function to call when rows are updated (old_row, new_row)
        """
        pass

    @abstractmethod
    def on_table_delete(self, table_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for table delete events.
        
        Args:
            table_name: Name of the table to watch
            callback: Function to call when rows are deleted
        """
        pass

    @abstractmethod
    def on_subscription_state_changed(self, callback: Callable[[str, SubscriptionState], None]) -> None:
        """
        Register a callback for subscription state changes.
        
        Args:
            callback: Function to call when subscription state changes (table_name, state)
        """
        pass

    @abstractmethod
    def on_initial_data_received(self, table_name: str, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """
        Register a callback for initial table data reception.
        
        Args:
            table_name: Name of the table to watch
            callback: Function to call when initial data is received
        """
        pass

    @abstractmethod
    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get current cached data for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of current table rows
        """
        pass

    @abstractmethod
    def clear_table_cache(self, table_name: Optional[str] = None) -> None:
        """
        Clear cached table data.
        
        Args:
            table_name: Specific table to clear (all tables if None)
        """
        pass

    @abstractmethod
    def get_subscription_info(self) -> Dict[str, Any]:
        """
        Get detailed subscription information.
        
        Returns:
            Dictionary containing subscription details
        """
        pass