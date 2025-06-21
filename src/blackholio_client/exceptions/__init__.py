"""
Exceptions Module - Custom Exception Classes

Defines custom exceptions for the blackholio client package
with clear error hierarchies and helpful error messages.
"""

from .connection_errors import (
    BlackholioConnectionError,
    BlackholioConfigurationError,
    ServerConfigurationError,
    SpacetimeDBError,
    ProtocolError,
    AuthenticationError,
    BlackholioTimeoutError,
    ConnectionLostError,
    ServerUnavailableError,
    DataValidationError,
    GameStateError,
    # Factory functions
    create_connection_timeout_error,
    create_server_config_error,
    create_protocol_error,
    create_server_unavailable_error,
    create_data_validation_error,
    create_game_state_error,
    # Utility functions
    is_retryable_error,
    is_configuration_error,
    get_error_category,
    # Backwards compatibility
    TimeoutError
)

__all__ = [
    "BlackholioConnectionError",
    "BlackholioConfigurationError",
    "ServerConfigurationError", 
    "SpacetimeDBError",
    "ProtocolError",
    "AuthenticationError",
    "BlackholioTimeoutError",
    "ConnectionLostError",
    "ServerUnavailableError",
    "DataValidationError",
    "GameStateError",
    # Factory functions
    "create_connection_timeout_error",
    "create_server_config_error",
    "create_protocol_error",
    "create_server_unavailable_error",
    "create_data_validation_error",
    "create_game_state_error",
    # Utility functions
    "is_retryable_error",
    "is_configuration_error",
    "get_error_category",
    # Backwards compatibility
    "TimeoutError",
]
