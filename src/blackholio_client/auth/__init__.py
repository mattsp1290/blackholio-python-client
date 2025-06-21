"""
Authentication Module - SpacetimeDB Identity and Token Management

Provides identity creation, management, and authentication for SpacetimeDB connections.
"""

from .identity_manager import IdentityManager, Identity
from .token_manager import TokenManager
from .auth_client import AuthenticatedClient

__all__ = [
    "IdentityManager",
    "Identity", 
    "TokenManager",
    "AuthenticatedClient"
]