"""
Configuration Module - Environment and Server Configuration

Handles environment variable management, server profiles,
and configuration validation for the blackholio client.
"""

from .environment import EnvironmentConfig, get_environment_config
from .server_profiles import ServerProfile, get_server_profile, list_server_profiles

# Import ServerConfig for backward compatibility
try:
    from ..connection.server_config import ServerConfig
except ImportError:
    ServerConfig = None

__all__ = [
    "EnvironmentConfig",
    "get_environment_config",
    "ServerProfile", 
    "get_server_profile",
    "list_server_profiles",
    "ServerConfig",
]
