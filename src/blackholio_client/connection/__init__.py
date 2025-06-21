"""
Connection Module - SpacetimeDB Integration

Handles all SpacetimeDB connection logic, server configuration,
and protocol management for multiple server languages.

Enhanced with modernized SDK capabilities while maintaining backward compatibility.
"""

# Enhanced SDK-powered implementations (recommended)
from .modernized_spacetimedb_client import ModernizedSpacetimeDBConnection, BlackholioClient, ConnectionState
from .enhanced_connection_manager import EnhancedConnectionManager, get_connection_manager as get_enhanced_manager

# Legacy implementations (for backward compatibility)
from .spacetimedb_connection import SpacetimeDBConnection
from .connection_manager import (
    ConnectionManager, 
    ConnectionPool, 
    PoolConfiguration,
    ConnectionMetrics,
    CircuitBreaker,
    get_connection
)

# Common utilities
from .server_config import ServerConfig, SERVER_CONFIGS
from .protocol_handlers import ProtocolHandler, V112ProtocolHandler

# Default to enhanced implementations
get_connection_manager = get_enhanced_manager

__all__ = [
    # Enhanced implementations (SDK-powered)
    "ModernizedSpacetimeDBConnection",
    "BlackholioClient",  # Now points to modernized version
    "ConnectionState",
    "EnhancedConnectionManager",
    "get_enhanced_manager",
    
    # Legacy implementations (backward compatibility)
    "SpacetimeDBConnection",
    "ConnectionManager",
    "ConnectionPool",
    "PoolConfiguration", 
    "ConnectionMetrics",
    "CircuitBreaker",
    "get_connection",
    
    # Default manager (points to enhanced)
    "get_connection_manager",
    
    # Common utilities
    "ServerConfig",
    "SERVER_CONFIGS",
    "ProtocolHandler",
    "V112ProtocolHandler",
]
