"""Registry for managing client factory implementations.

This module provides a registry pattern for managing and accessing
different client factory implementations. The registry allows for
dynamic registration of factories and provides a centralized way
to access the appropriate factory based on server language.
"""

from typing import Dict, Optional, Type
import logging
from threading import Lock

from .base import ClientFactory
from ..exceptions.connection_errors import BlackholioConfigurationError

logger = logging.getLogger(__name__)


class ClientFactoryRegistry:
    """Registry for managing client factory implementations.
    
    This class implements a thread-safe registry pattern for storing
    and retrieving client factory implementations based on server language.
    It follows the singleton pattern to ensure a single registry instance.
    """
    
    _instance: Optional["ClientFactoryRegistry"] = None
    _lock = Lock()
    
    def __new__(cls) -> "ClientFactoryRegistry":
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the registry."""
        if not hasattr(self, "_initialized"):
            self._factories: Dict[str, Type[ClientFactory]] = {}
            self._instances: Dict[str, ClientFactory] = {}
            self._initialized = True
            logger.debug("ClientFactoryRegistry initialized")
    
    @classmethod
    def get_instance(cls) -> "ClientFactoryRegistry":
        """Get the singleton registry instance.
        
        Returns:
            ClientFactoryRegistry: The registry instance
        """
        return cls()
    
    def register(
        self,
        language: str,
        factory_class: Type[ClientFactory],
        replace: bool = False
    ) -> None:
        """Register a factory class for a specific server language.
        
        Args:
            language: The server language (e.g., 'rust', 'python')
            factory_class: The factory class to register
            replace: Whether to replace an existing registration
            
        Raises:
            BlackholioConfigurationError: If language already registered and replace=False
        """
        language = language.lower()
        
        if language in self._factories and not replace:
            raise BlackholioConfigurationError(
                f"Factory for language '{language}' is already registered. "
                "Use replace=True to override."
            )
        
        self._factories[language] = factory_class
        # Clear any cached instance when registering new factory
        if language in self._instances:
            del self._instances[language]
        
        logger.info(f"Registered factory for language: {language}")
    
    def unregister(self, language: str) -> None:
        """Unregister a factory for a specific server language.
        
        Args:
            language: The server language to unregister
        """
        language = language.lower()
        
        if language in self._factories:
            del self._factories[language]
            if language in self._instances:
                del self._instances[language]
            logger.info(f"Unregistered factory for language: {language}")
        else:
            logger.warning(f"No factory registered for language: {language}")
    
    def get_factory_class(self, language: str) -> Type[ClientFactory]:
        """Get the factory class for a specific server language.
        
        Args:
            language: The server language
            
        Returns:
            Type[ClientFactory]: The factory class
            
        Raises:
            BlackholioConfigurationError: If no factory registered for language
        """
        language = language.lower()
        
        if language not in self._factories:
            available = ", ".join(sorted(self._factories.keys()))
            raise BlackholioConfigurationError(
                f"No factory registered for language '{language}'. "
                f"Available languages: {available}"
            )
        
        return self._factories[language]
    
    def get_factory(
        self,
        language: str,
        cache: bool = True,
        **kwargs
    ) -> ClientFactory:
        """Get or create a factory instance for a specific server language.
        
        Args:
            language: The server language
            cache: Whether to cache and reuse factory instances
            **kwargs: Additional arguments for factory initialization
            
        Returns:
            ClientFactory: The factory instance
            
        Raises:
            BlackholioConfigurationError: If no factory registered for language
        """
        language = language.lower()
        
        # Return cached instance if available and caching enabled
        if cache and language in self._instances:
            return self._instances[language]
        
        # Get factory class
        factory_class = self.get_factory_class(language)
        
        # Create new instance
        try:
            factory_instance = factory_class(**kwargs)
            
            # Cache if requested
            if cache:
                self._instances[language] = factory_instance
            
            logger.debug(f"Created factory instance for language: {language}")
            return factory_instance
            
        except Exception as e:
            logger.error(f"Failed to create factory for {language}: {e}")
            raise BlackholioConfigurationError(
                f"Cannot instantiate factory for language '{language}': {str(e)}"
            )
    
    def list_languages(self) -> list[str]:
        """List all registered server languages.
        
        Returns:
            list[str]: List of registered language names
        """
        return sorted(self._factories.keys())
    
    def has_factory(self, language: str) -> bool:
        """Check if a factory is registered for a language.
        
        Args:
            language: The server language to check
            
        Returns:
            bool: True if factory is registered
        """
        return language.lower() in self._factories
    
    def get_available_factories(self) -> Dict[str, ClientFactory]:
        """Get all available factory instances.
        
        This method creates instances of all registered factories
        and returns only those that are available for use.
        
        Returns:
            Dict[str, ClientFactory]: Map of language to available factory instances
        """
        available = {}
        
        for language in self._factories:
            try:
                factory = self.get_factory(language, cache=True)
                if factory.is_available:
                    available[language] = factory
                else:
                    logger.debug(f"Factory for {language} is not available")
            except Exception as e:
                logger.debug(f"Cannot create factory for {language}: {e}")
        
        return available
    
    def clear(self) -> None:
        """Clear all registered factories and cached instances.
        
        This is mainly useful for testing or resetting the registry.
        """
        self._factories.clear()
        self._instances.clear()
        logger.info("Cleared all registered factories")
    
    def __repr__(self) -> str:
        """Return string representation of the registry."""
        languages = ", ".join(self.list_languages())
        return f"ClientFactoryRegistry(languages=[{languages}])"


# Create and export the global registry instance
registry = ClientFactoryRegistry.get_instance()