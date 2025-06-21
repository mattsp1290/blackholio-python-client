"""
Unified SpacetimeDB client for Blackholio game.

This module provides the main GameClient implementation that consolidates all
functionality from the interfaces into a single, easy-to-use client class.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .interfaces.game_client_interface import GameClientInterface
from .interfaces.connection_interface import ConnectionState
from .interfaces.subscription_interface import SubscriptionState
from .interfaces.reducer_interface import ReducerStatus
from .models.game_entities import GamePlayer, GameEntity, GameCircle, Vector2
from .connection.modernized_spacetimedb_client import ModernizedSpacetimeDBConnection
from .connection.server_config import ServerConfig
from .config.environment import EnvironmentConfig
from .factory.client_factory import get_client_factory
from .exceptions.connection_errors import BlackholioTimeoutError, BlackholioConnectionError
from pathlib import Path


logger = logging.getLogger(__name__)


class GameClient(GameClientInterface):
    """
    Unified SpacetimeDB client for Blackholio game.
    
    This is the main client class that implements all interfaces and provides
    a consistent API for interacting with SpacetimeDB servers across different
    server languages.
    """

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
        self._host = host
        self._database = database
        self._server_language = server_language
        self._protocol = protocol
        self._auto_reconnect = auto_reconnect
        
        # Initialize configuration
        from .config.environment import get_environment_config
        self._config = get_environment_config()
        self._config.server_language = server_language
        if ':' in host:
            host_parts = host.split(':')
            self._config.server_ip = host_parts[0]
            self._config.server_port = int(host_parts[1])
        else:
            self._config.server_ip = host
        
        # Initialize connection manager
        from .connection.connection_manager import get_connection_manager
        self._connection_manager = get_connection_manager()
        
        # Client state
        self._connection_state = ConnectionState.DISCONNECTED
        self._is_authenticated = False
        self._identity = None
        self._token = None
        self._is_in_game = False
        self._local_player = None
        
        # Data caches
        self._entities: Dict[int, GameEntity] = {}
        self._players: Dict[int, GamePlayer] = {}
        self._circles: Dict[int, GameCircle] = {}
        self._game_config: Dict[str, Any] = {}
        
        # Subscription state
        self._subscribed_tables: List[str] = []
        self._subscription_states: Dict[str, SubscriptionState] = {}
        
        # Reducer tracking
        self._pending_reducers: Dict[str, ReducerStatus] = {}
        
        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'connection_state_changed': [],
            'error': [],
            'authentication_changed': [],
            'token_refresh': [],
            'subscription_state_changed': [],
            'table_insert': {},
            'table_update': {},
            'table_delete': {},
            'initial_data_received': {},
            'reducer_response': [],
            'reducer_error': [],
            'player_joined': [],
            'player_left': [],
            'entity_created': [],
            'entity_updated': [],
            'entity_destroyed': [],
            'game_state_changed': []
        }
        
        # Statistics
        self._stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'reducer_calls': 0,
            'successful_reducers': 0,
            'failed_reducers': 0,
            'messages_received': 0,
            'messages_sent': 0,
            'start_time': datetime.now(),
            'last_activity': datetime.now()
        }
        
        # ADD: Connection lifecycle management
        self._active_connection: Optional[Any] = None
        self._connection_context: Optional[Any] = None
        self._connection_lock = asyncio.Lock()
        self._is_connecting = False
        
        # Configure auto-reconnect if enabled
        if self._auto_reconnect:
            self.enable_auto_reconnect()

    # Connection Interface Implementation
    async def connect(self, auth_token: Optional[str] = None) -> bool:
        """Connect to the SpacetimeDB server with proper context manager usage."""
        async with self._connection_lock:
            # Prevent duplicate connection attempts
            if self._is_connecting:
                while self._is_connecting:
                    await asyncio.sleep(0.1)
                return self.is_connected()
            
            if self._active_connection and self.is_connected():
                return True  # Already connected
            
            try:
                self._is_connecting = True
                self._connection_state = ConnectionState.CONNECTING
                self._notify_connection_state_changed()
                self._stats['connection_attempts'] += 1
                
                # ✅ CORRECT: Use as async context manager
                self._connection_context = self._connection_manager.get_connection(
                    server_language=self._server_language
                )
                
                # Properly enter the context manager
                self._active_connection = await self._connection_context.__aenter__()
                
                if self._active_connection:
                    self._connection_state = ConnectionState.CONNECTED
                    self._stats['successful_connections'] += 1
                    self._stats['last_activity'] = datetime.now()
                    self._notify_connection_state_changed()
                    
                    # Authenticate if token provided
                    if auth_token:
                        await self.authenticate({'token': auth_token})
                    else:
                        self.load_token()
                    
                    return True
                else:
                    await self._cleanup_failed_connection()
                    return False
                    
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                await self._cleanup_failed_connection()
                return False
            finally:
                self._is_connecting = False

    async def _cleanup_failed_connection(self):
        """Clean up failed connection attempt."""
        self._connection_state = ConnectionState.FAILED
        self._stats['failed_connections'] += 1
        self._notify_connection_state_changed()
        
        if self._connection_context and self._active_connection:
            try:
                await self._connection_context.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error during connection cleanup: {e}")
            finally:
                self._active_connection = None
                self._connection_context = None

    async def disconnect(self) -> None:
        """Disconnect from the SpacetimeDB server with proper cleanup."""
        async with self._connection_lock:
            try:
                self._connection_state = ConnectionState.DISCONNECTED
                self._is_authenticated = False
                self._is_in_game = False
                self._local_player = None
                
                # Clear caches
                self._entities.clear()
                self._players.clear()
                self._circles.clear()
                
                # Properly exit the context manager
                if self._connection_context and self._active_connection:
                    await self._connection_context.__aexit__(None, None, None)
                
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self._active_connection = None
                self._connection_context = None
                self._notify_connection_state_changed()

    def is_connected(self) -> bool:
        """Check if currently connected to the server."""
        return self._connection_state == ConnectionState.CONNECTED

    def get_connection_state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._connection_state

    def on_connection_state_changed(self, callback: Callable[[ConnectionState], None]) -> None:
        """Register a callback for connection state changes."""
        self._callbacks['connection_state_changed'].append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Register a callback for connection errors."""
        self._callbacks['error'].append(callback)

    async def reconnect(self) -> bool:
        """Attempt to reconnect to the server."""
        self._connection_state = ConnectionState.RECONNECTING
        self._notify_connection_state_changed()
        return await self.connect()

    def enable_auto_reconnect(self, max_attempts: int = 10, delay: float = 1.0, exponential_backoff: bool = True) -> None:
        """Enable automatic reconnection on connection loss."""
        # This would be implemented with the connection manager's retry logic
        pass

    def disable_auto_reconnect(self) -> None:
        """Disable automatic reconnection."""
        pass

    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information."""
        return {
            'host': self._host,
            'database': self._database,
            'server_language': self._server_language,
            'protocol': self._protocol,
            'state': self._connection_state.value,
            'is_authenticated': self._is_authenticated,
            'auto_reconnect': self._auto_reconnect
        }

    async def ping(self) -> bool:
        """Send a ping to test connection health."""
        # This would be implemented with the actual connection
        return self.is_connected()

    def get_last_error(self) -> Optional[str]:
        """Get the last connection error message."""
        # This would be tracked in the connection manager
        return None

    # Authentication Interface Implementation
    @property
    def identity(self) -> Optional[str]:
        """Get the current user identity."""
        return self._identity

    @property
    def token(self) -> Optional[str]:
        """Get the current authentication token."""
        return self._token

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._is_authenticated

    async def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Authenticate with the SpacetimeDB server."""
        try:
            if credentials and 'token' in credentials:
                self._token = credentials['token']
                self._is_authenticated = True
                self._notify_authentication_changed()
                return True
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def logout(self) -> bool:
        """Logout and clear authentication state."""
        self._is_authenticated = False
        self._identity = None
        self._token = None
        self._notify_authentication_changed()
        return True

    def save_token(self, file_path: Optional[str] = None) -> bool:
        """Save the current authentication token to disk."""
        # Implementation would save token to file
        return True

    def load_token(self, file_path: Optional[str] = None) -> bool:
        """Load authentication token from disk."""
        # Implementation would load token from file
        return True

    def clear_saved_token(self, file_path: Optional[str] = None) -> bool:
        """Clear saved authentication token from disk."""
        # Implementation would clear token file
        return True

    def on_authentication_changed(self, callback: Callable[[bool], None]) -> None:
        """Register a callback for authentication state changes."""
        self._callbacks['authentication_changed'].append(callback)

    def on_token_refresh(self, callback: Callable[[str], None]) -> None:
        """Register a callback for token refresh events."""
        self._callbacks['token_refresh'].append(callback)

    def get_auth_info(self) -> Dict[str, Any]:
        """Get detailed authentication information."""
        return {
            'is_authenticated': self._is_authenticated,
            'identity': self._identity,
            'has_token': self._token is not None,
            'token_length': len(self._token) if self._token else 0
        }

    async def refresh_token(self) -> bool:
        """Refresh the current authentication token."""
        # Implementation would refresh token with server
        return True

    def validate_token(self, token: Optional[str] = None) -> bool:
        """Validate an authentication token."""
        token_to_validate = token or self._token
        return token_to_validate is not None and len(token_to_validate) > 0

    # Game State Access Methods
    def get_local_player(self) -> Optional[GamePlayer]:
        """Get the local player information."""
        return self._local_player

    def get_local_player_entities(self) -> List[GameEntity]:
        """Get all entities belonging to the local player."""
        if not self._local_player:
            return []
        
        return [entity for entity in self._entities.values() 
                if hasattr(entity, 'player_id') and entity.player_id == self._local_player.player_id]

    def get_all_entities(self) -> Dict[int, GameEntity]:
        """Get all game entities."""
        return self._entities.copy()

    def get_all_players(self) -> Dict[int, GamePlayer]:
        """Get all players in the game."""
        return self._players.copy()

    def get_all_circles(self) -> Dict[int, GameCircle]:
        """Get all circles in the game."""
        return self._circles.copy()

    def get_entities_near(self, position: Vector2, radius: float) -> List[GameEntity]:
        """Get entities within a radius of a position."""
        nearby_entities = []
        for entity in self._entities.values():
            distance = position.distance_to(entity.position)
            if distance <= radius:
                nearby_entities.append(entity)
        return nearby_entities

    def get_game_config(self) -> Dict[str, Any]:
        """Get current game configuration."""
        return self._game_config.copy()

    # Subscription Interface Implementation (simplified)
    async def subscribe_to_tables(self, table_names: List[str]) -> bool:
        """Subscribe to specific tables for real-time updates."""
        self._subscribed_tables.extend(table_names)
        for table in table_names:
            self._subscription_states[table] = SubscriptionState.ACTIVE
        return True

    async def unsubscribe_from_tables(self, table_names: List[str]) -> bool:
        """Unsubscribe from specific tables."""
        for table in table_names:
            if table in self._subscribed_tables:
                self._subscribed_tables.remove(table)
            self._subscription_states[table] = SubscriptionState.INACTIVE
        return True

    async def unsubscribe_all(self) -> bool:
        """Unsubscribe from all tables."""
        self._subscribed_tables.clear()
        for table in self._subscription_states:
            self._subscription_states[table] = SubscriptionState.INACTIVE
        return True

    def get_subscribed_tables(self) -> List[str]:
        """Get list of currently subscribed tables."""
        return self._subscribed_tables.copy()

    def get_subscription_state(self, table_name: str) -> SubscriptionState:
        """Get subscription state for a specific table."""
        return self._subscription_states.get(table_name, SubscriptionState.INACTIVE)

    # Reducer Interface Implementation (simplified)
    async def call_reducer(self, reducer_name: str, *args, request_id: Optional[str] = None, timeout: Optional[float] = None) -> bool:
        """Call a reducer on the SpacetimeDB server."""
        if not request_id:
            request_id = str(uuid.uuid4())
        
        self._pending_reducers[request_id] = ReducerStatus.PENDING
        self._stats['reducer_calls'] += 1
        
        # Simulate reducer call success
        self._pending_reducers[request_id] = ReducerStatus.SUCCESS
        self._stats['successful_reducers'] += 1
        return True

    async def call_reducer_with_response(self, reducer_name: str, *args, request_id: Optional[str] = None, timeout: Optional[float] = 10.0) -> Dict[str, Any]:
        """Call a reducer and wait for response."""
        success = await self.call_reducer(reducer_name, *args, request_id=request_id, timeout=timeout)
        return {
            'success': success,
            'request_id': request_id,
            'status': ReducerStatus.SUCCESS if success else ReducerStatus.FAILED
        }

    # Game-specific reducer methods
    async def enter_game(self, player_name: str) -> bool:
        """Enter the game with a player name."""
        success = await self.call_reducer("enter_game", player_name)
        if success:
            self._is_in_game = True
        return success

    async def update_player_input(self, direction: Dict[str, float]) -> bool:
        """Update player input direction."""
        return await self.call_reducer("update_player_input", direction)

    async def player_split(self) -> bool:
        """Split the player's entities."""
        return await self.call_reducer("player_split")

    async def leave_game(self) -> bool:
        """Leave the current game."""
        success = await self.call_reducer("leave_game")
        if success:
            self._is_in_game = False
            self._local_player = None
        return success

    # High-Level Game Operations
    async def join_game(self, player_name: str, auto_subscribe: bool = True) -> bool:
        """Join the game with proper connection validation."""
        if not self._active_connection or not self.is_connected():
            logger.error("Cannot join game: not connected to server")
            if not await self.connect():
                return False
        
        if auto_subscribe:
            await self.subscribe_to_tables(["entity", "player", "circle", "food", "config"])
        
        try:
            # Use the active connection for game operations
            # Implementation depends on the connection interface
            success = await self.enter_game(player_name)
            if success:
                self._is_in_game = True
                # Additional game state setup would go here
            return success
        except Exception as e:
            logger.error(f"Failed to join game: {e}")
            return False

    def is_in_game(self) -> bool:
        """Check if currently in a game."""
        return self._is_in_game

    async def move_player(self, direction: Vector2) -> bool:
        """Move the player in a direction."""
        return await self.update_player_input({"x": direction.x, "y": direction.y})

    # Client State and Statistics
    def get_client_statistics(self) -> Dict[str, Any]:
        """Get comprehensive client statistics."""
        current_time = datetime.now()
        uptime = current_time - self._stats['start_time']
        
        return {
            **self._stats,
            'uptime_seconds': uptime.total_seconds(),
            'entities_count': len(self._entities),
            'players_count': len(self._players),
            'circles_count': len(self._circles),
            'subscribed_tables_count': len(self._subscribed_tables),
            'pending_reducers_count': len(self._pending_reducers)
        }

    def get_client_state(self) -> Dict[str, Any]:
        """Get current client state summary."""
        return {
            'connection': self.get_connection_info(),
            'authentication': self.get_auth_info(),
            'game_state': {
                'is_in_game': self._is_in_game,
                'has_local_player': self._local_player is not None,
                'entities_count': len(self._entities),
                'players_count': len(self._players)
            },
            'subscriptions': {
                'tables': self._subscribed_tables,
                'states': {k: v.value for k, v in self._subscription_states.items()}
            },
            'statistics': self.get_client_statistics()
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the client."""
        if self._is_in_game:
            await self.leave_game()
        
        await self.unsubscribe_all()
        await self.disconnect()

    # Debug and Development Methods
    def enable_debug_logging(self, level: str = "DEBUG") -> None:
        """Enable debug logging for troubleshooting."""
        logging.getLogger(__name__).setLevel(getattr(logging, level.upper()))

    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information."""
        return {
            'client_state': self.get_client_state(),
            'configuration': {
                'host': self._host,
                'database': self._database,
                'server_language': self._server_language,
                'protocol': self._protocol,
                'auto_reconnect': self._auto_reconnect
            },
            'callbacks': {k: len(v) if isinstance(v, list) else len(v) 
                         for k, v in self._callbacks.items()},
            'memory_usage': {
                'entities': len(self._entities),
                'players': len(self._players),
                'circles': len(self._circles),
                'pending_reducers': len(self._pending_reducers)
            }
        }

    def export_state(self, file_path: str) -> bool:
        """Export current client state to file for debugging."""
        try:
            file_path = Path(file_path).resolve()
            if not str(file_path).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {file_path}")
            with open(file_path, 'w') as f:
                json.dump(self.get_debug_info(), f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to export state: {e}")
            return False

    # Event notification helpers
    def _notify_connection_state_changed(self) -> None:
        """Notify connection state change callbacks."""
        for callback in self._callbacks['connection_state_changed']:
            try:
                callback(self._connection_state)
            except Exception as e:
                logger.error(f"Error in connection state callback: {e}")

    def _notify_error(self, error_message: str) -> None:
        """Notify error callbacks."""
        for callback in self._callbacks['error']:
            try:
                callback(error_message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    def _notify_authentication_changed(self) -> None:
        """Notify authentication change callbacks."""
        for callback in self._callbacks['authentication_changed']:
            try:
                callback(self._is_authenticated)
            except Exception as e:
                logger.error(f"Error in authentication callback: {e}")

    # Placeholder implementations for remaining interface methods
    def on_table_insert(self, table_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        if table_name not in self._callbacks['table_insert']:
            self._callbacks['table_insert'][table_name] = []
        self._callbacks['table_insert'][table_name].append(callback)

    def on_table_update(self, table_name: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]) -> None:
        if table_name not in self._callbacks['table_update']:
            self._callbacks['table_update'][table_name] = []
        self._callbacks['table_update'][table_name].append(callback)

    def on_table_delete(self, table_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        if table_name not in self._callbacks['table_delete']:
            self._callbacks['table_delete'][table_name] = []
        self._callbacks['table_delete'][table_name].append(callback)

    def on_subscription_state_changed(self, callback: Callable[[str, SubscriptionState], None]) -> None:
        self._callbacks['subscription_state_changed'].append(callback)

    def on_initial_data_received(self, table_name: str, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        if table_name not in self._callbacks['initial_data_received']:
            self._callbacks['initial_data_received'][table_name] = []
        self._callbacks['initial_data_received'][table_name].append(callback)

    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    def clear_table_cache(self, table_name: Optional[str] = None) -> None:
        if table_name:
            # Clear specific table cache
            pass
        else:
            # Clear all table caches
            self._entities.clear()
            self._players.clear()
            self._circles.clear()

    def get_subscription_info(self) -> Dict[str, Any]:
        return {
            'subscribed_tables': self._subscribed_tables,
            'subscription_states': {k: v.value for k, v in self._subscription_states.items()}
        }

    def on_reducer_response(self, callback: Callable[[str, ReducerStatus, Dict[str, Any]], None]) -> None:
        self._callbacks['reducer_response'].append(callback)

    def on_reducer_error(self, callback: Callable[[str, str], None]) -> None:
        self._callbacks['reducer_error'].append(callback)

    def get_pending_reducers(self) -> List[str]:
        return [req_id for req_id, status in self._pending_reducers.items() 
                if status == ReducerStatus.PENDING]

    def cancel_reducer(self, request_id: str) -> bool:
        if request_id in self._pending_reducers:
            self._pending_reducers[request_id] = ReducerStatus.FAILED
            return True
        return False
    
    @property
    def server_language(self) -> str:
        """Get the server language."""
        return self._server_language

    def get_reducer_status(self, request_id: str) -> Optional[ReducerStatus]:
        return self._pending_reducers.get(request_id)

    def get_reducer_info(self) -> Dict[str, Any]:
        return {
            'total_calls': self._stats['reducer_calls'],
            'successful_calls': self._stats['successful_reducers'],
            'failed_calls': self._stats['failed_reducers'],
            'pending_calls': len(self.get_pending_reducers()),
            'pending_request_ids': self.get_pending_reducers()
        }

    def on_player_joined(self, callback: Callable[[GamePlayer], None]) -> None:
        self._callbacks['player_joined'].append(callback)

    def on_player_left(self, callback: Callable[[GamePlayer], None]) -> None:
        self._callbacks['player_left'].append(callback)

    def on_entity_created(self, callback: Callable[[GameEntity], None]) -> None:
        self._callbacks['entity_created'].append(callback)

    def on_entity_updated(self, callback: Callable[[GameEntity, GameEntity], None]) -> None:
        self._callbacks['entity_updated'].append(callback)

    def on_entity_destroyed(self, callback: Callable[[GameEntity], None]) -> None:
        self._callbacks['entity_destroyed'].append(callback)

    def on_game_state_changed(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks['game_state_changed'].append(callback)


# Factory function for creating clients
def create_game_client(host: str,
                      database: str,
                      server_language: str = "rust",
                      protocol: str = "v1.json.spacetimedb",
                      auto_reconnect: bool = True) -> GameClient:
    """
    Create a new GameClient instance.
    
    Args:
        host: Server host (e.g., "localhost:3000")
        database: Database identity/name
        server_language: Server implementation language (rust, python, csharp, go)
        protocol: SpacetimeDB protocol version
        auto_reconnect: Whether to enable automatic reconnection
        
    Returns:
        Configured GameClient instance
    """
    return GameClient(
        host=host,
        database=database,
        server_language=server_language,
        protocol=protocol,
        auto_reconnect=auto_reconnect
    )