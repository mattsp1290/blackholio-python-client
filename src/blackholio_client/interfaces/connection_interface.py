"""
Connection interface for SpacetimeDB client.

Provides an abstract interface for managing connections to SpacetimeDB servers
across different server languages (Rust, Python, C#, Go).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Optional, Dict, Any


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionInterface(ABC):
    """Abstract interface for SpacetimeDB connection management."""

    @abstractmethod
    async def connect(self, auth_token: Optional[str] = None) -> bool:
        """
        Connect to the SpacetimeDB server.
        
        Args:
            auth_token: Optional authentication token for connecting
            
        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the SpacetimeDB server."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to the server.
        
        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def get_connection_state(self) -> ConnectionState:
        """
        Get the current connection state.
        
        Returns:
            Current connection state
        """
        pass

    @abstractmethod
    def on_connection_state_changed(self, callback: Callable[[ConnectionState], None]) -> None:
        """
        Register a callback for connection state changes.
        
        Args:
            callback: Function to call when connection state changes
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for connection errors.
        
        Args:
            callback: Function to call when connection errors occur
        """
        pass

    @abstractmethod
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the server.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        pass

    @abstractmethod
    def enable_auto_reconnect(self, 
                             max_attempts: int = 10, 
                             delay: float = 1.0,
                             exponential_backoff: bool = True) -> None:
        """
        Enable automatic reconnection on connection loss.
        
        Args:
            max_attempts: Maximum number of reconnection attempts
            delay: Initial delay between reconnection attempts (seconds)
            exponential_backoff: Whether to use exponential backoff for delays
        """
        pass

    @abstractmethod
    def disable_auto_reconnect(self) -> None:
        """Disable automatic reconnection."""
        pass

    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get detailed connection information.
        
        Returns:
            Dictionary containing connection details (host, port, protocol, etc.)
        """
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """
        Send a ping to test connection health.
        
        Returns:
            True if ping successful, False otherwise
        """
        pass

    @abstractmethod
    def get_last_error(self) -> Optional[str]:
        """
        Get the last connection error message.
        
        Returns:
            Last error message or None if no error
        """
        pass