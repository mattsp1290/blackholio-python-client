"""
Token Manager - SpacetimeDB Authentication Token Management

Handles token lifecycle, refresh, and session management for SpacetimeDB connections.
"""

import time
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .identity_manager import Identity
from ..exceptions.connection_errors import (
    AuthenticationError,
    BlackholioTimeoutError
)


logger = logging.getLogger(__name__)


@dataclass
class AuthToken:
    """
    Authentication token representation.
    
    Contains token data, expiration, and metadata for SpacetimeDB authentication.
    """
    token: str
    token_type: str = "Bearer"
    expires_at: Optional[float] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    issued_at: Optional[float] = None
    identity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.issued_at is None:
            self.issued_at = time.time()
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> Optional[float]:
        """Get seconds until token expires."""
        if self.expires_at is None:
            return None
        return max(0, self.expires_at - time.time())
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (exists and not expired)."""
        return bool(self.token and not self.is_expired)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthToken':
        """Create AuthToken from dictionary."""
        return cls(
            token=data['token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_at=data.get('expires_at'),
            refresh_token=data.get('refresh_token'),
            scope=data.get('scope'),
            issued_at=data.get('issued_at'),
            identity_id=data.get('identity_id'),
            metadata=data.get('metadata', {})
        )
    
    def get_authorization_header(self) -> str:
        """Get authorization header value."""
        return f"{self.token_type} {self.token}"


class TokenManager:
    """
    Manages authentication tokens for SpacetimeDB connections.
    
    Handles token creation, storage, refresh, and validation with automatic
    refresh capabilities and session management.
    """
    
    def __init__(self, auto_refresh: bool = True, refresh_buffer: float = 300.0):
        """
        Initialize token manager.
        
        Args:
            auto_refresh: Whether to automatically refresh tokens
            refresh_buffer: Seconds before expiry to trigger refresh
        """
        self.auto_refresh = auto_refresh
        self.refresh_buffer = refresh_buffer
        
        # Token storage
        self._tokens: Dict[str, AuthToken] = {}  # identity_id -> token
        self._refresh_tasks: Dict[str, asyncio.Task] = {}  # identity_id -> refresh task
        
        # Callbacks
        self._token_refreshed_callbacks: Dict[str, Callable] = {}
        self._token_expired_callbacks: Dict[str, Callable] = {}
        
        logger.info("Token manager initialized")
    
    def store_token(self, identity: Identity, token: AuthToken) -> bool:
        """
        Store authentication token for an identity.
        
        Args:
            identity: Identity object
            token: Authentication token
            
        Returns:
            True if stored successfully
        """
        try:
            # Update token with identity ID
            token.identity_id = identity.identity_id
            
            # Store token
            self._tokens[identity.identity_id] = token
            
            # Start auto-refresh if enabled
            if self.auto_refresh and token.expires_at:
                self._schedule_token_refresh(identity.identity_id, token)
            
            logger.info(f"Stored token for identity {identity.name} (expires: {token.expires_at})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store token for identity {identity.name}: {e}")
            return False
    
    def get_token(self, identity: Identity) -> Optional[AuthToken]:
        """
        Get authentication token for an identity.
        
        Args:
            identity: Identity object
            
        Returns:
            AuthToken if available and valid, None otherwise
        """
        token = self._tokens.get(identity.identity_id)
        
        if token is None:
            return None
        
        if token.is_expired:
            logger.warning(f"Token expired for identity {identity.identity_id}")
            self.remove_token(identity)
            return None
        
        return token
    
    def get_valid_token(self, identity: Identity) -> Optional[AuthToken]:
        """
        Get valid token, attempting refresh if needed.
        
        Args:
            identity: Identity object
            
        Returns:
            Valid AuthToken or None if unavailable
        """
        token = self.get_token(identity)
        
        if token is None:
            return None
        
        # Check if token needs refresh
        if (token.expires_at and 
            token.expires_in_seconds and 
            token.expires_in_seconds < self.refresh_buffer):
            
            logger.info(f"Token for identity {identity.identity_id} needs refresh")
            # For now, return None - actual refresh would be implemented with server API
            return None
        
        return token
    
    def remove_token(self, identity: Identity) -> bool:
        """
        Remove token for an identity.
        
        Args:
            identity: Identity object
            
        Returns:
            True if removed, False if not found
        """
        identity_id = identity.identity_id
        
        # Cancel refresh task
        if identity_id in self._refresh_tasks:
            self._refresh_tasks[identity_id].cancel()
            del self._refresh_tasks[identity_id]
        
        # Remove token
        if identity_id in self._tokens:
            del self._tokens[identity_id]
            logger.info(f"Removed token for identity {identity.name}")
            return True
        
        return False
    
    def clear_all_tokens(self):
        """Clear all stored tokens."""
        # Cancel all refresh tasks
        for task in self._refresh_tasks.values():
            task.cancel()
        self._refresh_tasks.clear()
        
        # Clear tokens
        self._tokens.clear()
        logger.info("Cleared all tokens")
    
    def get_tokens_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of all stored tokens.
        
        Returns:
            Dictionary with token summaries
        """
        summary = {}
        
        for identity_id, token in self._tokens.items():
            summary[identity_id] = {
                'token_type': token.token_type,
                'expires_at': token.expires_at,
                'expires_in_seconds': token.expires_in_seconds,
                'is_valid': token.is_valid,
                'has_refresh_token': bool(token.refresh_token),
                'scope': token.scope
            }
        
        return summary
    
    async def authenticate_with_identity(self, identity: Identity, 
                                       challenge_data: Optional[Dict[str, Any]] = None) -> Optional[AuthToken]:
        """
        Authenticate with SpacetimeDB using an identity.
        
        Args:
            identity: Identity to authenticate with
            challenge_data: Optional challenge data from server
            
        Returns:
            AuthToken if authentication successful
        """
        try:
            # Create authentication message
            auth_data = self._create_auth_message(identity, challenge_data)
            
            # TODO: Send authentication request to SpacetimeDB server
            # This would be implemented with actual server communication
            
            # For now, create a mock token for development
            token = self._create_mock_token(identity)
            
            # Store the token
            if self.store_token(identity, token):
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication failed for identity {identity.name}: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def _create_auth_message(self, identity: Identity, challenge_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create authentication message for SpacetimeDB."""
        import base64
        
        # Basic authentication data
        auth_data = {
            'identity_id': identity.identity_id,
            'public_key': identity.public_key,
            'timestamp': time.time()
        }
        
        # Add challenge response if provided
        if challenge_data:
            # Sign the challenge with identity's private key
            challenge_bytes = json.dumps(challenge_data, sort_keys=True).encode('utf-8')
            signature = identity.sign_data(challenge_bytes)
            auth_data['challenge_response'] = base64.b64encode(signature).decode('ascii')
        
        # Sign the authentication data
        auth_bytes = json.dumps(auth_data, sort_keys=True).encode('utf-8')
        signature = identity.sign_data(auth_bytes)
        auth_data['signature'] = base64.b64encode(signature).decode('ascii')
        
        return auth_data
    
    def _create_mock_token(self, identity: Identity) -> AuthToken:
        """Create mock token for development/testing."""
        import secrets
        import base64
        
        # Generate mock token
        token_data = f"{identity.identity_id}:{secrets.token_hex(32)}"
        token_b64 = base64.b64encode(token_data.encode()).decode('ascii')
        
        # Token expires in 1 hour
        expires_at = time.time() + 3600
        
        return AuthToken(
            token=token_b64,
            token_type=self.TOKEN_TYPE_BEARER,
            expires_at=expires_at,
            identity_id=identity.identity_id,
            scope="game:read,game:write",
            metadata={"mock": True}
        )
    
    def _schedule_token_refresh(self, identity_id: str, token: AuthToken):
        """Schedule automatic token refresh."""
        if not token.expires_at:
            return
        
        # Calculate refresh time (buffer seconds before expiry)
        refresh_time = token.expires_at - self.refresh_buffer
        delay = max(0, refresh_time - time.time())
        
        # Cancel existing refresh task
        if identity_id in self._refresh_tasks:
            self._refresh_tasks[identity_id].cancel()
        
        # Schedule new refresh task
        async def refresh_task():
            try:
                await asyncio.sleep(delay)
                await self._refresh_token(identity_id)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Token refresh failed for identity {identity_id}: {e}")
        
        self._refresh_tasks[identity_id] = asyncio.create_task(refresh_task())
        logger.debug(f"Scheduled token refresh for identity {identity_id} in {delay:.1f}s")
    
    async def _refresh_token(self, identity_id: str):
        """Refresh token for an identity."""
        token = self._tokens.get(identity_id)
        if not token:
            return
        
        try:
            # TODO: Implement actual token refresh with server
            logger.info(f"Refreshing token for identity {identity_id}")
            
            # For now, extend expiry time (mock refresh)
            token.expires_at = time.time() + 3600
            
            # Reschedule next refresh
            self._schedule_token_refresh(identity_id, token)
            
            # Trigger callback
            callback = self._token_refreshed_callbacks.get(identity_id)
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(token)
                    else:
                        callback(token)
                except Exception as e:
                    logger.error(f"Token refresh callback failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to refresh token for identity {identity_id}: {e}")
            
            # Remove expired token
            if identity_id in self._tokens:
                del self._tokens[identity_id]
            
            # Trigger expiry callback
            callback = self._token_expired_callbacks.get(identity_id)
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(identity_id)
                    else:
                        callback(identity_id)
                except Exception as e:
                    logger.error(f"Token expiry callback failed: {e}")
    
    def on_token_refreshed(self, identity_id: str, callback: Callable):
        """Register callback for token refresh events."""
        self._token_refreshed_callbacks[identity_id] = callback
    
    def on_token_expired(self, identity_id: str, callback: Callable):
        """Register callback for token expiry events."""
        self._token_expired_callbacks[identity_id] = callback
    
    async def shutdown(self):
        """Shutdown token manager and cleanup tasks."""
        # Cancel all refresh tasks
        for task in self._refresh_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._refresh_tasks.clear()
        logger.info("Token manager shutdown complete")


# Global token manager instance
_global_token_manager: Optional[TokenManager] = None


def get_token_manager(auto_refresh: bool = True) -> TokenManager:
    """
    Get global token manager instance.
    
    Args:
        auto_refresh: Enable auto-refresh (only used on first call)
        
    Returns:
        TokenManager instance
    """
    global _global_token_manager
    
    if _global_token_manager is None:
        _global_token_manager = TokenManager(auto_refresh=auto_refresh)
    
    return _global_token_manager


def set_token_manager(manager: TokenManager):
    """
    Set global token manager instance.
    
    Args:
        manager: TokenManager instance to set as global
    """
    global _global_token_manager
    _global_token_manager = manager