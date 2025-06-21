"""Abstract base classes for the client factory pattern.

This module defines the abstract interfaces and base implementations for
the SpacetimeDB client factory pattern. All concrete factory implementations
must inherit from these base classes and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import logging
from pathlib import Path

from ..config.environment import EnvironmentConfig, get_environment_config
from ..integration.client_generator import SpacetimeDBClientGenerator
from ..integration.client_loader import ClientLoader
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import (
    BlackholioConfigurationError,
    BlackholioConnectionError,
)

logger = logging.getLogger(__name__)


class ClientFactory(ABC):
    """Abstract interface for SpacetimeDB client factories.
    
    This interface defines the contract that all concrete factory
    implementations must follow. Each factory is responsible for
    creating clients for a specific server language.
    """
    
    @abstractmethod
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for the specific server language.
        
        Args:
            identity: Optional identity token for authentication
            credentials: Optional credentials dictionary
            **kwargs: Additional keyword arguments for connection configuration
            
        Returns:
            SpacetimeDBConnection: Configured connection instance
            
        Raises:
            BlackholioConnectionError: If connection creation fails
            BlackholioConfigurationError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def get_client_module(self) -> Any:
        """Get the generated SpacetimeDB client module.
        
        Returns:
            Any: The loaded client module for the specific server language
            
        Raises:
            BlackholioConfigurationError: If client module cannot be loaded
        """
        pass
    
    @abstractmethod
    def validate_configuration(self) -> bool:
        """Validate the factory configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def server_language(self) -> str:
        """Get the server language this factory supports.
        
        Returns:
            str: The server language (e.g., 'rust', 'python', 'csharp', 'go')
        """
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this factory is available for use.
        
        This checks if all dependencies are met, generated clients exist,
        and the factory can successfully create connections.
        
        Returns:
            bool: True if factory is available, False otherwise
        """
        pass


class ClientFactoryBase(ClientFactory):
    """Base implementation of the ClientFactory with common functionality.
    
    This base class provides common implementation details that are shared
    across all concrete factory implementations. Subclasses should inherit
    from this class rather than directly from ClientFactory.
    """
    
    def __init__(
        self,
        config: Optional[EnvironmentConfig] = None,
        output_dir: Optional[Path] = None
    ):
        """Initialize the factory with configuration.
        
        Args:
            config: Environment configuration instance
            output_dir: Directory for generated client output
        """
        self.config = config or get_environment_config()
        self.output_dir = output_dir or Path.home() / ".blackholio" / "generated"
        self._client_generator: Optional[SpacetimeDBClientGenerator] = None
        self._client_loader: Optional[ClientLoader] = None
        self._client_module: Optional[Any] = None
        self._validated = False
        
    @property
    def client_generator(self) -> SpacetimeDBClientGenerator:
        """Get or create the client generator instance.
        
        Returns:
            SpacetimeDBClientGenerator: Client generator instance
        """
        if self._client_generator is None:
            self._client_generator = SpacetimeDBClientGenerator(
                output_dir=self.output_dir
            )
        return self._client_generator
    
    @property
    def client_loader(self) -> ClientLoader:
        """Get or create the client loader instance.
        
        Returns:
            ClientLoader: Client loader instance
        """
        if self._client_loader is None:
            self._client_loader = ClientLoader(
                generated_dir=self.output_dir
            )
        return self._client_loader
    
    def validate_configuration(self) -> bool:
        """Validate the factory configuration.
        
        This base implementation validates:
        - Environment configuration is valid
        - SpacetimeDB CLI is available
        - Server configuration matches expected language
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Validate environment config
            if not self.config.validate():
                logger.error("Environment configuration validation failed")
                return False
            
            # Validate server language matches
            if self.config.server_language != self.server_language:
                logger.error(
                    f"Server language mismatch: expected {self.server_language}, "
                    f"got {self.config.server_language}"
                )
                return False
            
            # Validate SpacetimeDB CLI is available
            if not self.client_generator.validate_spacetimedb_cli():
                logger.error("SpacetimeDB CLI validation failed")
                return False
            
            self._validated = True
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_client_module(self) -> Any:
        """Get the generated SpacetimeDB client module.
        
        This base implementation handles client generation and loading
        with caching to avoid regenerating clients unnecessarily.
        
        Returns:
            Any: The loaded client module
            
        Raises:
            BlackholioConfigurationError: If client cannot be generated or loaded
        """
        if self._client_module is not None:
            return self._client_module
        
        try:
            # Ensure configuration is validated
            if not self._validated and not self.validate_configuration():
                raise BlackholioConfigurationError(
                    f"Factory configuration validation failed for {self.server_language}"
                )
            
            # Check if client already exists
            module_name = f"blackholio_{self.server_language}_client"
            if self.client_loader.validate_client(module_name):
                logger.info(f"Loading existing client module: {module_name}")
                self._client_module = self.client_loader.load_client(module_name)
                return self._client_module
            
            # Generate client if needed
            logger.info(f"Generating new client for {self.server_language} server")
            server_path = self._get_server_path()
            
            success = self.client_generator.generate_client(
                server_path=server_path,
                server_language=self.server_language,
                output_name=module_name
            )
            
            if not success:
                raise BlackholioConfigurationError(
                    f"Failed to generate client for {self.server_language} server"
                )
            
            # Load the generated client
            self._client_module = self.client_loader.load_client(module_name)
            return self._client_module
            
        except Exception as e:
            logger.error(f"Failed to get client module: {e}")
            raise BlackholioConfigurationError(
                f"Cannot load client module for {self.server_language}: {str(e)}"
            )
    
    @abstractmethod
    def _get_server_path(self) -> Path:
        """Get the path to the server implementation.
        
        Subclasses must implement this to return the correct server path
        for their specific language.
        
        Returns:
            Path: Path to the server implementation
        """
        pass
    
    @property
    def is_available(self) -> bool:
        """Check if this factory is available for use.
        
        Returns:
            bool: True if factory can create clients
        """
        try:
            # Try to validate configuration
            if not self.validate_configuration():
                return False
            
            # Check if we can get the client module
            # Don't actually generate it, just check if it's possible
            module_name = f"blackholio_{self.server_language}_client"
            if self.client_loader.validate_client(module_name):
                return True
            
            # Check if server path exists
            server_path = self._get_server_path()
            return server_path.exists()
            
        except Exception as e:
            logger.debug(f"Factory availability check failed: {e}")
            return False
    
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for the specific server language.
        
        This base implementation handles common connection creation logic.
        
        Args:
            identity: Optional identity token
            credentials: Optional credentials dictionary
            **kwargs: Additional connection parameters
            
        Returns:
            SpacetimeDBConnection: Configured connection instance
            
        Raises:
            BlackholioConnectionError: If connection creation fails
        """
        try:
            # Get the client module to ensure it's available
            client_module = self.get_client_module()
            
            # Get connection URL from config
            url = self.config.get_connection_url()
            
            # Create connection with factory-specific configuration
            connection = SpacetimeDBConnection(
                url=url,
                identity=identity,
                credentials=credentials,
                server_language=self.server_language,
                client_module=client_module,
                **kwargs
            )
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise BlackholioConnectionError(
                f"Cannot create connection for {self.server_language} server: {str(e)}"
            )