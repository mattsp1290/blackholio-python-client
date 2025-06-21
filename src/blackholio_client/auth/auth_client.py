"""
Authenticated Client - High-level SpacetimeDB Client with Authentication

Provides an authenticated client interface that handles identity management,
token authentication, and secure connections to SpacetimeDB.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union, Callable
from pathlib import Path

from .identity_manager import IdentityManager, Identity, get_identity_manager
from .token_manager import TokenManager, AuthToken, get_token_manager
from ..connection.spacetimedb_connection import SpacetimeDBConnection, ConnectionState
from ..connection.server_config import ServerConfig
from ..config.environment import EnvironmentConfig
from ..exceptions.connection_errors import (
    AuthenticationError,
    BlackholioConnectionError,
    ServerConfigurationError
)


logger = logging.getLogger(__name__)


class AuthenticatedClient:
    """
    High-level authenticated client for SpacetimeDB.
    
    Combines connection management, identity handling, and token authentication
    into a single easy-to-use interface for Blackholio game integration.
    """
    
    def __init__(self, 
                 identity_name: Optional[str] = None,
                 identity_dir: Optional[Union[str, Path]] = None,
                 server_config: Optional[ServerConfig] = None,
                 auto_create_identity: bool = True,
                 auto_refresh_tokens: bool = True):
        """
        Initialize authenticated client.
        
        Args:
            identity_name: Name of identity to use (default: "default")
            identity_dir: Directory for identity storage
            server_config: Server configuration (uses environment if None)
            auto_create_identity: Create identity if it doesn't exist
            auto_refresh_tokens: Enable automatic token refresh
        """
        self.identity_name = identity_name or "default"
        self.auto_create_identity = auto_create_identity
        
        # Initialize managers
        self.identity_manager = get_identity_manager(identity_dir)
        self.token_manager = get_token_manager(auto_refresh_tokens)
        
        # Server configuration
        if server_config is None:
            env_config = EnvironmentConfig.from_environment()
            self.server_config = env_config.get_server_config()
        else:
            self.server_config = server_config
        
        # Connection
        self.connection = SpacetimeDBConnection(self.server_config)
        
        # Current identity and token
        self._current_identity: Optional[Identity] = None
        self._current_token: Optional[AuthToken] = None
        
        # Authentication state
        self._authenticated = False
        self._authentication_lock = asyncio.Lock()
        
        # Event callbacks
        self._auth_callbacks: Dict[str, Callable] = {}
        
        # Setup connection event handlers
        self._setup_connection_handlers()
        
        logger.info(f"Authenticated client initialized for identity: {self.identity_name}")
    
    async def connect_and_authenticate(self, timeout: float = 60.0) -> bool:
        """
        Connect to SpacetimeDB and authenticate.
        
        Args:
            timeout: Connection and authentication timeout
            
        Returns:
            True if connected and authenticated successfully
        """
        async with self._authentication_lock:
            try:
                # Load or create identity
                await self._ensure_identity()
                
                # Connect to server
                logger.info("Connecting to SpacetimeDB...")
                connected = await self.connection.connect()
                
                if not connected:
                    raise BlackholioConnectionError("Failed to establish connection")
                
                # Wait for connection to be fully established
                connected = await self.connection.wait_until_connected(timeout=10.0)
                if not connected:
                    raise BlackholioConnectionError("Connection not established in time")
                
                # Authenticate
                logger.info("Authenticating with SpacetimeDB...")
                authenticated = await self._authenticate(timeout=timeout-10.0)
                
                if authenticated:
                    self._authenticated = True
                    logger.info("Successfully connected and authenticated")
                    await self._trigger_auth_callback('authenticated', {
                        'identity': self._current_identity.name,
                        'server': self.server_config.language
                    })
                    return True
                else:
                    await self.connection.disconnect()
                    raise AuthenticationError("Authentication failed")
                
            except Exception as e:
                logger.error(f"Connection and authentication failed: {e}")
                await self._trigger_auth_callback('auth_failed', {'error': str(e)})
                return False
    
    async def disconnect(self):
        """Disconnect from SpacetimeDB."""
        async with self._authentication_lock:
            try:
                # Clear authentication state
                self._authenticated = False
                
                # Disconnect
                await self.connection.disconnect()
                
                # Clear current token
                if self._current_identity:
                    self.token_manager.remove_token(self._current_identity)
                
                self._current_token = None
                
                logger.info("Disconnected from SpacetimeDB")
                await self._trigger_auth_callback('disconnected', {})
                
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    async def send_authenticated_request(self, message_type: str, data: Dict[str, Any], 
                                       timeout: float = 30.0) -> Any:
        """
        Send authenticated request to SpacetimeDB.
        
        Args:
            message_type: Type of message to send
            data: Message data
            timeout: Request timeout
            
        Returns:
            Response data
            
        Raises:
            AuthenticationError: If not authenticated
            BlackholioConnectionError: If connection failed
        """
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        if not self._current_token or not self._current_token.is_valid:
            # Try to refresh token
            if not await self._refresh_authentication():
                raise AuthenticationError("Token expired and refresh failed")
        
        # Add authentication to request
        auth_data = data.copy()
        auth_data['authorization'] = self._current_token.get_authorization_header()
        
        # Send request
        return await self.connection.send_request(message_type, auth_data, timeout)
    
    async def enter_game_authenticated(self, player_name: str) -> bool:
        """
        Enter game with authentication.
        
        Args:
            player_name: Player name for the game
            
        Returns:
            True if entered successfully
        """
        try:
            response = await self.send_authenticated_request('enter_game', {
                'player_name': player_name,
                'identity_id': self._current_identity.identity_id
            })
            
            logger.info(f"Entered game as {player_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enter game: {e}")
            return False
    
    async def _ensure_identity(self):
        """Ensure identity exists and is loaded."""
        # Try to load existing identity
        identity = self.identity_manager.load_identity(self.identity_name)
        
        if identity is None:
            if self.auto_create_identity:
                logger.info(f"Creating new identity: {self.identity_name}")
                identity = self.identity_manager.create_identity(
                    self.identity_name,
                    metadata={
                        'created_by': 'authenticated_client',
                        'server': self.server_config.language
                    }
                )
            else:
                raise AuthenticationError(f"Identity '{self.identity_name}' not found")
        
        self._current_identity = identity
        
        # Update last used timestamp
        self.identity_manager.update_last_used(self.identity_name)
        
        logger.info(f"Using identity: {identity.name} (ID: {identity.identity_id})")
    
    async def _authenticate(self, timeout: float = 30.0) -> bool:
        """Authenticate with the server."""
        if not self._current_identity:
            raise AuthenticationError("No identity available")
        
        try:
            # Check for existing valid token
            existing_token = self.token_manager.get_valid_token(self._current_identity)
            if existing_token:
                self._current_token = existing_token
                logger.info("Using existing valid token")
                return True
            
            # Perform authentication
            token = await self.token_manager.authenticate_with_identity(
                self._current_identity
            )
            
            if token and token.is_valid:
                self._current_token = token
                logger.info("Authentication successful")
                return True
            else:
                logger.error("Authentication failed - invalid token received")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def _refresh_authentication(self) -> bool:
        """Refresh authentication token."""
        if not self._current_identity:
            return False
        
        try:
            # Try to get refreshed token
            token = self.token_manager.get_valid_token(self._current_identity)
            if token:
                self._current_token = token
                return True
            
            # Re-authenticate if refresh failed
            return await self._authenticate()
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    def _setup_connection_handlers(self):
        """Setup connection event handlers."""
        self.connection.on('connected', self._on_connection_connected)
        self.connection.on('disconnected', self._on_connection_disconnected)
        self.connection.on('connection_failed', self._on_connection_failed)
        self.connection.on('reconnecting', self._on_connection_reconnecting)
    
    async def _on_connection_connected(self, data: Dict[str, Any]):
        """Handle connection established event."""
        logger.debug("Connection established")
        await self._trigger_auth_callback('connection_established', data)
    
    async def _on_connection_disconnected(self, data: Dict[str, Any]):
        """Handle connection lost event."""
        logger.debug("Connection lost")
        self._authenticated = False
        await self._trigger_auth_callback('connection_lost', data)
    
    async def _on_connection_failed(self, data: Dict[str, Any]):
        """Handle connection failed event."""
        logger.debug("Connection failed")
        self._authenticated = False
        await self._trigger_auth_callback('connection_failed', data)
    
    async def _on_connection_reconnecting(self, data: Dict[str, Any]):
        """Handle reconnection attempt event."""
        logger.debug("Reconnecting...")
        await self._trigger_auth_callback('reconnecting', data)
    
    def on_auth_event(self, event: str, callback: Callable):
        """
        Register callback for authentication events.
        
        Events: authenticated, auth_failed, disconnected, connection_established,
               connection_lost, connection_failed, reconnecting
        """
        self._auth_callbacks[event] = callback
    
    async def _trigger_auth_callback(self, event: str, data: Dict[str, Any]):
        """Trigger authentication event callback."""
        callback = self._auth_callbacks.get(event)
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Auth callback error for {event}: {e}")
    
    # Delegate connection methods
    def on(self, event: str, callback: Callable):
        """Register event callback (delegates to connection)."""
        self.connection.on(event, callback)
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.connection.is_connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._authenticated and self._current_token and self._current_token.is_valid
    
    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.connection.state
    
    @property
    def current_identity(self) -> Optional[Identity]:
        """Get current identity."""
        return self._current_identity
    
    @property
    def current_token(self) -> Optional[AuthToken]:
        """Get current authentication token."""
        return self._current_token
    
    @property
    def connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        stats = self.connection.connection_stats
        stats.update({
            'authenticated': self._authenticated,
            'identity_name': self.identity_name,
            'identity_id': self._current_identity.identity_id if self._current_identity else None,
            'token_valid': self._current_token.is_valid if self._current_token else False
        })
        return stats
    
    async def shutdown(self):
        """Shutdown client and cleanup resources."""
        await self.disconnect()
        await self.token_manager.shutdown()
        logger.info("Authenticated client shutdown complete")