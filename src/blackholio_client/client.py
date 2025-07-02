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
        
        # Override environment default with passed database parameter
        self._config.spacetime_db_identity = database
        
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
            
        # Set up connection event handlers for data synchronization
        self._setup_connection_event_handlers()

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
                    server_language=self._server_language,
                    database=self._database
                )
                
                # Properly enter the context manager
                self._active_connection = await self._connection_context.__aenter__()
                
                if self._active_connection:
                    self._connection_state = ConnectionState.CONNECTED
                    self._stats['successful_connections'] += 1
                    self._stats['last_activity'] = datetime.now()
                    self._notify_connection_state_changed()
                    
                    # Set up event handlers for future messages
                    self._bridge_connection_events()
                    
                    # CRITICAL FIX: Process any subscription data that was already received
                    # This handles the timing issue where InitialSubscription arrives before handlers are set up
                    await self._process_existing_subscription_data()
                    
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

    async def debug_full_client_state(self) -> None:
        """Comprehensive debugging of client state."""
        print("=== CLIENT DEBUGGING ===")
        
        # Connection state
        await self.debug_connection_state()
        
        # Subscription setup
        await self.debug_subscription_setup() 
        
        # Table access testing
        await self.debug_table_access()
        
        # Data format debugging
        await self.debug_data_format()
        
        print("=== END DEBUGGING ===")

    async def debug_connection_state(self) -> None:
        """Debug connection state."""
        print(f"Connected to database: {self._database}")
        print(f"Connection state: {self._connection_state}")
        print(f"Is authenticated: {self._is_authenticated}")
        print(f"Is in game: {self._is_in_game}")
        print(f"Active connection: {self._active_connection is not None}")
        if self._active_connection:
            print(f"Connection type: {type(self._active_connection)}")

    async def debug_subscription_setup(self) -> None:
        """Debug subscription setup."""
        print(f"Subscribed tables: {self._subscribed_tables}")
        print(f"Subscription states: {self._subscription_states}")
        print(f"Subscription state count: {len(self._subscription_states)}")

    async def debug_table_access(self) -> None:
        """Debug what tables we can actually access."""
        tables_to_test = ['player', 'entity', 'circle', 'food', 'config']
        
        for table in tables_to_test:
            try:
                # Method 1: Check client method access
                if table == 'player':
                    players = self.get_all_players()
                    print(f"get_all_players(): {len(players)} found")
                    if len(players) > 0:
                        print(f"Sample player: {list(players.values())[0]}")
                        
                elif table == 'entity':
                    entities = self.get_all_entities()  
                    print(f"get_all_entities(): {len(entities)} found")
                    if len(entities) > 0:
                        print(f"Sample entity: {list(entities.values())[0]}")
                        
                # Method 2: Check raw cache data
                if table == 'player':
                    print(f"Raw _players cache: {len(self._players)} items")
                    if self._players:
                        print(f"_players keys: {list(self._players.keys())}")
                elif table == 'entity':
                    print(f"Raw _entities cache: {len(self._entities)} items")
                    if self._entities:
                        print(f"_entities keys: {list(self._entities.keys())}")
                        
            except Exception as e:
                print(f"Table {table} access failed: {e}")
                import traceback
                traceback.print_exc()

    async def debug_data_format(self) -> None:
        """Debug the format of received data."""
        # Check if we have any connection to get data from
        if not self._active_connection:
            print("No active connection to check data flow")
            return
            
        # Check cache state
        print(f"Entities cache: {len(self._entities)} items")
        print(f"Players cache: {len(self._players)} items")
        print(f"Circles cache: {len(self._circles)} items")
        
        # Check if connection manager has any data
        if hasattr(self._active_connection, 'get_entities'):
            try:
                conn_entities = self._active_connection.get_entities()
                print(f"Connection entities: {len(conn_entities)} items")
            except Exception as e:
                print(f"Could not get entities from connection: {e}")
                
        if hasattr(self._active_connection, 'get_players'):
            try:
                conn_players = self._active_connection.get_players()
                print(f"Connection players: {len(conn_players)} items")
            except Exception as e:
                print(f"Could not get players from connection: {e}")

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

    def _setup_connection_event_handlers(self) -> None:
        """Set up event handlers to bridge connection data to client state."""
        # Note: This will be called during connect() when we have an active connection
        pass
    
    def _setup_early_event_handlers(self, connection) -> None:
        """Set up event handlers before connection processes messages."""
        try:
            logger.info(f"🚀 Setting up EARLY event handlers on {type(connection)}")
            
            # Register handlers for subscription data
            connection.on('initial_subscription', self._handle_initial_subscription_data)
            connection.on('transaction_update', self._handle_transaction_update_data)
            connection.on('identity_token', self._debug_event_handler)
            connection.on('raw_message', self._debug_event_handler)
            
            # Verify registration
            if hasattr(connection, '_event_callbacks'):
                logger.info(f"🎯 Early event callbacks registered: {list(connection._event_callbacks.keys())}")
                for event, callbacks in connection._event_callbacks.items():
                    logger.info(f"🎯   {event}: {len(callbacks)} callbacks")
            
        except Exception as e:
            logger.error(f"Failed to set up early event handlers: {e}")
            import traceback
            traceback.print_exc()
    
    async def _process_existing_subscription_data(self) -> None:
        """Process any subscription data that was already received during connection setup."""
        try:
            if not self._active_connection:
                return
                
            logger.info("🔄 Checking for existing subscription data to process...")
            
            # Check if the connection has any cached subscription data
            # This is a workaround for the timing issue where InitialSubscription
            # arrives before our event handlers are registered
            
            # Option 1: If connection has stored InitialSubscription data
            if hasattr(self._active_connection, '_last_initial_subscription'):
                logger.info("📦 Found stored InitialSubscription data, processing...")
                await self._handle_initial_subscription_data({
                    'subscription_data': self._active_connection._last_initial_subscription
                })
            
            # Option 2: Try to access SpacetimeDB tables directly via connection
            # This is a fallback to get initial state even if we missed the subscription message
            elif hasattr(self._active_connection, 'get_entities') and hasattr(self._active_connection, 'get_players'):
                logger.info("📊 Attempting to get initial state directly from connection...")
                try:
                    entities = self._active_connection.get_entities()
                    players = self._active_connection.get_players()
                    
                    logger.info(f"📊 Direct connection access: {len(entities)} entities, {len(players)} players")
                    
                    # Manually populate caches if we got data
                    for entity in entities.values():
                        self._entities[entity.entity_id] = entity
                    for player in players.values():
                        self._players[player.player_id] = player
                        
                except Exception as e:
                    logger.debug(f"Direct connection access failed: {e}")
            
            logger.info(f"🔄 After processing existing data: {len(self._players)} players, {len(self._entities)} entities")
            
        except Exception as e:
            logger.error(f"Error processing existing subscription data: {e}")
    
    def _bridge_connection_events(self) -> None:
        """Bridge events from the active connection to populate client state."""
        if not self._active_connection:
            logger.warning("No active connection to bridge events from")
            return
            
        # Set up event handlers on the actual connection object
        if hasattr(self._active_connection, 'on'):
            # Handle subscription data updates
            logger.info(f"🔧 Registering event handler for 'initial_subscription'")
            self._active_connection.on('initial_subscription', self._handle_initial_subscription_data)
            
            logger.info(f"🔧 Registering event handler for 'transaction_update'")
            self._active_connection.on('transaction_update', self._handle_transaction_update_data)
            
            # Add debug handlers to see what events are being triggered
            logger.info(f"🔧 Registering event handler for 'identity_token'")
            self._active_connection.on('identity_token', self._debug_event_handler)
            
            logger.info(f"🔧 Registering event handler for 'raw_message'")
            self._active_connection.on('raw_message', self._debug_event_handler)
            
            # Verify callbacks were registered
            if hasattr(self._active_connection, '_event_callbacks'):
                logger.info(f"🔍 Event callbacks after registration: {list(self._active_connection._event_callbacks.keys())}")
                for event, callbacks in self._active_connection._event_callbacks.items():
                    logger.info(f"🔍   {event}: {len(callbacks)} callbacks")
            
            logger.debug("Set up connection event handlers for data bridging")
        else:
            logger.warning(f"Active connection {type(self._active_connection)} does not support event handling")
    
    async def _debug_event_handler(self, data: Any) -> None:
        """Debug handler to see what events are being triggered."""
        logger.info(f"🔍 Event triggered: {type(data)} - {str(data)[:100]}...")
    
    async def _handle_initial_subscription_data(self, data: Dict[str, Any]) -> None:
        """Handle initial subscription data from connection."""
        try:
            logger.info("🎯 Processing initial subscription data")
            subscription_data = data.get('subscription_data', {})
            
            # Process database_update if present
            if 'database_update' in subscription_data:
                db_update = subscription_data['database_update']
                await self._process_database_update(db_update)
                
        except Exception as e:
            logger.error(f"Error handling initial subscription data: {e}")
    
    async def _handle_transaction_update_data(self, data: Dict[str, Any]) -> None:
        """Handle transaction update data from connection."""
        try:
            logger.debug("Processing transaction update data")
            update_data = data.get('update_data', {})
            
            # Process database_update if present
            if 'database_update' in update_data:
                db_update = update_data['database_update']
                await self._process_database_update(db_update)
                
        except Exception as e:
            logger.error(f"Error handling transaction update data: {e}")
    
    async def _process_database_update(self, db_update: Dict[str, Any]) -> None:
        """Process database update and populate client caches."""
        try:
            # Process table updates
            tables = db_update.get('tables', [])
            
            for table_update in tables:
                table_name = table_update.get('table_name', '').lower()
                
                # Process inserts
                for insert in table_update.get('inserts', []):
                    await self._process_table_insert(table_name, insert)
                
                # Process updates  
                for update in table_update.get('updates', []):
                    await self._process_table_update(table_name, update)
                
                # Process deletes
                for delete in table_update.get('deletes', []):
                    await self._process_table_delete(table_name, delete)
                    
            logger.debug(f"Processed database update - Players: {len(self._players)}, Entities: {len(self._entities)}")
                    
        except Exception as e:
            logger.error(f"Error processing database update: {e}")
            import traceback
            traceback.print_exc()
    
    async def _process_table_insert(self, table_name: str, row_data: Dict[str, Any]) -> None:
        """Process table insert and update client cache."""
        try:
            if table_name in ['player', 'players']:
                # Create GamePlayer object
                player = GamePlayer.from_dict(row_data)
                self._players[player.player_id] = player
                logger.debug(f"Added player {player.player_id} to cache")
                
                # Trigger callback
                for callback in self._callbacks['player_joined']:
                    try:
                        callback(player)
                    except Exception as e:
                        logger.error(f"Error in player_joined callback: {e}")
                        
            elif table_name in ['entity', 'entities']:
                # Create GameEntity object
                entity = GameEntity.from_dict(row_data)
                self._entities[entity.entity_id] = entity
                logger.debug(f"Added entity {entity.entity_id} to cache")
                
                # Trigger callback
                for callback in self._callbacks['entity_created']:
                    try:
                        callback(entity)
                    except Exception as e:
                        logger.error(f"Error in entity_created callback: {e}")
                        
            elif table_name in ['circle', 'circles']:
                # Create GameCircle object
                circle = GameCircle.from_dict(row_data)
                self._circles[circle.circle_id] = circle
                logger.debug(f"Added circle {circle.circle_id} to cache")
                
        except Exception as e:
            logger.error(f"Error processing {table_name} insert: {e}")
    
    async def _process_table_update(self, table_name: str, update_data: Dict[str, Any]) -> None:
        """Process table update and update client cache."""
        try:
            # Similar to insert but for updates
            if table_name in ['player', 'players']:
                player = GamePlayer.from_dict(update_data)
                old_player = self._players.get(player.player_id)
                self._players[player.player_id] = player
                
                # Trigger callback with old and new
                for callback in self._callbacks.get('player_updated', []):
                    try:
                        callback(old_player, player)
                    except Exception as e:
                        logger.error(f"Error in player_updated callback: {e}")
                        
            elif table_name in ['entity', 'entities']:
                entity = GameEntity.from_dict(update_data)
                old_entity = self._entities.get(entity.entity_id)
                self._entities[entity.entity_id] = entity
                
                # Trigger callback
                for callback in self._callbacks['entity_updated']:
                    try:
                        callback(old_entity, entity)
                    except Exception as e:
                        logger.error(f"Error in entity_updated callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing {table_name} update: {e}")
    
    async def _process_table_delete(self, table_name: str, delete_data: Dict[str, Any]) -> None:
        """Process table delete and remove from client cache."""
        try:
            if table_name in ['player', 'players']:
                player_id = delete_data.get('player_id')
                if player_id and player_id in self._players:
                    player = self._players.pop(player_id)
                    
                    # Trigger callback
                    for callback in self._callbacks['player_left']:
                        try:
                            callback(player)
                        except Exception as e:
                            logger.error(f"Error in player_left callback: {e}")
                            
            elif table_name in ['entity', 'entities']:
                entity_id = delete_data.get('entity_id')
                if entity_id and entity_id in self._entities:
                    entity = self._entities.pop(entity_id)
                    
                    # Trigger callback
                    for callback in self._callbacks['entity_destroyed']:
                        try:
                            callback(entity)
                        except Exception as e:
                            logger.error(f"Error in entity_destroyed callback: {e}")
                            
        except Exception as e:
            logger.error(f"Error processing {table_name} delete: {e}")

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