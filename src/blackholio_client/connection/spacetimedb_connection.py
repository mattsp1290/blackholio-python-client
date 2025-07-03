"""
SpacetimeDB Connection - Unified Client Implementation

Consolidates connection logic from blackholio-agent and client-pygame
into a single, robust implementation supporting multiple server languages.
"""

import asyncio
import json
import logging
import os
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Union
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException, InvalidStatus
from websockets.client import WebSocketClientProtocol
from spacetimedb_sdk.protocol_helpers import (
    SpacetimeDBProtocolHelper,
    get_json_protocol_subprotocol
)
# Import protocol validation from the enhanced SDK
SDK_VALIDATION_AVAILABLE = False
validate_protocol_version = None
check_protocol_compatibility = None
ProtocolDecoder = None

try:
    from spacetimedb_sdk.protocol import (
        validate_protocol_version, 
        check_protocol_compatibility,
        ProtocolDecoder
    )
    SDK_VALIDATION_AVAILABLE = True
except ImportError:
    # Fallback for older SDK versions
    pass

from ..config.environment import EnvironmentConfig
from ..models.game_entities import GameEntity, GamePlayer, GameCircle, Vector2
from ..exceptions.connection_errors import (
    BlackholioConnectionError,
    ServerConfigurationError,
    SpacetimeDBError,
    ConnectionLostError,
    TimeoutError as BlackholioTimeoutError,
    AuthenticationError,
    create_connection_timeout_error
)
from .server_config import ServerConfig
from .protocol_handlers import V112ProtocolHandler


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class SpacetimeDBConnection:
    """
    Core SpacetimeDB connection class that consolidates the duplicate
    connection logic from both blackholio-agent and client-pygame.
    
    Supports SpacetimeDB v1.1.2 protocol with multi-server-language capability.
    """
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        self.protocol_handler = V112ProtocolHandler()
        
        # Initialize JSON protocol helper with validation
        self.protocol_helper = SpacetimeDBProtocolHelper(use_binary=False)
        
        # Enhanced protocol decoder for better message type recognition
        if SDK_VALIDATION_AVAILABLE:
            self.protocol_decoder = ProtocolDecoder(use_binary=False)
        else:
            self.protocol_decoder = None
            
        # Protocol validation state
        self._protocol_validated = False
        self._protocol_version = "v1.json.spacetimedb"
        
        # JWT Authentication state
        self._identity = None
        self._auth_token = None
        self._credentials_file = Path.home() / '.spacetimedb' / 'credentials.json'
        
        # Connection state
        self._connection_lock = asyncio.Lock()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0
        self._connection_timeout = 30.0
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        # Message handling
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._message_handler_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat_time = 0
        self._heartbeat_interval = 30.0
        self._heartbeat_timeout = 10.0
        
        # Request tracking for correlation
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        
        # Connection statistics
        self._connection_start_time: Optional[float] = None
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_sent = 0
        self._bytes_received = 0
        
        # Connection state synchronization
        self._connection_ready = False
        self._subscriptions_active = False
        self._last_data_received: Optional[float] = None
        self._subscription_tables: List[str] = []
        self._last_initial_subscription: Optional[Dict[str, Any]] = None  # Store InitialSubscription for later
        
        logger.info(f"Initialized SpacetimeDB connection for {config.language} server at {config.host}")
        if not SDK_VALIDATION_AVAILABLE:
            logger.warning("Enhanced SDK protocol validation not available - using basic validation")
    
    async def connect(self) -> bool:
        """
        Connect to SpacetimeDB server with retry logic.
        Consolidates connection patterns from both existing implementations.
        """
        async with self._connection_lock:
            if self.state == ConnectionState.CONNECTED:
                logger.warning("Already connected to SpacetimeDB")
                return True
            
            if self.state == ConnectionState.CONNECTING:
                logger.warning("Connection already in progress")
                return False
            
            self.state = ConnectionState.CONNECTING
            
            try:
                # Try to load existing credentials
                await self._load_credentials()
                
                # Build WebSocket URL
                ws_url = self._build_websocket_url()
                logger.info(f"🔗 [TIMING] Starting WebSocket connection attempt to {ws_url}")
                connection_start_time = time.time()
                
                # Attempt connection with authentication
                logger.info(f"🔗 [TIMING] Attempting authentication")
                success = await self._connect_with_auth(ws_url)
                
                if success:
                    auth_time = time.time() - connection_start_time
                    logger.info(f"🔗 [TIMING] WebSocket connected and authenticated in {auth_time:.3f}s")
                
                if not success:
                    self.state = ConnectionState.FAILED
                    return False
                
                # Record connection time
                self._connection_start_time = time.time()
                
                # Set state to connected before starting tasks
                self.state = ConnectionState.CONNECTED
                self._reconnect_attempts = 0
                
                # Start message handler and heartbeat
                logger.info(f"🔗 [TIMING] Starting message processing loop")
                message_handler_start_time = time.time()
                
                self._message_handler_task = asyncio.create_task(
                    self._message_handler(),
                    name="message_handler"
                )
                self._heartbeat_task = asyncio.create_task(
                    self._heartbeat_handler(),
                    name="heartbeat_handler"
                )
                
                logger.info(f"🔗 [TIMING] Message handler started in {time.time() - message_handler_start_time:.3f}s")
                
                # Send initial subscription request
                logger.info(f"🔗 [TIMING] Sending initial subscription request")
                subscription_start_time = time.time()
                await self._send_subscription_request()
                logger.info(f"🔗 [TIMING] Subscription request sent in {time.time() - subscription_start_time:.3f}s")
                
                # Wait for subscription data to start flowing
                logger.info(f"🔗 [TIMING] Waiting for subscription data...")
                subscription_wait_start = time.time()
                subscription_ready = await self.wait_for_subscription_data(timeout=5.0)
                subscription_wait_time = time.time() - subscription_wait_start
                
                if subscription_ready:
                    logger.info(f"🔗 [TIMING] Subscription data received in {subscription_wait_time:.3f}s")
                else:
                    logger.warning(f"🔗 [TIMING] Subscription data timeout after {subscription_wait_time:.3f}s - subscriptions may not be working")
                
                total_connection_time = time.time() - connection_start_time
                identity_info = f" with identity: {self._identity}" if self._identity else ""
                logger.info(f"✅ [TIMING] Total connection time: {total_connection_time:.3f}s")
                logger.info(f"Successfully connected to SpacetimeDB{identity_info} - subscriptions {'active' if subscription_ready else 'pending'}")
                await self._trigger_event('connected', {
                    'server': self.config.language,
                    'url': ws_url,
                    'identity': self._identity,
                    'timestamp': time.time()
                })
                
                return True
                
            except asyncio.TimeoutError:
                self.state = ConnectionState.FAILED
                error = create_connection_timeout_error(
                    self._connection_timeout,
                    "initial_connection"
                )
                logger.error(f"Connection timeout: {error}")
                await self._handle_connection_error(error)
                return False
                
            except Exception as e:
                self.state = ConnectionState.FAILED
                logger.error(f"Failed to connect to SpacetimeDB: {e}")
                await self._handle_connection_error(e)
                return False
    
    async def disconnect(self):
        """Gracefully disconnect from SpacetimeDB server."""
        async with self._connection_lock:
            if self.state == ConnectionState.DISCONNECTED:
                return
            
            logger.info("Disconnecting from SpacetimeDB")
            previous_state = self.state
            
            # Set state to disconnecting to prevent new operations
            self.state = ConnectionState.DISCONNECTED
            
            # Step 1: Stop sending new messages by cancelling heartbeat first
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None
            
            # Step 2: Send proper WebSocket close frame before closing connection
            if self.websocket and self._is_websocket_open():
                try:
                    # Send a proper close frame with normal closure code
                    await self._send_close_frame()
                    logger.debug("Sent WebSocket close frame")
                except Exception as e:
                    logger.warning(f"Failed to send close frame: {e}")
            
            # Step 3: Close WebSocket with proper timeout
            if self.websocket:
                try:
                    # Use close with reason code for clean shutdown
                    await self.websocket.close(code=1000, reason="Normal closure")
                    logger.debug("WebSocket closed with normal closure code")
                except Exception as e:
                    logger.warning(f"Error during websocket close: {e}")
                finally:
                    self.websocket = None
            
            # Step 4: Cancel remaining tasks after WebSocket is closed
            if self._message_handler_task:
                self._message_handler_task.cancel()
                try:
                    await self._message_handler_task
                except asyncio.CancelledError:
                    pass
                self._message_handler_task = None
            
            # Step 5: Cancel all pending requests
            for request_id, future in self._pending_requests.items():
                if not future.done():
                    future.cancel()
            self._pending_requests.clear()
            
            # Calculate connection duration
            duration = None
            if self._connection_start_time:
                duration = time.time() - self._connection_start_time
                self._connection_start_time = None
            
            await self._trigger_event('disconnected', {
                'previous_state': previous_state.value,
                'duration': duration,
                'messages_sent': self._messages_sent,
                'messages_received': self._messages_received,
                'bytes_sent': self._bytes_sent,
                'bytes_received': self._bytes_received
            })
            
            # Reset statistics
            self._messages_sent = 0
            self._messages_received = 0
            self._bytes_sent = 0
            self._bytes_received = 0
            
            logger.info("Disconnected from SpacetimeDB")
    
    def _build_websocket_url(self) -> str:
        """Build WebSocket URL based on server configuration."""
        protocol = "wss" if self.config.use_ssl else "ws"
        # Check if host already includes port
        if ':' in self.config.host:
            # Host already includes port, don't add it again
            return f"{protocol}://{self.config.host}/v1/database/{self.config.db_identity}/subscribe"
        else:
            # Host doesn't include port, add it if available
            port_part = f":{self.config.port}" if self.config.port else ""
            return f"{protocol}://{self.config.host}{port_part}/v1/database/{self.config.db_identity}/subscribe"
    
    async def _connect_with_auth(self, url: str) -> bool:
        """Attempt connection with JWT authentication handling."""
        try:
            # Prepare headers
            headers = {}
            if self._auth_token:
                headers['Authorization'] = f'Bearer {self._auth_token}'
                logger.debug("Using cached authentication token")
            
            # Validate protocol configuration first
            if SDK_VALIDATION_AVAILABLE and not validate_protocol_version(self._protocol_version):
                logger.warning(f"Unsupported protocol version: {self._protocol_version}")
                
            # Use JSON protocol - requires v1.json.spacetimedb subprotocol
            subprotocols = ["v1.json.spacetimedb"]
            logger.debug(f"Requesting subprotocol: {subprotocols[0]}")
            
            if headers:
                connect_task = websockets.connect(
                    url,
                    subprotocols=subprotocols,
                    additional_headers=headers,
                    ping_interval=self._heartbeat_interval,
                    ping_timeout=self._heartbeat_timeout,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024  # 10MB max message size
                )
            else:
                connect_task = websockets.connect(
                    url,
                    subprotocols=subprotocols,
                    ping_interval=self._heartbeat_interval,
                    ping_timeout=self._heartbeat_timeout,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024  # 10MB max message size
                )
            
            self.websocket = await asyncio.wait_for(
                connect_task,
                timeout=self._connection_timeout
            )
            
            # Validate negotiated protocol
            negotiated_protocol = await self.negotiate_protocol()
            if not negotiated_protocol:
                logger.warning("Failed to negotiate protocol with server")
                    
            logger.info(f"Connected to SpacetimeDB at {url}")
            return True
            
        except InvalidStatus as e:
            # Check if this is a 400 response (authentication required)
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            
            if status_code == 400 or '400' in str(e):
                # Check if this is an authentication requirement
                headers = {}
                if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    headers = dict(e.response.headers)
                
                if 'spacetime-identity' in headers and 'spacetime-identity-token' in headers:
                    # Authentication handshake required
                    logger.debug("Received 400 with JWT credentials - performing authentication handshake")
                    return await self._handle_auth_handshake(url, e)
                else:
                    # Different 400 error (e.g., database not found)
                    logger.error(f"Database connection failed: {e}")
                    raise BlackholioConnectionError(f"Database connection failed: {e}")
            else:
                logger.error(f"Connection failed with status {status_code or 'unknown'}")
                raise BlackholioConnectionError(f"Connection failed with status {status_code or 'unknown'}")
                
        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            return False
    
    async def _handle_auth_handshake(self, url: str, error_response: InvalidStatus) -> bool:
        """Handle the JWT authentication handshake."""
        try:
            # Extract credentials from 400 response headers
            headers = {}
            if hasattr(error_response, 'response') and hasattr(error_response.response, 'headers'):
                headers = dict(error_response.response.headers)
            
            # Log available headers for debugging
            logger.debug(f"Available headers: {list(headers.keys())}")
            
            identity = headers.get('spacetime-identity')
            token = headers.get('spacetime-identity-token')
            
            if not token or not identity:
                logger.error("No authentication token in 400 response")
                logger.debug(f"Available headers: {list(headers.keys())}")
                raise AuthenticationError("Server requires authentication but no token provided")
            
            logger.debug(f"Received identity: {identity}")
            logger.debug(f"Received token: {token[:20]}...")
            
            # Store credentials
            self._identity = identity
            self._auth_token = token
            await self._store_credentials()
            
            # Retry connection with authentication and JSON protocol
            auth_headers = {'Authorization': f'Bearer {token}'}
            subprotocols = ["v1.json.spacetimedb"]
            
            connect_task = websockets.connect(
                url,
                subprotocols=subprotocols,
                additional_headers=auth_headers,
                ping_interval=self._heartbeat_interval,
                ping_timeout=self._heartbeat_timeout,
                close_timeout=10,
                max_size=10 * 1024 * 1024
            )
            
            self.websocket = await asyncio.wait_for(
                connect_task,
                timeout=self._connection_timeout
            )
            
            # Validate negotiated protocol after authentication
            negotiated_protocol = await self.negotiate_protocol()
            
            logger.info(f"Authentication successful - connected with identity: {identity}, protocol: {negotiated_protocol}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication handshake failed: {e}")
            raise AuthenticationError(f"Authentication handshake failed: {e}")
    
    async def _load_credentials(self):
        """Load stored credentials if available and not expired."""
        if not self._credentials_file.exists():
            logger.debug("No credential file found")
            return
        
        try:
            with open(self._credentials_file, 'r') as f:
                data = json.load(f)
            
            # Create key for this host/database combination
            key = f"{self.config.host}:{self.config.db_identity}"
            
            if key in data:
                cred = data[key]
                
                # Check if credentials are expired (24 hour default)
                timestamp = cred.get('timestamp', 0)
                if time.time() - timestamp < 24 * 3600:  # 24 hours
                    self._identity = cred.get('identity')
                    self._auth_token = cred.get('token')
                    logger.debug(f"Loaded credentials for {key}")
                else:
                    logger.debug(f"Credentials expired for {key}")
            else:
                logger.debug(f"No credentials found for {key}")
                
        except Exception as e:
            logger.debug(f"Failed to load credentials: {e}")
    
    async def negotiate_protocol(self) -> Optional[str]:
        """
        Negotiate protocol version with server.
        
        Returns:
            Negotiated protocol version or None if negotiation fails
        """
        if not self.websocket:
            logger.error("Cannot negotiate protocol without active websocket connection")
            return None
            
        try:
            # Check negotiated subprotocol
            negotiated_protocol = getattr(self.websocket, 'subprotocol', None)
            
            if negotiated_protocol:
                logger.info(f"Negotiated protocol: {negotiated_protocol}")
                
                # Update protocol mode based on negotiation
                if negotiated_protocol == "v1.json.spacetimedb":
                    self._protocol_version = negotiated_protocol
                    self._protocol_validated = True
                    # Ensure we're using JSON mode
                    if hasattr(self.protocol_helper, 'use_binary'):
                        self.protocol_helper.use_binary = False
                elif negotiated_protocol == "v1.bsatn.spacetimedb":
                    logger.warning("Server negotiated binary protocol but client is configured for JSON")
                    self._protocol_version = negotiated_protocol
                    # We could switch to binary mode here if needed
                else:
                    logger.warning(f"Unknown negotiated protocol: {negotiated_protocol}")
                    
                return negotiated_protocol
            else:
                logger.warning("No protocol negotiated with server")
                return None
                
        except Exception as e:
            logger.error(f"Error during protocol negotiation: {e}")
            return None
    
    async def _store_credentials(self):
        """Store credentials for reuse."""
        if not self._identity or not self._auth_token:
            return
        
        try:
            # Ensure directory exists
            self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing data
            data = {}
            if self._credentials_file.exists():
                with open(self._credentials_file, 'r') as f:
                    data = json.load(f)
            
            # Store credentials with key
            key = f"{self.config.host}:{self.config.db_identity}"
            data[key] = {
                'identity': self._identity,
                'token': self._auth_token,
                'host': self.config.host,
                'database': self.config.db_identity,
                'timestamp': time.time()
            }
            
            # Save to file
            with open(self._credentials_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Stored credentials for {key}")
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
    
    
    async def _send_subscription_request(self):
        """Send initial subscription request using JSON protocol."""
        # Get tables to subscribe to
        tables = ["entity", "player", "circle", "food", "config"]
        
        # CRITICAL FIX: Ensure proper frame type based on negotiated protocol
        if self._protocol_version == "v1.json.spacetimedb":
            # For JSON protocol, we must send TEXT frames (strings)
            json_message = self.protocol_helper.encode_subscription(tables)
            
            # CRITICAL: Force string type for TEXT frame transmission
            if isinstance(json_message, bytes):
                # SDK returned bytes, convert to string for TEXT frame
                json_message = json_message.decode('utf-8')
                logger.debug("Converted bytes to string for JSON protocol TEXT frame")
            elif not isinstance(json_message, str):
                # SDK returned something else, convert to JSON string
                import json
                json_message = json.dumps(json_message)
                logger.debug("Converted object to JSON string for TEXT frame")
            
            # Send as TEXT frame - only strings are sent as TEXT frames
            await self.websocket.send(json_message)
            logger.info(f"Sent JSON subscription request as TEXT frame ({len(json_message)} chars)")
            
        else:
            # For binary protocol, send BINARY frames
            binary_message = self.protocol_helper.encode_subscription(tables)
            
            # Ensure bytes for BINARY frame transmission
            if isinstance(binary_message, str):
                binary_message = binary_message.encode('utf-8')
                
            await self.websocket.send(binary_message)
            logger.info(f"Sent binary subscription request as BINARY frame ({len(binary_message)} bytes)")
    
    async def _send_message(self, message: Dict[str, Any], request_id: Optional[str] = None) -> Optional[asyncio.Future]:
        """
        Send message to SpacetimeDB server with optional request tracking.
        
        Args:
            message: Message to send
            request_id: Optional request ID for correlation
            
        Returns:
            Future for request response if request_id provided
        """
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            raise BlackholioConnectionError("Not connected to SpacetimeDB")
        
        try:
            # Add request ID if provided
            if request_id:
                message['request_id'] = request_id
                # Create future for response tracking
                future = asyncio.get_event_loop().create_future()
                self._pending_requests[request_id] = future
            else:
                future = None
            
            # Use SDK methods directly - JSON protocol returns strings for TEXT frames
            message_type = message.get('type', '')
            
            # CRITICAL: Never send custom "type" messages to SpacetimeDB
            # The protocol doesn't accept arbitrary JSON with "type" fields
            if message_type == 'heartbeat':
                # Heartbeat should be handled via WebSocket ping, not custom messages
                raise SpacetimeDBError("Custom heartbeat messages violate SpacetimeDB protocol. Use WebSocket ping instead.")
            elif 'reducer' in message:
                # Use encode_reducer_call for reducer messages
                reducer_name = message.get('reducer', '')
                args = message.get('args', {})
                message_data = self.protocol_helper.encode_reducer_call(reducer_name, args)
            elif 'query' in message:
                # Use encode_one_off_query for query messages
                query = message.get('query', '')
                message_data = self.protocol_helper.encode_one_off_query(query)
            else:
                # For other messages, fallback to JSON for compatibility
                import json
                message_data = json.dumps(message)
            
            # CRITICAL FIX: Send message with correct frame type based on protocol
            if self._protocol_version == "v1.json.spacetimedb":
                # JSON protocol requires TEXT frames (strings)
                if isinstance(message_data, bytes):
                    message_data = message_data.decode('utf-8')
                elif not isinstance(message_data, str):
                    import json
                    message_data = json.dumps(message_data)
                
                await self.websocket.send(message_data)  # TEXT frame
                logger.debug(f"Sent {message_type or 'message'} as TEXT frame ({len(message_data)} chars)")
            else:
                # Binary protocol requires BINARY frames (bytes)
                if isinstance(message_data, str):
                    message_data = message_data.encode('utf-8')
                    
                await self.websocket.send(message_data)  # BINARY frame
                logger.debug(f"Sent {message_type or 'message'} as BINARY frame ({len(message_data)} bytes)")
            
            # Update statistics
            self._messages_sent += 1
            self._bytes_sent += len(str(message_data).encode('utf-8'))
            
            logger.debug(f"Sent message ({len(str(message_data))} chars): {message}")
            
            return future
            
        except Exception as e:
            # Clean up pending request on error
            if request_id and request_id in self._pending_requests:
                del self._pending_requests[request_id]
            
            logger.error(f"Failed to send message: {e}")
            raise SpacetimeDBError(f"Failed to send message: {e}")
    
    async def send_request(self, message_type: str, data: Dict[str, Any], timeout: float = 30.0) -> Any:
        """
        Send a request and wait for response.
        
        Args:
            message_type: Type of message to send
            data: Message data
            timeout: Request timeout in seconds
            
        Returns:
            Response data
            
        Raises:
            BlackholioTimeoutError: If request times out
            SpacetimeDBError: If request fails
        """
        # Generate request ID
        self._request_counter += 1
        request_id = f"req_{self._request_counter}_{int(time.time() * 1000)}"
        
        # Format message
        message = self.protocol_handler.format_outgoing_message(message_type, data)
        
        # Send with request tracking
        future = await self._send_message(message, request_id)
        
        if not future:
            raise SpacetimeDBError("Failed to create request future")
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending request
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            
            raise BlackholioTimeoutError(
                f"Request '{message_type}' timed out after {timeout}s",
                timeout_duration=timeout,
                operation=message_type
            )
        except Exception as e:
            # Clean up pending request
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            
            raise SpacetimeDBError(f"Request '{message_type}' failed: {e}")
    
    async def call_reducer(self, reducer_name: str, args: List[Any]) -> bool:
        """
        Call a SpacetimeDB reducer.
        
        Args:
            reducer_name: Name of the reducer to call
            args: List of arguments to pass to the reducer
            
        Returns:
            True if the reducer call was sent successfully
        """
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            raise BlackholioConnectionError("Not connected to SpacetimeDB")
        
        try:
            # Convert args list to proper format for SpacetimeDB
            # For the enter_game reducer, it expects a single "name" parameter
            args_dict = {}
            if args:
                if reducer_name == "enter_game" and len(args) == 1:
                    # Special case for enter_game reducer which expects "name" parameter
                    args_dict = {"name": args[0]}
                elif len(args) == 1:
                    # For other single argument reducers, pass the value directly
                    args_dict = {"value": args[0]}
                else:
                    # For multiple arguments, create indexed dict
                    args_dict = {f"arg{i}": arg for i, arg in enumerate(args)}
            
            # Use the existing _send_message method which handles reducer encoding
            await self._send_message({
                'reducer': reducer_name,
                'args': args_dict
            })
            
            logger.info(f"✅ Called reducer '{reducer_name}' with args: {args}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to call reducer '{reducer_name}': {e}")
            raise BlackholioConnectionError(f"Reducer call failed: {e}")
    
    async def _message_handler(self):
        """Handle incoming messages from SpacetimeDB with enhanced protocol validation."""
        try:
            async for message in self.websocket:
                try:
                    # Update statistics
                    self._messages_received += 1
                    
                    # Enhanced frame type validation
                    if isinstance(message, bytes):
                        # Binary message - should NOT happen with JSON protocol
                        self._bytes_received += len(message)
                        if self._protocol_version == "v1.json.spacetimedb":
                            logger.error("Protocol mismatch: negotiated JSON but received binary frame")
                            logger.debug(f"Binary frame length: {len(message)} bytes")
                            # Still try to handle it for robustness, but log the inconsistency
                        data = await self._handle_binary_message(message)
                    elif isinstance(message, str):
                        # Text message - this is expected with JSON protocol
                        self._bytes_received += len(message.encode('utf-8'))
                        logger.debug(f"Received TEXT frame ({len(message)} chars) - parsing with JSON protocol")
                        data = await self._handle_text_message(message)
                    else:
                        logger.warning(f"Unknown message type: {type(message)}")
                        continue
                    
                    # Process the message
                    if data:
                        await self._process_message(data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {e}")
                    logger.debug(f"Problematic message: {message[:200]}...")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    logger.debug(f"Message type: {type(message)}")
                    
        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            await self._handle_disconnection()
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            await self._handle_connection_error(e)
    
    async def _handle_binary_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Handle binary message format using SpacetimeDB protocol helper.
        
        Args:
            data: Binary message data
            
        Returns:
            Parsed message data or None
        """
        try:
            # Try to decode using protocol helper first
            try:
                server_message = self.protocol_helper.decode_server_message(data)
                
                # Convert to dict format for processing
                if hasattr(server_message, '__dict__'):
                    return server_message.__dict__
                elif hasattr(server_message, '__class__'):
                    # Handle different message types
                    message_type = server_message.__class__.__name__
                    logger.debug(f"Received {message_type} message")
                    return {'type': message_type, 'data': server_message}
                
            except Exception as e:
                logger.debug(f"Failed to decode as binary protocol: {e}")
                pass
            
            # Try to decode as JSON (fallback for mixed protocol servers)
            try:
                text = data.decode('utf-8')
                return json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            
            # Log unknown binary messages
            logger.warning(f"Received undecodable binary message ({len(data)} bytes)")
            return None
            
        except Exception as e:
            logger.error(f"Error handling binary message: {e}")
            return None
    
    async def _handle_text_message(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Handle text message format using enhanced SDK decoder.
        
        Args:
            message: Text message data
            
        Returns:
            Parsed message data or None
        """
        try:
            # Use enhanced decoder if available
            if self.protocol_decoder and SDK_VALIDATION_AVAILABLE:
                try:
                    server_message = self.protocol_decoder.decode_server_message(message.encode('utf-8'))
                    
                    # Convert to dict format for processing
                    if hasattr(server_message, '__dict__'):
                        return server_message.__dict__
                    elif hasattr(server_message, '__class__'):
                        message_type = server_message.__class__.__name__
                        logger.debug(f"Decoded {message_type} message with enhanced decoder")
                        return {'type': message_type, 'data': server_message}
                        
                except Exception as e:
                    logger.debug(f"Enhanced decoder failed, falling back to JSON: {e}")
            
            # Fallback to JSON parsing
            data = json.loads(message)
            
            # Check for unknown message types and provide enhanced logging
            if isinstance(data, dict):
                unknown_keys = []
                known_message_types = {
                    'IdentityToken', 'InitialSubscription', 'TransactionUpdate',
                    'subscription_applied', 'transaction_update', 'identity_token'
                }
                
                for key in data.keys():
                    if key not in known_message_types and key.capitalize() in {'IdentityToken', 'InitialSubscription', 'TransactionUpdate'}:
                        unknown_keys.append(key)
                
                if unknown_keys:
                    logger.warning(f"Unknown message type in data: {{{', '.join([f"'{k}': {{...}}" for k in unknown_keys])}}}")
                    logger.debug(f"Full message data: {data}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode text message as JSON: {e}")
            logger.debug(f"Problematic message: {message[:200]}...")
            return None
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            return None
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming message using enhanced protocol handler with improved message type recognition."""
        try:
            # Check for request response
            request_id = data.get('request_id')
            if request_id and request_id in self._pending_requests:
                # This is a response to a pending request
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    # Check for error response
                    if data.get('error'):
                        error_data = data['error']
                        error_msg = error_data.get('message', 'Unknown error')
                        future.set_exception(SpacetimeDBError(error_msg, server_response=data))
                    else:
                        future.set_result(data.get('result', data))
                return
            
            # Enhanced message type recognition
            message_type = None
            processed_data = None
            
            # First check if this is a typed message (has 'type' field)
            if 'type' in data:
                # Handle messages with explicit type field
                msg_type = data['type']
                logger.info(f"🔥 About to trigger event '{msg_type}' with data keys: {list(data.keys())}")
                
                if msg_type == 'IdentityToken':
                    # Store identity information
                    if 'identity' in data:
                        self._identity = data['identity']
                    if 'token' in data:
                        self._auth_token = data['token']
                    # Trigger the event directly with the original data
                    await self._trigger_event(msg_type, data)
                    return
                    
                elif msg_type == 'DatabaseUpdate':
                    # This is likely the initial subscription data
                    logger.info(f"📨 [MESSAGE] 📋 CRITICAL DatabaseUpdate analysis starting...")
                    logger.info(f"📨 [MESSAGE] DatabaseUpdate keys: {list(data.keys())}")
                    
                    if 'tables' in data:
                        # Log what's in the tables
                        tables_data = data.get('tables')
                        logger.info(f"📨 [MESSAGE] Found 'tables' field - Type: {type(tables_data)}")
                        
                        if isinstance(tables_data, dict):
                            logger.info(f"📨 [MESSAGE] Tables dict has {len(tables_data)} keys: {list(tables_data.keys())}")
                            
                            if not tables_data:
                                logger.error(f"📨 [MESSAGE] ❌ PROBLEM FOUND: Tables dict is EMPTY! This explains the empty data.")
                            else:
                                logger.info(f"📨 [MESSAGE] ✅ Tables dict has content - analyzing each table...")
                                for table_name, table_content in tables_data.items():
                                    if isinstance(table_content, list):
                                        logger.info(f"📨 [MESSAGE] Table '{table_name}': {len(table_content)} items")
                                        if table_content:
                                            # Log sample data from first item
                                            try:
                                                import json
                                                sample = json.dumps(table_content[0], default=str)[:200]
                                                logger.info(f"📨 [MESSAGE] Table '{table_name}' sample: {sample}...")
                                            except Exception as e:
                                                logger.info(f"📨 [MESSAGE] Table '{table_name}' sample: {repr(table_content[0])}")
                                    else:
                                        logger.info(f"📨 [MESSAGE] Table '{table_name}': unexpected type {type(table_content)}")
                                        
                        elif isinstance(tables_data, list):
                            logger.info(f"📨 [MESSAGE] Tables is list with {len(tables_data)} items")
                            if not tables_data:
                                logger.error(f"📨 [MESSAGE] ❌ PROBLEM: Tables list is EMPTY!")
                        else:
                            logger.warning(f"📨 [MESSAGE] Tables is unexpected type: {type(tables_data)}")
                        
                        # Store as initial subscription for later processing
                        self._last_initial_subscription = data
                        logger.info(f"💾 [MESSAGE] Stored DatabaseUpdate as InitialSubscription data")
                        self.on_subscription_data(data)
                    else:
                        logger.error(f"📨 [MESSAGE] ❌ MAJOR PROBLEM: DatabaseUpdate has NO 'tables' key! Keys: {list(data.keys())}")
                        
                    # Trigger both DatabaseUpdate and InitialSubscription events
                    logger.info(f"📨 [MESSAGE] Triggering DatabaseUpdate and InitialSubscription events")
                    await self._trigger_event(msg_type, data)
                    await self._trigger_event('InitialSubscription', data)
                    return
                else:
                    # For other typed messages, trigger directly
                    await self._trigger_event(msg_type, data)
                    return
            
            # Handle known SpacetimeDB message types (original format)
            if 'IdentityToken' in data:
                message_type = 'identity_token'
                processed_data = {'type': message_type, 'identity_token': data['IdentityToken']}
                # Safe string representation for logging
                identity_str = str(data['IdentityToken'])
                logger.debug(f"Recognized IdentityToken message: {identity_str[:20]}...")
                
            elif 'InitialSubscription' in data:
                message_type = 'initial_subscription'
                processed_data = {'type': message_type, 'subscription_data': data['InitialSubscription']}
                logger.debug("Recognized InitialSubscription message")
                
                # CRITICAL: Store the subscription data for later retrieval
                # This solves the timing issue where events are fired before handlers are registered
                self._last_initial_subscription = data['InitialSubscription']
                logger.info(f"💾 Stored InitialSubscription data for later processing ({len(str(data['InitialSubscription']))} chars)")
                
                # Mark that we're receiving subscription data
                self.on_subscription_data(data)
                
            elif 'TransactionUpdate' in data:
                message_type = 'transaction_update'
                processed_data = {'type': message_type, 'update_data': data['TransactionUpdate']}
                logger.debug("Recognized TransactionUpdate message")
                # Mark that we're receiving subscription data
                self.on_subscription_data(data)
                
            else:
                # Fall back to protocol handler for other message types
                processed_data = self.protocol_handler.process_message(data)
                if processed_data:
                    message_type = processed_data.get('type')
            
            # Trigger events if we have processed data
            if processed_data and message_type:
                logger.info(f"🔥 About to trigger event '{message_type}' with data keys: {list(processed_data.keys()) if isinstance(processed_data, dict) else type(processed_data)}")
                # Check if this is a subscription-related message
                if message_type in ('subscription_update', 'initial_subscription', 'transaction_update'):
                    self.on_subscription_data(processed_data)
                await self._trigger_event(message_type, processed_data)
            elif data:
                # Log unrecognized message but don't fail completely
                logger.info(f"Received unrecognized message format: {list(data.keys())[:5]}")
                logger.debug(f"Full unrecognized message: {data}")
                # Try to trigger a generic message event
                await self._trigger_event('raw_message', {'type': 'raw_message', 'data': data})
                    
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            logger.debug(f"Message data: {data}")
    
    async def _heartbeat_handler(self):
        """
        Handle heartbeat/keepalive messages.
        
        CRITICAL: Uses WebSocket ping for keepalive, NOT custom messages.
        SpacetimeDB protocol does not accept arbitrary JSON with "type" fields.
        """
        try:
            while self.state == ConnectionState.CONNECTED:
                try:
                    # Wait for heartbeat interval
                    await asyncio.sleep(self._heartbeat_interval)
                    
                    # Check if connection is still alive
                    if self.websocket and self._is_websocket_open():
                        # CRITICAL: SpacetimeDB protocol compliance
                        # Use WebSocket ping instead of custom heartbeat messages
                        # SpacetimeDB doesn't expect custom "type" messages - this violates protocol
                        self._last_heartbeat_time = time.time()
                        
                        try:
                            await self.websocket.ping()
                            logger.debug("Sent WebSocket ping")
                        except Exception as e:
                            logger.warning(f"Failed to send ping: {e}")
                            # If ping fails, connection might be broken
                            break
                    else:
                        logger.warning("WebSocket closed during heartbeat check")
                        break
                        
                except asyncio.CancelledError:
                    logger.debug("Heartbeat handler cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in heartbeat handler: {e}")
                    
        except Exception as e:
            logger.error(f"Fatal error in heartbeat handler: {e}")
        finally:
            logger.debug("Heartbeat handler stopped")
    
    def _is_websocket_open(self) -> bool:
        """
        Safely check if websocket is open and available.
        
        Returns:
            True if websocket is open and ready for communication
        """
        if not self.websocket:
            return False
        
        try:
            # Check various websocket state indicators
            if hasattr(self.websocket, 'closed'):
                return not self.websocket.closed
            elif hasattr(self.websocket, 'close_code'):
                return self.websocket.close_code is None
            elif hasattr(self.websocket, 'state'):
                # For some websocket implementations
                return str(self.websocket.state).lower() in ('open', 'connected')
            else:
                # Fallback: assume open if we have a websocket object
                return True
        except Exception:
            # If any check fails, assume websocket is not usable
            return False
    
    async def _send_close_frame(self):
        """
        Prepare for proper WebSocket close frame before disconnecting.
        
        CRITICAL: Does NOT send custom application messages to SpacetimeDB.
        SpacetimeDB protocol specification forbids arbitrary JSON with "type" fields.
        WebSocket close frames are handled at the WebSocket protocol layer.
        """
        if not self.websocket or not self._is_websocket_open():
            return
        
        try:
            # CRITICAL: SpacetimeDB protocol compliance
            # Don't send custom close messages - SpacetimeDB doesn't expect "type" messages
            # This violates the SpacetimeDB protocol specification and causes connection termination
            # The WebSocket close frame sent by websocket.close() is sufficient for clean shutdown
            if self._is_websocket_open():
                logger.debug("WebSocket ready for clean close")
                # Small delay to ensure any pending messages are processed
                await asyncio.sleep(0.05)
            
        except asyncio.TimeoutError:
            logger.debug("Close frame send timed out")
        except Exception as e:
            logger.debug(f"Failed to send close frame: {e}")
    
    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors with retry logic."""
        previous_state = self.state
        
        # Determine if error is retryable
        from ..exceptions.connection_errors import is_retryable_error
        
        if not is_retryable_error(error) or self._reconnect_attempts >= self._max_reconnect_attempts:
            self.state = ConnectionState.FAILED
            logger.error(f"Connection failed permanently: {error}")
            await self._trigger_event('connection_failed', {
                'error': str(error),
                'error_type': type(error).__name__,
                'attempts': self._reconnect_attempts,
                'retryable': is_retryable_error(error)
            })
            return
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self.state = ConnectionState.RECONNECTING
            self._reconnect_attempts += 1
            
            # Exponential backoff with jitter
            delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
            jitter = delay * 0.1 * (2 * asyncio.get_event_loop().time() % 1 - 1)
            delay = max(0.1, delay + jitter)
            
            logger.warning(
                f"Connection error: {error}. Retrying in {delay:.1f}s "
                f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
            )
            
            await self._trigger_event('reconnecting', {
                'error': str(error),
                'attempt': self._reconnect_attempts,
                'max_attempts': self._max_reconnect_attempts,
                'delay': delay
            })
            
            await asyncio.sleep(delay)
            
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                await self._handle_connection_error(e)
    
    async def _handle_disconnection(self):
        """Handle unexpected disconnection."""
        if self.state == ConnectionState.CONNECTED:
            logger.warning("Unexpected disconnection from SpacetimeDB")
            
            # Don't call full disconnect() as connection is already lost
            # Just clean up internal state
            self.state = ConnectionState.DISCONNECTED
            
            # Cancel tasks without trying to send close frames
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None
            
            if self._message_handler_task:
                self._message_handler_task.cancel()
                try:
                    await self._message_handler_task
                except asyncio.CancelledError:
                    pass
                self._message_handler_task = None
            
            # Clear websocket reference
            self.websocket = None
            
            # Cancel pending requests
            for request_id, future in self._pending_requests.items():
                if not future.done():
                    future.cancel()
            self._pending_requests.clear()
            
            error = ConnectionLostError(
                "Connection to SpacetimeDB was lost unexpectedly",
                reconnect_attempts=self._reconnect_attempts
            )
            
            await self._handle_connection_error(error)
    
    # Utility methods
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.state == ConnectionState.CONNECTED
    
    @property
    def identity(self) -> Optional[str]:
        """Get the current identity."""
        return self._identity
    
    @property
    def connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        uptime = None
        if self._connection_start_time and self.is_connected:
            uptime = time.time() - self._connection_start_time
        
        return {
            'state': self.state.value,
            'uptime': uptime,
            'messages_sent': self._messages_sent,
            'messages_received': self._messages_received,
            'bytes_sent': self._bytes_sent,
            'bytes_received': self._bytes_received,
            'pending_requests': len(self._pending_requests),
            'reconnect_attempts': self._reconnect_attempts,
            'last_heartbeat': self._last_heartbeat_time
        }
    
    def get_pending_request_count(self) -> int:
        """Get number of pending requests."""
        return len(self._pending_requests)
    
    async def wait_until_connected(self, timeout: float = 30.0) -> bool:
        """
        Wait until connection is established.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if connected, False if timeout
        """
        start_time = time.time()
        
        while True:
            # Check current state
            if self.state == ConnectionState.CONNECTED:
                return True
            elif self.state == ConnectionState.FAILED:
                return False
            
            # Check timeout BEFORE sleeping to prevent infinite loops
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Connection timeout reached after {elapsed:.1f}s")
                return False
            
            # Sleep for a short interval
            await asyncio.sleep(0.1)
    
    async def wait_for_subscription_data(self, timeout: float = 5.0) -> bool:
        """
        Wait for subscription data to start flowing.
        
        Args:
            timeout: Maximum time to wait for subscription data
            
        Returns:
            True if subscription data is flowing, False if timeout
        """
        start_time = time.time()
        
        logger.debug(f"Waiting for subscription data (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            # Check if we've received data recently
            if self._last_data_received and time.time() - self._last_data_received < 1.0:
                logger.debug("Subscription data confirmed - data received within last second")
                self._subscriptions_active = True
                return True
            
            # Also check if we've marked subscriptions as active
            if self._subscriptions_active:
                logger.debug("Subscriptions marked as active")
                return True
            
            await asyncio.sleep(0.1)
        
        logger.warning(f"Timeout waiting for subscription data after {timeout}s")
        return False
    
    def on_subscription_data(self, data: Any) -> None:
        """
        Mark that subscription data was received.
        
        Args:
            data: The subscription data received
        """
        self._last_data_received = time.time()
        self._subscriptions_active = True
        logger.debug("Subscription data received - marking connection as active")
    
    def enable_protocol_debugging(self) -> None:
        """
        Enable enhanced protocol debugging to help identify protocol issues.
        This will log detailed information about frame types and protocol mismatches.
        """
        logger.info("Protocol debugging enabled - will log frame type validation warnings")
        
        # Set logging level to DEBUG for this specific logger
        current_logger = logging.getLogger(__name__)
        current_logger.setLevel(logging.DEBUG)
        
        # Log current protocol configuration
        logger.info(f"Current protocol version: {self._protocol_version}")
        logger.info(f"Protocol validated: {self._protocol_validated}")
        logger.info(f"Enhanced SDK validation available: {SDK_VALIDATION_AVAILABLE}")
        
        if self.websocket:
            negotiated_protocol = getattr(self.websocket, 'subprotocol', 'unknown')
            logger.info(f"Negotiated WebSocket subprotocol: {negotiated_protocol}")
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """
        Get current protocol configuration and validation status.
        
        Returns:
            Dictionary with protocol information
        """
        negotiated_protocol = None
        if self.websocket:
            negotiated_protocol = getattr(self.websocket, 'subprotocol', None)
            
        return {
            'protocol_version': self._protocol_version,
            'protocol_validated': self._protocol_validated,
            'negotiated_protocol': negotiated_protocol,
            'sdk_validation_available': SDK_VALIDATION_AVAILABLE,
            'connection_state': self.state.value,
            'use_binary': self.protocol_helper.use_binary if hasattr(self.protocol_helper, 'use_binary') else False
        }
    
    def on(self, event: str, callback: Callable):
        """Register event callback."""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    async def _trigger_event(self, event: str, data: Any = None):
        """Trigger event callbacks."""
        import time
        import json
        
        trigger_start_time = time.time()
        logger.info(f"🚀 [EVENT] ==> Starting event trigger for '{event}' at {trigger_start_time:.3f}")
        
        # Log event data structure for key events
        if event in ['DatabaseUpdate', 'IdentityToken', 'InitialSubscription']:
            try:
                if isinstance(data, dict):
                    data_summary = {k: f"{type(v).__name__}({len(v) if hasattr(v, '__len__') and not isinstance(v, str) else 'N/A'})" for k, v in data.items()}
                    logger.info(f"🚀 [EVENT] Event '{event}' data structure: {data_summary}")
                else:
                    logger.info(f"🚀 [EVENT] Event '{event}' data type: {type(data)}")
            except Exception as e:
                logger.warning(f"🚀 [EVENT] Could not analyze event data: {e}")
        
        # Map of PascalCase to lowercase event names
        event_mapping = {
            'IdentityToken': 'identity_token',
            'InitialSubscription': 'initial_subscription',
            'TransactionUpdate': 'transaction_update',
            'DatabaseUpdate': 'database_update',
            'Connected': 'connected',
            'Disconnected': 'disconnected'
        }
        
        # Check both the original event name and the mapped name
        events_to_trigger = [event]
        
        # If this is a PascalCase event, also trigger the lowercase version
        if event in event_mapping:
            events_to_trigger.append(event_mapping[event])
            logger.info(f"🚀 [EVENT] Will also trigger lowercase version: {event_mapping[event]}")
        # If this is a lowercase event, also check for PascalCase version
        elif event in event_mapping.values():
            # Find the PascalCase version
            for pascal, lower in event_mapping.items():
                if lower == event:
                    events_to_trigger.append(pascal)
                    logger.info(f"🚀 [EVENT] Will also trigger PascalCase version: {pascal}")
                    break
        
        logger.info(f"🚀 [EVENT] Total events to trigger: {len(events_to_trigger)} - {events_to_trigger}")
        
        # Trigger callbacks for all event name variations
        total_callbacks_executed = 0
        
        for event_name in events_to_trigger:
            callbacks = self._event_callbacks.get(event_name, [])
            
            if callbacks:
                logger.info(f"🚀 [EVENT] ✅ Triggering event '{event_name}' with {len(callbacks)} callbacks")
                
                for i, callback in enumerate(callbacks):
                    callback_start_time = time.time()
                    try:
                        logger.info(f"🚀 [EVENT] Executing callback {i+1}/{len(callbacks)} for '{event_name}'")
                        
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                            
                        callback_duration = time.time() - callback_start_time
                        logger.info(f"🚀 [EVENT] ✅ Callback {i+1} completed in {callback_duration:.3f}s")
                        total_callbacks_executed += 1
                        
                    except Exception as e:
                        callback_duration = time.time() - callback_start_time
                        logger.error(f"🚀 [EVENT] ❌ Callback {i+1} failed after {callback_duration:.3f}s: {e}")
                        import traceback
                        logger.error(f"🚀 [EVENT] Callback traceback: {traceback.format_exc()}")
            else:
                # Log missing callbacks with different severity based on event importance
                if event_name in ['DatabaseUpdate', 'IdentityToken', 'InitialSubscription']:
                    logger.warning(f"🚀 [EVENT] ⚠️ CRITICAL: No callbacks registered for important event '{event_name}'!")
                else:
                    logger.info(f"🚀 [EVENT] 🟡 No callbacks for event '{event_name}'")
        
        total_duration = time.time() - trigger_start_time
        logger.info(f"🚀 [EVENT] <== Event trigger complete. Executed {total_callbacks_executed} callbacks in {total_duration:.3f}s")

    def get_registered_events(self) -> dict:
        """Return currently registered event callbacks for debugging."""
        return {event: len(callbacks) for event, callbacks in self._event_callbacks.items()}


class BlackholioClient:
    """
    High-level client interface for Blackholio game integration.
    
    Provides a simple, unified API that abstracts away server language
    differences and connection complexity.
    """
    
    def __init__(self, server_language: Optional[str] = None, **kwargs):
        """
        Initialize Blackholio client.
        
        Args:
            server_language: Override server language (rust, python, csharp, go)
            **kwargs: Additional configuration options
        """
        # Load configuration from environment
        self.env_config = EnvironmentConfig()
        self.server_config = self.env_config.get_server_config(server_language)
        
        # Override with any provided kwargs
        for key, value in kwargs.items():
            if hasattr(self.server_config, key):
                setattr(self.server_config, key, value)
        
        # Initialize connection
        self.connection = SpacetimeDBConnection(self.server_config)
        
        # Game state
        self.player_id = None
        self.game_entities: Dict[str, GameEntity] = {}
        self.game_players: Dict[str, GamePlayer] = {}
        
        # Set up event handlers
        self._setup_event_handlers()
        
        logger.info(f"Initialized BlackholioClient for {self.server_config.language} server")
    
    def _setup_event_handlers(self):
        """Set up internal event handlers for game state management."""
        self.connection.on('entity_update', self._handle_entity_update)
        self.connection.on('player_update', self._handle_player_update)
        self.connection.on('game_state', self._handle_game_state)
        
        # Add subscription-related event handlers
        self.connection.on('initial_subscription', self._handle_initial_subscription)
        self.connection.on('subscription_update', self._handle_subscription_update)
        self.connection.on('transaction_update', self._handle_transaction_update)
    
    async def connect(self) -> bool:
        """Connect to the game server."""
        return await self.connection.connect()
    
    async def disconnect(self):
        """Disconnect from the game server."""
        await self.connection.disconnect()
    
    async def enter_game(self, player_name: str) -> bool:
        """
        Enter the game with specified player name.
        
        Args:
            player_name: Name for the player
            
        Returns:
            True if successfully entered game
        """
        try:
            # Encode reducer call using JSON protocol
            message = self.connection.protocol_helper.encode_reducer_call(
                "enter_game", 
                {"player_name": player_name}
            )
            
            await self.connection.websocket.send(message)
            logger.info(f"Sent enter_game reducer as text frame ({len(message)} chars) for player: {player_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enter game: {e}")
            return False
    
    async def update_player_input(self, direction: Vector2) -> bool:
        """
        Update player movement direction.
        
        Args:
            direction: Movement direction vector
            
        Returns:
            True if input was sent successfully
        """
        try:
            # Encode reducer call using JSON protocol
            message = self.connection.protocol_helper.encode_reducer_call(
                "update_input", 
                {
                    "direction": {
                        "x": direction.x,
                        "y": direction.y
                    }
                }
            )
            
            await self.connection.websocket.send(message)
            logger.debug(f"Sent update_input reducer as text frame ({len(message)} chars)")
            return True
        except Exception as e:
            logger.error(f"Failed to update player input: {e}")
            return False
    
    async def _handle_entity_update(self, data: Dict[str, Any]):
        """Handle entity update events."""
        try:
            entity = GameEntity.from_dict(data)
            self.game_entities[entity.entity_id] = entity
        except Exception as e:
            logger.error(f"Failed to handle entity update: {e}")
    
    async def _handle_player_update(self, data: Dict[str, Any]):
        """Handle player update events."""
        try:
            player = GamePlayer.from_dict(data)
            self.game_players[player.player_id] = player
            
            # Track our own player ID
            if player.name and not self.player_id:
                self.player_id = player.player_id
        except Exception as e:
            logger.error(f"Failed to handle player update: {e}")
    
    async def _handle_game_state(self, data: Dict[str, Any]):
        """Handle full game state updates."""
        try:
            # Update entities
            if 'entities' in data:
                for entity_data in data['entities']:
                    entity = GameEntity.from_dict(entity_data)
                    self.game_entities[entity.entity_id] = entity
            
            # Update players
            if 'players' in data:
                for player_data in data['players']:
                    player = GamePlayer.from_dict(player_data)
                    self.game_players[player.player_id] = player
                    
        except Exception as e:
            logger.error(f"Failed to handle game state: {e}")
    
    def on(self, event: str, callback: Callable):
        """Register event callback (delegates to connection)."""
        self.connection.on(event, callback)
    
    def enable_protocol_debugging(self) -> None:
        """Enable protocol debugging for troubleshooting connection issues."""
        self.connection.enable_protocol_debugging()
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol information for debugging."""
        return self.connection.get_protocol_info()
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.connection.is_connected
    
    def get_entities(self) -> Dict[str, GameEntity]:
        """Get current game entities."""
        return self.game_entities.copy()
    
    def get_players(self) -> Dict[str, GamePlayer]:
        """Get current game players."""
        return self.game_players.copy()
    
    def get_my_player(self) -> Optional[GamePlayer]:
        """Get the current player."""
        if self.player_id and self.player_id in self.game_players:
            return self.game_players[self.player_id]
        return None
    
    async def _handle_initial_subscription(self, data: Dict[str, Any]):
        """Handle initial subscription data."""
        try:
            subscription_data = data.get('subscription_data', {})
            logger.debug(f"Received initial subscription with {len(subscription_data)} tables")
            
            # Process any initial data provided
            if 'tables' in subscription_data:
                for table_data in subscription_data['tables']:
                    await self._process_table_data(table_data)
                    
        except Exception as e:
            logger.error(f"Failed to handle initial subscription: {e}")
    
    async def _handle_subscription_update(self, data: Dict[str, Any]):
        """Handle subscription update events."""
        try:
            logger.debug("Received subscription update")
            # Process subscription updates
            if 'tables' in data:
                for table_data in data['tables']:
                    await self._process_table_data(table_data)
                    
        except Exception as e:
            logger.error(f"Failed to handle subscription update: {e}")
    
    async def _handle_transaction_update(self, data: Dict[str, Any]):
        """Handle transaction update events."""
        try:
            logger.debug("Received transaction update")
            
            # Process entities from transaction update
            if 'entities' in data:
                for entity_data in data['entities']:
                    entity = GameEntity.from_dict(entity_data)
                    self.game_entities[entity.entity_id] = entity
                    
            # Process players from transaction update  
            if 'players' in data:
                for player_data in data['players']:
                    player = GamePlayer.from_dict(player_data)
                    self.game_players[player.player_id] = player
                    
        except Exception as e:
            logger.error(f"Failed to handle transaction update: {e}")
    
    async def _process_table_data(self, table_data: Dict[str, Any]):
        """Process data from a specific table."""
        try:
            table_name = table_data.get('table_name', '').lower()
            
            if table_name in ['entities', 'entity', 'game_entities']:
                for row in table_data.get('rows', []):
                    entity = GameEntity.from_dict(row)
                    self.game_entities[entity.entity_id] = entity
                    
            elif table_name in ['players', 'player', 'game_players']:
                for row in table_data.get('rows', []):
                    player = GamePlayer.from_dict(row)
                    self.game_players[player.player_id] = player
                    
        except Exception as e:
            logger.error(f"Failed to process table data: {e}")
