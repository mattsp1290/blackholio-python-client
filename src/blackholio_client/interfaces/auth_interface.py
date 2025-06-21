"""
Authentication interface for SpacetimeDB client.

Provides an abstract interface for handling authentication and identity management
across different server languages and deployment configurations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable


class AuthInterface(ABC):
    """Abstract interface for SpacetimeDB authentication management."""

    @property
    @abstractmethod
    def identity(self) -> Optional[str]:
        """
        Get the current user identity.
        
        Returns:
            Current identity string or None if not authenticated
        """
        pass

    @property
    @abstractmethod
    def token(self) -> Optional[str]:
        """
        Get the current authentication token.
        
        Returns:
            Current token string or None if not authenticated
        """
        pass

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        pass

    @abstractmethod
    async def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """
        Authenticate with the SpacetimeDB server.
        
        Args:
            credentials: Optional credentials dictionary for authentication
            
        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    async def logout(self) -> bool:
        """
        Logout and clear authentication state.
        
        Returns:
            True if logout successful, False otherwise
        """
        pass

    @abstractmethod
    def save_token(self, file_path: Optional[str] = None) -> bool:
        """
        Save the current authentication token to disk.
        
        Args:
            file_path: Optional custom file path for saving token
            
        Returns:
            True if save successful, False otherwise
        """
        pass

    @abstractmethod
    def load_token(self, file_path: Optional[str] = None) -> bool:
        """
        Load authentication token from disk.
        
        Args:
            file_path: Optional custom file path for loading token
            
        Returns:
            True if load successful, False otherwise
        """
        pass

    @abstractmethod
    def clear_saved_token(self, file_path: Optional[str] = None) -> bool:
        """
        Clear saved authentication token from disk.
        
        Args:
            file_path: Optional custom file path for token file
            
        Returns:
            True if clear successful, False otherwise
        """
        pass

    @abstractmethod
    def on_authentication_changed(self, callback: Callable[[bool], None]) -> None:
        """
        Register a callback for authentication state changes.
        
        Args:
            callback: Function to call when authentication state changes
        """
        pass

    @abstractmethod
    def on_token_refresh(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for token refresh events.
        
        Args:
            callback: Function to call when token is refreshed
        """
        pass

    @abstractmethod
    def get_auth_info(self) -> Dict[str, Any]:
        """
        Get detailed authentication information.
        
        Returns:
            Dictionary containing auth details (identity, token status, etc.)
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> bool:
        """
        Refresh the current authentication token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass

    @abstractmethod
    def validate_token(self, token: Optional[str] = None) -> bool:
        """
        Validate an authentication token.
        
        Args:
            token: Token to validate (uses current token if None)
            
        Returns:
            True if token is valid, False otherwise
        """
        pass