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
                logger.info(f"Connecting to SpacetimeDB at {ws_url}")
                
                # Attempt connection with authentication
                success = await self._connect_with_auth(ws_url)
                
                if not success:
                    self.state = ConnectionState.FAILED
                    return False
                
                # Record connection time
                self._connection_start_time = time.time()
                
                # Set state to connected before starting tasks
                self.state = ConnectionState.CONNECTED
                self._reconnect_attempts = 0
                
                # Start message handler and heartbeat
                self._message_handler_task = asyncio.create_task(
                    self._message_handler(),
                    name="message_handler"
                )
                self._heartbeat_task = asyncio.create_task(
                    self._heartbeat_handler(),
                    name="heartbeat_handler"
                )
                
                # Send initial subscription request
                await self._send_subscription_request()
                
                identity_info = f" with identity: {self._identity}" if self._identity else ""
                logger.info(f"Successfully connected to SpacetimeDB{identity_info}")
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
            negotiated_protocol = getattr(self.websocket, 'subprotocol', None)
            if negotiated_protocol:
                logger.info(f"Connected with protocol: {negotiated_protocol}")
                if negotiated_protocol != "v1.json.spacetimedb":
                    logger.warning(f"Protocol mismatch - requested JSON but got: {negotiated_protocol}")
                    
            logger.info(f"Connected to SpacetimeDB at {url}")
            self._protocol_validated = True
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
            
            logger.info(f"Authentication successful - connected with identity: {identity}")
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
        
        # Create JSON subscription message - SDK now returns string for JSON protocol
        json_message = self.protocol_helper.encode_subscription(tables)
        
        # Send as text frame - websockets library sends strings as text frames
        await self.websocket.send(json_message)
        logger.info(f"Sent JSON subscription request ({len(json_message)} chars) - frame type: TEXT")
    
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
            
            if message_type == 'heartbeat':
                # For heartbeat, use simple JSON encoding
                import json
                message_data = json.dumps(message)
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
            
            # Send message - protocol helper returns appropriate type for frame transmission
            await self.websocket.send(message_data)
            logger.debug(f"Sent {message_type or 'message'} as text frame ({len(str(message_data))} chars)")
            
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
                        logger.warning(f"Received BINARY frame with v1.json.spacetimedb protocol - this may indicate protocol mismatch")
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
            
            # Handle known SpacetimeDB message types
            if 'IdentityToken' in data:
                message_type = 'identity_token'
                processed_data = {'type': message_type, 'identity_token': data['IdentityToken']}
                logger.debug(f"Recognized IdentityToken message: {data['IdentityToken'][:20]}...")
                
            elif 'InitialSubscription' in data:
                message_type = 'initial_subscription'
                processed_data = {'type': message_type, 'subscription_data': data['InitialSubscription']}
                logger.debug("Recognized InitialSubscription message")
                
            elif 'TransactionUpdate' in data:
                message_type = 'transaction_update'
                processed_data = {'type': message_type, 'update_data': data['TransactionUpdate']}
                logger.debug("Recognized TransactionUpdate message")
                
            else:
                # Fall back to protocol handler for other message types
                processed_data = self.protocol_handler.process_message(data)
                if processed_data:
                    message_type = processed_data.get('type')
            
            # Trigger events if we have processed data
            if processed_data and message_type:
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
        if event in self._event_callbacks:
            for callback in self._event_callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback for {event}: {e}")


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
