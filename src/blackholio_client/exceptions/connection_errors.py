"""
Connection Errors - Custom Exception Classes for Connection Issues

Defines specific exception classes for different types of connection
and SpacetimeDB-related errors with helpful error messages.
"""

from typing import Optional, Dict, Any


class BlackholioConnectionError(Exception):
    """
    Base exception for all blackholio client connection errors.
    
    This is the root exception class that all other connection-related
    exceptions inherit from.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize connection error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"{self.__class__.__name__}(message='{self.message}', error_code='{self.error_code}', details={self.details})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class BlackholioConfigurationError(BlackholioConnectionError):
    """
    General configuration error for the Blackholio client.
    
    This is raised for configuration issues that aren't specifically
    server-related, such as missing dependencies, invalid factory
    configurations, or module loading errors.
    """
    
    def __init__(self, message: str, config_item: Optional[str] = None, **kwargs):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_item: Name of the configuration item that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.config_item = config_item
        if config_item:
            self.details['config_item'] = config_item


class ServerConfigurationError(BlackholioConnectionError):
    """
    Exception raised for server configuration errors.
    
    This includes invalid server languages, malformed URLs,
    missing configuration parameters, etc.
    """
    
    def __init__(self, message: str, config_field: Optional[str] = None, **kwargs):
        """
        Initialize server configuration error.
        
        Args:
            message: Error message
            config_field: Name of the configuration field that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.config_field = config_field
        if config_field:
            self.details['config_field'] = config_field


class SpacetimeDBError(BlackholioConnectionError):
    """
    Exception raised for SpacetimeDB-specific errors.
    
    This includes protocol errors, database errors, subscription failures, etc.
    """
    
    def __init__(self, message: str, server_response: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize SpacetimeDB error.
        
        Args:
            message: Error message
            server_response: Optional server response that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.server_response = server_response
        if server_response:
            self.details['server_response'] = server_response


class ProtocolError(SpacetimeDBError):
    """
    Exception raised for protocol-level errors.
    
    This includes malformed messages, unsupported protocol versions,
    invalid message types, etc.
    """
    
    def __init__(self, message: str, protocol_version: Optional[str] = None, message_data: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize protocol error.
        
        Args:
            message: Error message
            protocol_version: Protocol version that caused the error
            message_data: Message data that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.protocol_version = protocol_version
        self.message_data = message_data
        
        if protocol_version:
            self.details['protocol_version'] = protocol_version
        if message_data:
            self.details['message_data'] = message_data


class AuthenticationError(BlackholioConnectionError):
    """
    Exception raised for authentication and authorization errors.
    
    This includes invalid credentials, expired tokens, insufficient permissions, etc.
    """
    
    def __init__(self, message: str, auth_method: Optional[str] = None, **kwargs):
        """
        Initialize authentication error.
        
        Args:
            message: Error message
            auth_method: Authentication method that failed
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.auth_method = auth_method
        if auth_method:
            self.details['auth_method'] = auth_method


class BlackholioTimeoutError(BlackholioConnectionError):
    """
    Exception raised for timeout-related errors.
    
    This includes connection timeouts, operation timeouts, etc.
    """
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, operation: Optional[str] = None, **kwargs):
        """
        Initialize timeout error.
        
        Args:
            message: Error message
            timeout_duration: Duration of the timeout in seconds
            operation: Operation that timed out
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.timeout_duration = timeout_duration
        self.operation = operation
        
        if timeout_duration:
            self.details['timeout_duration'] = timeout_duration
        if operation:
            self.details['operation'] = operation


class ConnectionLostError(BlackholioConnectionError):
    """
    Exception raised when connection to server is lost unexpectedly.
    """
    
    def __init__(self, message: str = "Connection to server was lost", reconnect_attempts: Optional[int] = None, **kwargs):
        """
        Initialize connection lost error.
        
        Args:
            message: Error message
            reconnect_attempts: Number of reconnection attempts made
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.reconnect_attempts = reconnect_attempts
        if reconnect_attempts is not None:
            self.details['reconnect_attempts'] = reconnect_attempts


class ServerUnavailableError(BlackholioConnectionError):
    """
    Exception raised when server is unavailable or unreachable.
    """
    
    def __init__(self, message: str, server_url: Optional[str] = None, **kwargs):
        """
        Initialize server unavailable error.
        
        Args:
            message: Error message
            server_url: URL of the unavailable server
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.server_url = server_url
        if server_url:
            self.details['server_url'] = server_url


class DataValidationError(BlackholioConnectionError):
    """
    Exception raised for data validation errors.
    
    This includes invalid game data, malformed entities, etc.
    """
    
    def __init__(self, message: str, validation_field: Optional[str] = None, invalid_data: Optional[Any] = None, **kwargs):
        """
        Initialize data validation error.
        
        Args:
            message: Error message
            validation_field: Field that failed validation
            invalid_data: Data that failed validation
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.validation_field = validation_field
        self.invalid_data = invalid_data
        
        if validation_field:
            self.details['validation_field'] = validation_field
        if invalid_data is not None:
            self.details['invalid_data'] = str(invalid_data)  # Convert to string for serialization


class GameStateError(BlackholioConnectionError):
    """
    Exception raised for game state-related errors.
    
    This includes invalid game operations, state inconsistencies, etc.
    """
    
    def __init__(self, message: str, game_state: Optional[str] = None, player_id: Optional[str] = None, **kwargs):
        """
        Initialize game state error.
        
        Args:
            message: Error message
            game_state: Current game state
            player_id: Player ID associated with the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.game_state = game_state
        self.player_id = player_id
        
        if game_state:
            self.details['game_state'] = game_state
        if player_id:
            self.details['player_id'] = player_id


# Convenience functions for creating common errors
def create_connection_timeout_error(timeout_duration: float, operation: str = "connection") -> BlackholioTimeoutError:
    """
    Create a connection timeout error.
    
    Args:
        timeout_duration: Timeout duration in seconds
        operation: Operation that timed out
        
    Returns:
        BlackholioTimeoutError instance
    """
    return BlackholioTimeoutError(
        f"Connection timeout after {timeout_duration}s during {operation}",
        timeout_duration=timeout_duration,
        operation=operation,
        error_code="CONNECTION_TIMEOUT"
    )


def create_server_config_error(field: str, value: Any, reason: str) -> ServerConfigurationError:
    """
    Create a server configuration error.
    
    Args:
        field: Configuration field name
        value: Invalid value
        reason: Reason why the value is invalid
        
    Returns:
        ServerConfigurationError instance
    """
    return ServerConfigurationError(
        f"Invalid configuration for '{field}': {reason} (value: {value})",
        config_field=field,
        error_code="INVALID_CONFIG"
    )


def create_protocol_error(protocol_version: str, message_type: str, reason: str) -> ProtocolError:
    """
    Create a protocol error.
    
    Args:
        protocol_version: Protocol version
        message_type: Message type that caused the error
        reason: Reason for the error
        
    Returns:
        ProtocolError instance
    """
    return ProtocolError(
        f"Protocol error in {protocol_version} for message type '{message_type}': {reason}",
        protocol_version=protocol_version,
        error_code="PROTOCOL_ERROR"
    )


def create_server_unavailable_error(server_url: str, reason: str = "Server is unreachable") -> ServerUnavailableError:
    """
    Create a server unavailable error.
    
    Args:
        server_url: Server URL
        reason: Reason why server is unavailable
        
    Returns:
        ServerUnavailableError instance
    """
    return ServerUnavailableError(
        f"Server unavailable at {server_url}: {reason}",
        server_url=server_url,
        error_code="SERVER_UNAVAILABLE"
    )


def create_data_validation_error(field: str, value: Any, expected: str) -> DataValidationError:
    """
    Create a data validation error.
    
    Args:
        field: Field that failed validation
        value: Invalid value
        expected: Expected value format/type
        
    Returns:
        DataValidationError instance
    """
    return DataValidationError(
        f"Validation failed for field '{field}': expected {expected}, got {type(value).__name__} ({value})",
        validation_field=field,
        invalid_data=value,
        error_code="VALIDATION_ERROR"
    )


def create_game_state_error(operation: str, current_state: str, required_state: str, player_id: Optional[str] = None) -> GameStateError:
    """
    Create a game state error.
    
    Args:
        operation: Operation that failed
        current_state: Current game state
        required_state: Required game state for the operation
        player_id: Optional player ID
        
    Returns:
        GameStateError instance
    """
    message = f"Cannot perform '{operation}' in state '{current_state}', requires state '{required_state}'"
    if player_id:
        message += f" (player: {player_id})"
    
    return GameStateError(
        message,
        game_state=current_state,
        player_id=player_id,
        error_code="INVALID_GAME_STATE"
    )


# Error handling utilities
def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error is retryable
    """
    retryable_errors = (
        ConnectionLostError,
        ServerUnavailableError,
        BlackholioTimeoutError
    )
    
    return isinstance(error, retryable_errors)


def is_configuration_error(error: Exception) -> bool:
    """
    Check if an error is a configuration error.
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error is a configuration error
    """
    return isinstance(error, ServerConfigurationError)


def get_error_category(error: Exception) -> str:
    """
    Get the category of an error.
    
    Args:
        error: Exception to categorize
        
    Returns:
        Error category string
    """
    if isinstance(error, ServerConfigurationError):
        return "server_configuration"
    elif isinstance(error, BlackholioConfigurationError):
        return "configuration"
    elif isinstance(error, AuthenticationError):
        return "authentication"
    elif isinstance(error, ProtocolError):
        return "protocol"
    elif isinstance(error, BlackholioTimeoutError):
        return "timeout"
    elif isinstance(error, ConnectionLostError):
        return "connection_lost"
    elif isinstance(error, ServerUnavailableError):
        return "server_unavailable"
    elif isinstance(error, DataValidationError):
        return "validation"
    elif isinstance(error, GameStateError):
        return "game_state"
    elif isinstance(error, SpacetimeDBError):
        return "spacetimedb"
    elif isinstance(error, BlackholioConnectionError):
        return "connection"
    else:
        return "unknown"


# Backwards compatibility alias
TimeoutError = BlackholioTimeoutError
