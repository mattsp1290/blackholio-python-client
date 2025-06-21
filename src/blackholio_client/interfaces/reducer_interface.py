"""
Reducer interface for SpacetimeDB client.

Provides an abstract interface for calling reducers (game actions) on SpacetimeDB
servers across different server languages with consistent error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List
from enum import Enum


class ReducerStatus(Enum):
    """Reducer call status enumeration."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ReducerInterface(ABC):
    """Abstract interface for SpacetimeDB reducer calls."""

    @abstractmethod
    async def call_reducer(self, 
                          reducer_name: str, 
                          *args,
                          request_id: Optional[str] = None,
                          timeout: Optional[float] = None) -> bool:
        """
        Call a reducer on the SpacetimeDB server.
        
        Args:
            reducer_name: Name of the reducer to call
            *args: Arguments to pass to the reducer
            request_id: Optional request ID for tracking
            timeout: Optional timeout for the call (seconds)
            
        Returns:
            True if reducer call successful, False otherwise
        """
        pass

    @abstractmethod
    async def call_reducer_with_response(self,
                                       reducer_name: str,
                                       *args,
                                       request_id: Optional[str] = None,
                                       timeout: Optional[float] = 10.0) -> Dict[str, Any]:
        """
        Call a reducer and wait for response.
        
        Args:
            reducer_name: Name of the reducer to call
            *args: Arguments to pass to the reducer
            request_id: Optional request ID for tracking
            timeout: Timeout for waiting for response (seconds)
            
        Returns:
            Dictionary containing response data and status
        """
        pass

    @abstractmethod
    def on_reducer_response(self, callback: Callable[[str, ReducerStatus, Dict[str, Any]], None]) -> None:
        """
        Register a callback for reducer responses.
        
        Args:
            callback: Function to call when reducer response received (request_id, status, data)
        """
        pass

    @abstractmethod
    def on_reducer_error(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback for reducer errors.
        
        Args:
            callback: Function to call when reducer error occurs (reducer_name, error_message)
        """
        pass

    @abstractmethod
    def get_pending_reducers(self) -> List[str]:
        """
        Get list of pending reducer requests.
        
        Returns:
            List of request IDs for pending reducers
        """
        pass

    @abstractmethod
    def cancel_reducer(self, request_id: str) -> bool:
        """
        Cancel a pending reducer request.
        
        Args:
            request_id: Request ID to cancel
            
        Returns:
            True if cancellation successful, False otherwise
        """
        pass

    @abstractmethod
    def get_reducer_status(self, request_id: str) -> Optional[ReducerStatus]:
        """
        Get status of a specific reducer request.
        
        Args:
            request_id: Request ID to check
            
        Returns:
            Current status or None if request not found
        """
        pass

    # Game-specific reducer methods (convenience methods)
    @abstractmethod
    async def enter_game(self, player_name: str) -> bool:
        """
        Enter the game with a player name.
        
        Args:
            player_name: Name of the player entering the game
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def update_player_input(self, direction: Dict[str, float]) -> bool:
        """
        Update player input direction.
        
        Args:
            direction: Direction vector (e.g., {"x": 0.5, "y": -0.3})
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def player_split(self) -> bool:
        """
        Split the player's entities.
        
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def leave_game(self) -> bool:
        """
        Leave the current game.
        
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_reducer_info(self) -> Dict[str, Any]:
        """
        Get detailed reducer information and statistics.
        
        Returns:
            Dictionary containing reducer call statistics and state
        """
        pass