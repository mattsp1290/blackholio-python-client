"""Factory implementation for Python SpacetimeDB servers.

This module provides a concrete factory implementation for creating
SpacetimeDB clients that work with Python-based servers. Python servers
offer native Python integration and easier debugging.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import logging

from .base import ClientFactoryBase
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import BlackholioConfigurationError

logger = logging.getLogger(__name__)


class PythonClientFactory(ClientFactoryBase):
    """Factory for creating clients for Python SpacetimeDB servers.
    
    This factory handles the creation of SpacetimeDB clients specifically
    for Python-based server implementations. It provides optimizations for
    Python-to-Python communication.
    """
    
    @property
    def server_language(self) -> str:
        """Get the server language this factory supports.
        
        Returns:
            str: 'python'
        """
        return "python"
    
    def _get_server_path(self) -> Path:
        """Get the path to the Python server implementation.
        
        Returns:
            Path: Path to the Python server directory
            
        Raises:
            BlackholioConfigurationError: If server path doesn't exist
        """
        # Check multiple possible locations for the Python server
        possible_paths = [
            Path.home() / "git" / "Blackholio" / "server-python",
            Path.home() / "git" / "blackholio" / "server-python",
            Path("/Users/punk1290/git/Blackholio/server-python"),
            Path.cwd() / "server-python",
        ]
        
        # Check if a custom path is configured
        custom_path = self.config.get("python_server_path")
        if custom_path:
            possible_paths.insert(0, Path(custom_path))
        
        # Find the first existing path
        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found Python server at: {path}")
                return path
        
        # No path found
        paths_str = "\n  ".join(str(p) for p in possible_paths)
        raise BlackholioConfigurationError(
            f"Cannot find Python server implementation. Searched:\n  {paths_str}"
        )
    
    def validate_configuration(self) -> bool:
        """Validate the Python factory configuration.
        
        This extends the base validation with Python-specific checks.
        
        Returns:
            bool: True if configuration is valid
        """
        # First run base validation
        if not super().validate_configuration():
            return False
        
        try:
            # Check that server path exists
            server_path = self._get_server_path()
            if not server_path.exists():
                logger.error(f"Python server path does not exist: {server_path}")
                return False
            
            # Check for Python project indicators
            python_indicators = [
                "pyproject.toml",
                "setup.py",
                "requirements.txt",
                "main.py",
                "__main__.py",
            ]
            
            found_indicator = False
            for indicator in python_indicators:
                if (server_path / indicator).exists():
                    found_indicator = True
                    break
            
            if not found_indicator:
                logger.error(
                    f"No Python project indicators found at: {server_path}"
                )
                return False
            
            # Check for src or module directory
            module_indicators = ["src", "blackholio_server", "server"]
            found_module = False
            for module in module_indicators:
                if (server_path / module).exists():
                    found_module = True
                    break
            
            if not found_module and not (server_path / "main.py").exists():
                logger.error(f"No Python module structure found at: {server_path}")
                return False
            
            logger.info("Python factory configuration validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Python factory validation failed: {e}")
            return False
    
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for a Python server.
        
        This method extends the base implementation with Python-specific
        optimizations and configuration.
        
        Args:
            identity: Optional identity token
            credentials: Optional credentials dictionary
            **kwargs: Additional connection parameters
            
        Returns:
            SpacetimeDBConnection: Configured connection for Python server
        """
        # Add Python-specific defaults
        python_defaults = {
            "protocol_version": "v1.1.2",
            "compression": False,  # Python servers may have optional compression
            "binary_protocol": False,  # Python servers may prefer JSON
            "serialization": "json",  # Python works well with JSON
            "enable_type_checking": True,  # Python supports runtime type checking
        }
        
        # Merge with provided kwargs
        python_defaults.update(kwargs)
        
        # Create connection using base implementation
        connection = super().create_connection(
            identity=identity,
            credentials=credentials,
            **python_defaults
        )
        
        logger.info("Created Python server connection")
        return connection
    
    @property
    def is_available(self) -> bool:
        """Check if the Python factory is available.
        
        Returns:
            bool: True if Python server and dependencies are available
        """
        try:
            # Check base availability
            if not super().is_available:
                return False
            
            # Additional Python-specific checks
            server_path = self._get_server_path()
            
            # Check for virtual environment
            venv_indicators = [".venv", "venv", "env", ".env"]
            has_venv = any((server_path / venv).exists() for venv in venv_indicators)
            
            if has_venv:
                logger.debug("Python server has virtual environment")
            
            # Check for installed dependencies
            site_packages = None
            for venv in venv_indicators:
                venv_path = server_path / venv
                if venv_path.exists():
                    # Look for site-packages in common locations
                    possible_sites = [
                        venv_path / "lib" / "python3.8" / "site-packages",
                        venv_path / "lib" / "python3.9" / "site-packages",
                        venv_path / "lib" / "python3.10" / "site-packages",
                        venv_path / "lib" / "python3.11" / "site-packages",
                        venv_path / "Lib" / "site-packages",  # Windows
                    ]
                    for site in possible_sites:
                        if site.exists():
                            site_packages = site
                            break
                    if site_packages:
                        break
            
            # Python server is available if source exists
            # Dependencies can be installed on demand
            return True
            
        except Exception as e:
            logger.debug(f"Python factory availability check failed: {e}")
            return False