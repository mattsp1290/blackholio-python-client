"""
Modernized SpacetimeDB Client Implementation

This module provides a wrapper around the modernized spacetimedb-python-sdk
while maintaining compatibility with the existing blackholio-client API.

This allows for a gradual migration while preserving all existing functionality.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Union

# Import from the modernized SDK
from spacetimedb_sdk import (
    ModernSpacetimeDBClient,
    create_rust_client,
    create_python_client,
    create_csharp_client,
    create_go_client,
    ServerConfig as SDKServerConfig,
    get_connection_manager,
    get_event_manager,
    ConnectionState as SDKConnectionState,
    EventType,
    ConnectionEvent,
    TableUpdateEvent,
    ReducerCallEvent,
    ErrorEvent,
    subscribe_to_events
)

from ..config.environment import EnvironmentConfig
from ..exceptions.connection_errors import (
    BlackholioConnectionError,
    ServerConfigurationError,
    SpacetimeDBError,
    ConnectionLostError,
    TimeoutError as BlackholioTimeoutError
)
from .server_config import ServerConfig


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration (compatible with existing API)."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ModernizedSpacetimeDBConnection:
    """
    Modernized SpacetimeDB connection that wraps the enhanced SDK
    while maintaining compatibility with existing blackholio-client API.
    
    This class eliminates the duplicate SpacetimeDB implementation by
    using the modernized SDK under the hood.
    """
    
    def __init__(self, config: ServerConfig):
        """
        Initialize the modernized connection.
        
        Args:
            config: Server configuration (existing format)
        """
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        
        # Convert to SDK server config
        self._sdk_server_config = self._convert_to_sdk_config(config)
        
        # Get SDK client based on server language
        self._sdk_client: Optional[ModernSpacetimeDBClient] = None
        
        # Connection statistics (maintain existing API)
        self._connection_start_time: Optional[float] = None
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_sent = 0
        self._bytes_received = 0
        self._reconnect_attempts = 0
        
        # Event callbacks (maintain existing API)
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        # Setup event monitoring (defer until connect is called)
        self._event_monitoring_setup = False
        
        logger.info(f"Initialized modernized SpacetimeDB connection for {config.language} server")
    
    def _convert_to_sdk_config(self, config: ServerConfig) -> SDKServerConfig:
        """Convert blackholio ServerConfig to SDK ServerConfig."""
        from spacetimedb_sdk.factory.base import ServerLanguage, OptimizationProfile
        
        # Map language strings to SDK enums
        language_map = {
            'rust': ServerLanguage.RUST,
            'python': ServerLanguage.PYTHON,
            'csharp': ServerLanguage.CSHARP,
            'go': ServerLanguage.GO
        }
        
        sdk_language = language_map.get(config.language.lower(), ServerLanguage.RUST)
        
        return SDKServerConfig(
            language=sdk_language,
            host=config.host,
            port=config.port,
            database=config.db_identity,  # Use db_identity instead of database_name
            auth_token=getattr(config, 'auth_token', None),
            optimization_profile=OptimizationProfile.BALANCED,
            additional_config={
                'original_config': config.__dict__
            }
        )
    
    def _setup_event_monitoring(self):
        """Setup event monitoring to track connection state changes."""
        def on_connection_event(event):
            """Handle connection events from the SDK."""
            if event.state == "connected":
                self.state = ConnectionState.CONNECTED
                self._trigger_callback('connected', {'event': event})
            elif event.state == "disconnected":
                self.state = ConnectionState.DISCONNECTED
                self._trigger_callback('disconnected', {'event': event})
            elif event.state == "connecting":
                self.state = ConnectionState.CONNECTING
            elif event.state == "failed":
                self.state = ConnectionState.FAILED
                self._trigger_callback('error', {'event': event})
        
        def on_table_update(event):
            """Handle table update events."""
            self._trigger_callback('table_update', {
                'table': event.table_name,
                'operation': event.operation,
                'data': event.row_data
            })
        
        def on_error_event(event):
            """Handle error events."""
            self._trigger_callback('error', {
                'error': event.error_message,
                'type': event.error_type
            })
        
        # Subscribe to SDK events
        subscribe_to_events(on_connection_event, [EventType.CONNECTION], "blackholio_connection")
        subscribe_to_events(on_table_update, [EventType.TABLE_UPDATE], "blackholio_table_updates")
        subscribe_to_events(on_error_event, [EventType.ERROR], "blackholio_errors")
    
    async def connect(self) -> bool:
        """
        Connect to SpacetimeDB server using the modernized SDK.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.state = ConnectionState.CONNECTING
            
            # Setup event monitoring if not already done
            if not self._event_monitoring_setup:
                self._setup_event_monitoring()
                self._event_monitoring_setup = True
            
            # Create SDK client based on server language
            if self._sdk_server_config.language.value == 'rust':
                self._sdk_client = create_rust_client(
                    host=self._sdk_server_config.host,
                    database=self._sdk_server_config.database,
                    auth_token=self._sdk_server_config.auth_token
                )
            elif self._sdk_server_config.language.value == 'python':
                self._sdk_client = create_python_client(
                    host=self._sdk_server_config.host,
                    database=self._sdk_server_config.database,
                    auth_token=self._sdk_server_config.auth_token
                )
            elif self._sdk_server_config.language.value == 'csharp':
                self._sdk_client = create_csharp_client(
                    host=self._sdk_server_config.host,
                    database=self._sdk_server_config.database,
                    auth_token=self._sdk_server_config.auth_token
                )
            elif self._sdk_server_config.language.value == 'go':
                self._sdk_client = create_go_client(
                    host=self._sdk_server_config.host,
                    database=self._sdk_server_config.database,
                    auth_token=self._sdk_server_config.auth_token
                )
            else:
                raise ServerConfigurationError(f"Unsupported server language: {self._sdk_server_config.language}")
            
            # Connect using the SDK
            await self._sdk_client.connect()
            
            if self._sdk_client.is_connected:
                self.state = ConnectionState.CONNECTED
                self._connection_start_time = asyncio.get_event_loop().time()
                logger.info(f"Successfully connected to {self.config.language} server")
                return True
            else:
                self.state = ConnectionState.FAILED
                return False
                
        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(f"Failed to connect to SpacetimeDB: {e}")
            raise BlackholioConnectionError(f"Connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from the SpacetimeDB server."""
        try:
            if self._sdk_client:
                await self._sdk_client.disconnect()
            self.state = ConnectionState.DISCONNECTED
            logger.info("Disconnected from SpacetimeDB server")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            raise BlackholioConnectionError(f"Disconnect failed: {e}") from e
    
    async def subscribe(self, query: str, callback: Optional[Callable] = None) -> str:
        """
        Subscribe to a query (compatible with existing API).
        
        Args:
            query: SQL query to subscribe to
            callback: Optional callback for subscription updates
            
        Returns:
            Subscription ID
        """
        if not self._sdk_client:
            raise BlackholioConnectionError("Not connected to server")
        
        try:
            # Use SDK subscription functionality
            subscription_id = await self._sdk_client.subscribe(query)
            
            if callback:
                # Register callback for this subscription
                self.on('table_update', callback)
            
            return subscription_id
            
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            raise BlackholioConnectionError(f"Subscription failed: {e}") from e
    
    async def call_reducer(self, reducer_name: str, args: List[Any]) -> Any:
        """
        Call a reducer function (compatible with existing API).
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            
        Returns:
            Reducer result
        """
        if not self._sdk_client:
            raise BlackholioConnectionError("Not connected to server")
        
        try:
            result = await self._sdk_client.call_reducer(reducer_name, *args)
            self._messages_sent += 1
            return result
            
        except Exception as e:
            logger.error(f"Reducer call failed: {e}")
            raise BlackholioConnectionError(f"Reducer call failed: {e}") from e
    
    def on(self, event: str, callback: Callable) -> None:
        """Register an event callback (maintain existing API)."""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, data: Any) -> None:
        """Trigger event callbacks."""
        callbacks = self._event_callbacks.get(event, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in event callback for {event}: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.state == ConnectionState.CONNECTED and self._sdk_client and self._sdk_client.is_connected
    
    @property
    def connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics (maintain existing API)."""
        uptime = 0
        if self._connection_start_time:
            uptime = asyncio.get_event_loop().time() - self._connection_start_time
        
        return {
            'state': self.state.value,
            'uptime': uptime,
            'messages_sent': self._messages_sent,
            'messages_received': self._messages_received,
            'bytes_sent': self._bytes_sent,
            'bytes_received': self._bytes_received,
            'reconnect_attempts': self._reconnect_attempts,
            'sdk_client_type': type(self._sdk_client).__name__ if self._sdk_client else None
        }
    
    async def ping(self) -> bool:
        """Ping the server to check connection health."""
        if not self._sdk_client:
            return False
        
        try:
            # Use SDK ping if available, otherwise check connection state
            if hasattr(self._sdk_client, 'ping'):
                return await self._sdk_client.ping()
            else:
                return self._sdk_client.is_connected
        except Exception:
            return False


# Alias for backward compatibility
BlackholioClient = ModernizedSpacetimeDBConnection


def create_modernized_client(config: ServerConfig) -> ModernizedSpacetimeDBConnection:
    """
    Create a modernized client instance.
    
    Args:
        config: Server configuration
        
    Returns:
        ModernizedSpacetimeDBConnection instance
    """
    return ModernizedSpacetimeDBConnection(config)


__all__ = [
    'ModernizedSpacetimeDBConnection',
    'BlackholioClient',
    'ConnectionState',
    'create_modernized_client'
]