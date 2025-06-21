"""
Main game client interface for SpacetimeDB client.

Provides the primary interface that consolidates connection management, authentication,
subscriptions, and game logic into a unified API that abstracts server language differences.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from .connection_interface import ConnectionInterface, ConnectionState
from .auth_interface import AuthInterface
from .subscription_interface import SubscriptionInterface, SubscriptionState
from .reducer_interface import ReducerInterface, ReducerStatus
from ..models.game_entities import GamePlayer, GameEntity, GameCircle, Vector2


class GameClientInterface(ConnectionInterface, AuthInterface, SubscriptionInterface, ReducerInterface):
    """
    Main unified interface for Blackholio SpacetimeDB client.
    
    This interface combines all sub-interfaces into a single comprehensive API
    that provides access to connection management, authentication, table subscriptions,
    reducer calls, and game-specific functionality.
    """

    @abstractmethod
    def __init__(self, 
                 host: str,
                 database: str,
                 server_language: str = "rust",
                 protocol: str = "v1.json.spacetimedb",
                 auto_reconnect: bool = True) -> None:
        """
        Initialize the game client.
        
        Args:
            host: Server host (e.g., "localhost:3000")
            database: Database identity/name
            server_language: Server implementation language (rust, python, csharp, go)
            protocol: SpacetimeDB protocol version
            auto_reconnect: Whether to enable automatic reconnection
        """
        pass

    # Game State Access Methods
    @abstractmethod
    def get_local_player(self) -> Optional[GamePlayer]:
        """
        Get the local player information.
        
        Returns:
            Local player object or None if not in game
        """
        pass

    @abstractmethod
    def get_local_player_entities(self) -> List[GameEntity]:
        """
        Get all entities belonging to the local player.
        
        Returns:
            List of local player's entities
        """
        pass

    @abstractmethod
    def get_all_entities(self) -> Dict[int, GameEntity]:
        """
        Get all game entities.
        
        Returns:
            Dictionary mapping entity IDs to entities
        """
        pass

    @abstractmethod
    def get_all_players(self) -> Dict[int, GamePlayer]:
        """
        Get all players in the game.
        
        Returns:
            Dictionary mapping player IDs to players
        """
        pass

    @abstractmethod
    def get_all_circles(self) -> Dict[int, GameCircle]:
        """
        Get all circles in the game.
        
        Returns:
            Dictionary mapping circle IDs to circles
        """
        pass

    @abstractmethod
    def get_entities_near(self, position: Vector2, radius: float) -> List[GameEntity]:
        """
        Get entities within a radius of a position.
        
        Args:
            position: Center position to search from
            radius: Search radius
            
        Returns:
            List of entities within the radius
        """
        pass

    @abstractmethod
    def get_game_config(self) -> Dict[str, Any]:
        """
        Get current game configuration.
        
        Returns:
            Dictionary containing game configuration parameters
        """
        pass

    # Game Event Handlers
    @abstractmethod
    def on_player_joined(self, callback: Callable[[GamePlayer], None]) -> None:
        """
        Register callback for when a player joins the game.
        
        Args:
            callback: Function to call when player joins
        """
        pass

    @abstractmethod
    def on_player_left(self, callback: Callable[[GamePlayer], None]) -> None:
        """
        Register callback for when a player leaves the game.
        
        Args:
            callback: Function to call when player leaves
        """
        pass

    @abstractmethod
    def on_entity_created(self, callback: Callable[[GameEntity], None]) -> None:
        """
        Register callback for when an entity is created.
        
        Args:
            callback: Function to call when entity is created
        """
        pass

    @abstractmethod
    def on_entity_updated(self, callback: Callable[[GameEntity, GameEntity], None]) -> None:
        """
        Register callback for when an entity is updated.
        
        Args:
            callback: Function to call when entity is updated (old, new)
        """
        pass

    @abstractmethod
    def on_entity_destroyed(self, callback: Callable[[GameEntity], None]) -> None:
        """
        Register callback for when an entity is destroyed.
        
        Args:
            callback: Function to call when entity is destroyed
        """
        pass

    @abstractmethod
    def on_game_state_changed(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register callback for general game state changes.
        
        Args:
            callback: Function to call when game state changes
        """
        pass

    # High-Level Game Operations
    @abstractmethod
    async def join_game(self, player_name: str, auto_subscribe: bool = True) -> bool:
        """
        Join the game with full initialization.
        
        Args:
            player_name: Name of the player
            auto_subscribe: Whether to automatically subscribe to game tables
            
        Returns:
            True if join successful, False otherwise
        """
        pass

    @abstractmethod
    async def leave_game(self, auto_unsubscribe: bool = True) -> bool:
        """
        Leave the game with cleanup.
        
        Args:
            auto_unsubscribe: Whether to automatically unsubscribe from tables
            
        Returns:
            True if leave successful, False otherwise
        """
        pass

    @abstractmethod
    def is_in_game(self) -> bool:
        """
        Check if currently in a game.
        
        Returns:
            True if in game, False otherwise
        """
        pass

    @abstractmethod
    async def move_player(self, direction: Vector2) -> bool:
        """
        Move the player in a direction.
        
        Args:
            direction: Normalized direction vector
            
        Returns:
            True if movement successful, False otherwise
        """
        pass

    # Client State and Statistics
    @abstractmethod
    def get_client_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive client statistics.
        
        Returns:
            Dictionary containing connection stats, game stats, performance metrics
        """
        pass

    @abstractmethod
    def get_client_state(self) -> Dict[str, Any]:
        """
        Get current client state summary.
        
        Returns:
            Dictionary containing current state of all client components
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the client.
        
        Performs cleanup including disconnection, unsubscription, and resource cleanup.
        """
        pass

    # Debug and Development Methods
    @abstractmethod
    def enable_debug_logging(self, level: str = "DEBUG") -> None:
        """
        Enable debug logging for troubleshooting.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        pass

    @abstractmethod
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get comprehensive debug information.
        
        Returns:
            Dictionary containing detailed debug information
        """
        pass

    @abstractmethod
    def export_state(self, file_path: str) -> bool:
        """
        Export current client state to file for debugging.
        
        Args:
            file_path: Path to save state file
            
        Returns:
            True if export successful, False otherwise
        """
        pass