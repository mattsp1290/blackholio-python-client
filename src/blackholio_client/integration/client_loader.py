"""
SpacetimeDB Client Loader

Dynamically loads and imports generated SpacetimeDB client modules
based on server language configuration.
"""

import os
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from types import ModuleType
from dataclasses import dataclass

from ..config.environment import EnvironmentConfig, get_environment_config
from ..exceptions.connection_errors import BlackholioConnectionError
from .client_generator import SpacetimeDBClientGenerator, GenerationResult


logger = logging.getLogger(__name__)


@dataclass
class LoadedClient:
    """Information about a loaded SpacetimeDB client."""
    language: str
    module: ModuleType
    client_dir: str
    main_module_path: str
    loaded_modules: List[str]


class ClientLoader:
    """
    Loads generated SpacetimeDB client modules dynamically.
    
    This class handles the dynamic loading and importing of SpacetimeDB
    client code generated for different server languages.
    """
    
    # Common client module names to look for
    CLIENT_MODULE_NAMES = [
        'client.py',
        '__init__.py',
        'spacetimedb_client.py',
        'lib.py',
        'stdb_client.py'
    ]
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """
        Initialize the client loader.
        
        Args:
            config: Environment configuration (uses global if not provided)
        """
        self.config = config or get_environment_config()
        self.generator = SpacetimeDBClientGenerator(self.config)
        self._loaded_clients: Dict[str, LoadedClient] = {}
        
        logger.info(f"SpacetimeDB Client Loader initialized for server language: {self.config.server_language}")
    
    def load_client(self, 
                   server_language: Optional[str] = None,
                   client_dir: Optional[str] = None,
                   force_reload: bool = False) -> LoadedClient:
        """
        Load a SpacetimeDB client for the specified server language.
        
        Args:
            server_language: Server language to load client for
            client_dir: Directory containing generated client (generates if not provided)
            force_reload: Force reload even if already loaded
            
        Returns:
            LoadedClient instance
            
        Raises:
            BlackholioConnectionError: If client loading fails
        """
        language = server_language or self.config.server_language
        
        # Check if already loaded and not forcing reload
        if not force_reload and language in self._loaded_clients:
            cached_client = self._loaded_clients[language]
            if self._validate_loaded_client(cached_client):
                logger.info(f"Using cached client for {language}")
                return cached_client
            else:
                # Remove invalid cached client
                del self._loaded_clients[language]
        
        # Get or generate client directory
        if not client_dir:
            client_dir = self.generator.get_cached_client(language)
            
            if not client_dir:
                logger.info(f"Generating client for {language}")
                generation_result = self.generator.generate_client(language)
                
                if not generation_result.success:
                    raise BlackholioConnectionError(
                        f"Failed to generate client for {language}: {generation_result.error_message}"
                    )
                
                client_dir = generation_result.output_dir
        
        # Load the client module
        try:
            loaded_client = self._load_client_from_directory(language, client_dir)
            
            # Cache the loaded client
            self._loaded_clients[language] = loaded_client
            
            logger.info(f"Successfully loaded client for {language} from {client_dir}")
            return loaded_client
            
        except Exception as e:
            logger.error(f"Failed to load client for {language}: {e}")
            raise BlackholioConnectionError(f"Client loading failed: {e}")
    
    def _load_client_from_directory(self, language: str, client_dir: str) -> LoadedClient:
        """
        Load a client module from a directory.
        
        Args:
            language: Server language
            client_dir: Directory containing client files
            
        Returns:
            LoadedClient instance
            
        Raises:
            BlackholioConnectionError: If loading fails
        """
        if not os.path.isdir(client_dir):
            raise BlackholioConnectionError(f"Client directory not found: {client_dir}")
        
        # Find the main client module
        main_module_path = self._find_main_module(client_dir)
        
        if not main_module_path:
            raise BlackholioConnectionError(
                f"No main client module found in {client_dir}. "
                f"Expected one of: {self.CLIENT_MODULE_NAMES}"
            )
        
        # Create a unique module name
        module_name = f"spacetimedb_client_{language}_{id(self)}"
        
        # Load the module
        try:
            spec = importlib.util.spec_from_file_location(module_name, main_module_path)
            if not spec or not spec.loader:
                raise BlackholioConnectionError(f"Failed to create module spec for {main_module_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add the client directory to sys.path temporarily
            original_path = sys.path.copy()
            client_dir_abs = os.path.abspath(client_dir)
            if client_dir_abs not in sys.path:
                sys.path.insert(0, client_dir_abs)
            
            try:
                spec.loader.exec_module(module)
            finally:
                # Restore original sys.path
                sys.path = original_path
            
            # Get list of loaded modules
            loaded_modules = self._get_loaded_modules(client_dir)
            
            return LoadedClient(
                language=language,
                module=module,
                client_dir=client_dir,
                main_module_path=main_module_path,
                loaded_modules=loaded_modules
            )
            
        except Exception as e:
            raise BlackholioConnectionError(f"Failed to load module from {main_module_path}: {e}")
    
    def _find_main_module(self, client_dir: str) -> Optional[str]:
        """
        Find the main client module in a directory.
        
        Args:
            client_dir: Directory to search
            
        Returns:
            Path to main module or None if not found
        """
        for module_name in self.CLIENT_MODULE_NAMES:
            module_path = os.path.join(client_dir, module_name)
            if os.path.isfile(module_path):
                return module_path
        
        # Look for Python files recursively
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Check if this looks like a main module
                    if self._is_main_module(file_path):
                        return file_path
        
        return None
    
    def _is_main_module(self, file_path: str) -> bool:
        """
        Check if a Python file looks like a main SpacetimeDB client module.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            True if this looks like a main module
        """
        try:
            file_path = Path(file_path).resolve()
            if not str(file_path).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for SpacetimeDB-related imports or classes
            spacetime_indicators = [
                'spacetimedb',
                'SpacetimeDBClient',
                'stdb_client',
                'reducer',
                'table',
                'subscribe',
                'connect'
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in spacetime_indicators)
            
        except Exception:
            return False
    
    def _get_loaded_modules(self, client_dir: str) -> List[str]:
        """
        Get list of Python modules in the client directory.
        
        Args:
            client_dir: Client directory
            
        Returns:
            List of module names
        """
        modules = []
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, client_dir)
                    modules.append(rel_path)
        
        return sorted(modules)
    
    def _validate_loaded_client(self, client: LoadedClient) -> bool:
        """
        Validate that a loaded client is still valid.
        
        Args:
            client: LoadedClient to validate
            
        Returns:
            True if client is valid
        """
        try:
            # Check if module is still accessible
            if not hasattr(client.module, '__name__'):
                return False
            
            # Check if client directory still exists
            if not os.path.isdir(client.client_dir):
                return False
            
            # Check if main module file still exists
            if not os.path.isfile(client.main_module_path):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_loaded_client(self, server_language: str) -> Optional[LoadedClient]:
        """
        Get a loaded client for the specified server language.
        
        Args:
            server_language: Server language
            
        Returns:
            LoadedClient or None if not loaded
        """
        client = self._loaded_clients.get(server_language)
        
        if client and self._validate_loaded_client(client):
            return client
        
        # Remove invalid client
        if server_language in self._loaded_clients:
            del self._loaded_clients[server_language]
        
        return None
    
    def reload_client(self, server_language: str) -> LoadedClient:
        """
        Reload a client for the specified server language.
        
        Args:
            server_language: Server language
            
        Returns:
            Reloaded LoadedClient instance
        """
        return self.load_client(server_language, force_reload=True)
    
    def load_all_clients(self, force_reload: bool = False) -> Dict[str, LoadedClient]:
        """
        Load clients for all supported server languages.
        
        Args:
            force_reload: Force reload for all languages
            
        Returns:
            Dictionary mapping language to LoadedClient
        """
        results = {}
        
        for language in self.generator.DEFAULT_SERVER_PATHS.keys():
            try:
                client = self.load_client(language, force_reload=force_reload)
                results[language] = client
                
            except Exception as e:
                logger.error(f"Failed to load client for {language}: {e}")
        
        return results
    
    def unload_client(self, server_language: str):
        """
        Unload a client for the specified server language.
        
        Args:
            server_language: Server language
        """
        if server_language in self._loaded_clients:
            del self._loaded_clients[server_language]
            logger.info(f"Unloaded client for {server_language}")
    
    def unload_all_clients(self):
        """Unload all cached clients."""
        self._loaded_clients.clear()
        logger.info("Unloaded all cached clients")
    
    def get_client_info(self, server_language: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded client.
        
        Args:
            server_language: Server language
            
        Returns:
            Dictionary with client information or None if not loaded
        """
        client = self.get_loaded_client(server_language)
        
        if not client:
            return None
        
        return {
            'language': client.language,
            'client_dir': client.client_dir,
            'main_module_path': client.main_module_path,
            'loaded_modules': client.loaded_modules,
            'module_name': client.module.__name__,
            'module_attributes': [attr for attr in dir(client.module) if not attr.startswith('_')]
        }
    
    def list_loaded_clients(self) -> List[str]:
        """
        List all currently loaded client languages.
        
        Returns:
            List of loaded client languages
        """
        return list(self._loaded_clients.keys())
    
    def create_client_instance(self, 
                              server_language: Optional[str] = None,
                              **kwargs) -> Any:
        """
        Create a client instance for the specified server language.
        
        Args:
            server_language: Server language (uses config default if not provided)
            **kwargs: Additional arguments to pass to client constructor
            
        Returns:
            Client instance
            
        Raises:
            BlackholioConnectionError: If client creation fails
        """
        language = server_language or self.config.server_language
        
        # Load the client module
        loaded_client = self.load_client(language)
        
        # Try to find a client class or factory function
        client_instance = self._create_instance_from_module(loaded_client.module, **kwargs)
        
        if client_instance is None:
            raise BlackholioConnectionError(
                f"Could not create client instance for {language}. "
                f"No suitable client class or factory function found."
            )
        
        return client_instance
    
    def _create_instance_from_module(self, module: ModuleType, **kwargs) -> Any:
        """
        Create a client instance from a loaded module.
        
        Args:
            module: Loaded module
            **kwargs: Constructor arguments
            
        Returns:
            Client instance or None if not found
        """
        # Common client class names
        client_class_names = [
            'SpacetimeDBClient',
            'Client',
            'StdbClient',
            'BlackholioClient'
        ]
        
        # Try to find a client class
        for class_name in client_class_names:
            if hasattr(module, class_name):
                client_class = getattr(module, class_name)
                try:
                    return client_class(**kwargs)
                except Exception as e:
                    logger.warning(f"Failed to instantiate {class_name}: {e}")
                    continue
        
        # Try to find factory functions
        factory_function_names = [
            'create_client',
            'get_client',
            'connect',
            'new_client'
        ]
        
        for func_name in factory_function_names:
            if hasattr(module, func_name):
                factory_func = getattr(module, func_name)
                try:
                    return factory_func(**kwargs)
                except Exception as e:
                    logger.warning(f"Failed to call {func_name}: {e}")
                    continue
        
        return None
    
    def __str__(self) -> str:
        """String representation of the loader."""
        return f"ClientLoader(language={self.config.server_language}, loaded={len(self._loaded_clients)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ClientLoader(config={self.config}, "
                f"loaded_clients={list(self._loaded_clients.keys())})")