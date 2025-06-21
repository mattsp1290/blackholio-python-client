"""
Unified API interfaces for Blackholio SpacetimeDB client.

This module provides abstract base classes and interfaces that hide server language
differences and provide a consistent API for both blackholio-agent and client-pygame
projects.
"""

from .auth_interface import AuthInterface
from .connection_interface import ConnectionInterface
from .game_client_interface import GameClientInterface
from .reducer_interface import ReducerInterface
from .subscription_interface import SubscriptionInterface

__all__ = [
    'AuthInterface',
    'ConnectionInterface', 
    'GameClientInterface',
    'ReducerInterface',
    'SubscriptionInterface'
]