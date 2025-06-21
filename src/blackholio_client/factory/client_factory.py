"""High-level client factory functions for SpacetimeDB clients.

This module provides the main entry points for creating SpacetimeDB
clients using the factory pattern. It handles factory registration,
selection based on environment configuration, and provides convenient
functions for client creation.
"""

from typing import Any, Dict, Optional, Union
import logging
from pathlib import Path

from .registry import registry
from .base import ClientFactory
from .rust_factory import RustClientFactory
from .python_factory import PythonClientFactory
from .csharp_factory import CSharpClientFactory
from .go_factory import GoClientFactory
from ..config.environment import EnvironmentConfig
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import (
    BlackholioConfigurationError,
    BlackholioConnectionError,
)

logger = logging.getLogger(__name__)

# Register all factory implementations
def _register_factories():
    """Register all available factory implementations."""
    registry.register("rust", RustClientFactory)
    registry.register("python", PythonClientFactory)
    registry.register("csharp", CSharpClientFactory)
    registry.register("go", GoClientFactory)
    logger.debug("Registered all client factories")

# Auto-register on module import
_register_factories()


def get_client_factory(
    language: Optional[str] = None,
    config: Optional[EnvironmentConfig] = None,
    **kwargs: Any
) -> ClientFactory:
    """Get a client factory for the specified or configured language.
    
    This function returns the appropriate factory instance based on
    the server language. If no language is specified, it uses the
    configured SERVER_LANGUAGE environment variable.
    
    Args:
        language: Optional server language override
        config: Optional environment configuration
        **kwargs: Additional arguments for factory initialization
        
    Returns:
        ClientFactory: The appropriate factory instance
        
    Raises:
        BlackholioConfigurationError: If language is not supported
    """
    # Get configuration
    if config is None:
        config = EnvironmentConfig.get_instance()
    
    # Determine language
    if language is None:
        language = config.server_language
    
    language = language.lower()
    logger.info(f"Getting client factory for language: {language}")
    
    # Get factory from registry
    try:
        factory = registry.get_factory(
            language=language,
            config=config,
            **kwargs
        )
        
        # Validate factory is available
        if not factory.is_available:
            raise BlackholioConfigurationError(
                f"Factory for {language} is registered but not available. "
                f"Check server installation and configuration."
            )
        
        return factory
        
    except BlackholioConfigurationError:
        # Re-raise configuration errors
        raise
    except Exception as e:
        logger.error(f"Failed to get factory for {language}: {e}")
        raise BlackholioConfigurationError(
            f"Cannot get factory for language '{language}': {str(e)}"
        )


def create_client(
    identity: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
    config: Optional[EnvironmentConfig] = None,
    factory: Optional[ClientFactory] = None,
    **kwargs: Any
) -> SpacetimeDBConnection:
    """Create a SpacetimeDB client connection.
    
    This is the main entry point for creating SpacetimeDB clients.
    It automatically selects the appropriate factory based on the
    configured server language and creates a connection.
    
    Args:
        identity: Optional identity token for authentication
        credentials: Optional credentials dictionary
        language: Optional server language override
        config: Optional environment configuration
        factory: Optional factory instance to use directly
        **kwargs: Additional connection parameters
        
    Returns:
        SpacetimeDBConnection: Configured connection instance
        
    Raises:
        BlackholioConnectionError: If connection creation fails
        BlackholioConfigurationError: If configuration is invalid
        
    Example:
        # Create client using environment configuration
        client = create_client()
        
        # Create client for specific language
        client = create_client(language="python")
        
        # Create client with authentication
        client = create_client(
            identity="user123",
            credentials={"token": "secret"}
        )
    """
    try:
        # Use provided factory or get one based on language
        if factory is None:
            factory = get_client_factory(
                language=language,
                config=config
            )
        
        logger.info(
            f"Creating client using {factory.server_language} factory"
        )
        
        # Create connection using factory
        connection = factory.create_connection(
            identity=identity,
            credentials=credentials,
            **kwargs
        )
        
        logger.info("Successfully created SpacetimeDB client connection")
        return connection
        
    except (BlackholioConnectionError, BlackholioConfigurationError):
        # Re-raise our exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to create client: {e}")
        raise BlackholioConnectionError(
            f"Cannot create SpacetimeDB client: {str(e)}"
        )


def list_available_languages() -> list[str]:
    """List all available server languages.
    
    Returns languages that have both registered factories and
    available server implementations.
    
    Returns:
        list[str]: List of available language names
    """
    available_factories = registry.get_available_factories()
    return sorted(available_factories.keys())


def get_factory_info() -> Dict[str, Dict[str, Any]]:
    """Get information about all registered factories.
    
    Returns:
        Dict[str, Dict[str, Any]]: Factory information by language
    """
    info = {}
    
    for language in registry.list_languages():
        try:
            factory = registry.get_factory(language, cache=True)
            info[language] = {
                "registered": True,
                "available": factory.is_available,
                "validated": factory.validate_configuration(),
                "server_language": factory.server_language,
                "class": factory.__class__.__name__,
            }
        except Exception as e:
            info[language] = {
                "registered": True,
                "available": False,
                "validated": False,
                "error": str(e),
            }
    
    return info


def create_all_available_clients(
    identity: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Dict[str, Union[SpacetimeDBConnection, Exception]]:
    """Create clients for all available server languages.
    
    This is useful for testing or when you need to work with
    multiple server implementations simultaneously.
    
    Args:
        identity: Optional identity token
        credentials: Optional credentials dictionary
        **kwargs: Additional connection parameters
        
    Returns:
        Dict[str, Union[SpacetimeDBConnection, Exception]]: 
            Map of language to connection or exception
    """
    results = {}
    
    for language in list_available_languages():
        try:
            client = create_client(
                identity=identity,
                credentials=credentials,
                language=language,
                **kwargs
            )
            results[language] = client
            logger.info(f"Created client for {language}")
        except Exception as e:
            results[language] = e
            logger.error(f"Failed to create client for {language}: {e}")
    
    return results