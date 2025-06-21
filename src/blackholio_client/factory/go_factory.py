"""Factory implementation for Go SpacetimeDB servers.

This module provides a concrete factory implementation for creating
SpacetimeDB clients that work with Go-based servers. Go servers offer
excellent performance and concurrent processing capabilities.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import logging

from .base import ClientFactoryBase
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import BlackholioConfigurationError

logger = logging.getLogger(__name__)


class GoClientFactory(ClientFactoryBase):
    """Factory for creating clients for Go SpacetimeDB servers.
    
    This factory handles the creation of SpacetimeDB clients specifically
    for Go-based server implementations. It handles Go module structures
    and build configurations.
    """
    
    @property
    def server_language(self) -> str:
        """Get the server language this factory supports.
        
        Returns:
            str: 'go'
        """
        return "go"
    
    def _get_server_path(self) -> Path:
        """Get the path to the Go server implementation.
        
        Returns:
            Path: Path to the Go server directory
            
        Raises:
            BlackholioConfigurationError: If server path doesn't exist
        """
        # Check multiple possible locations for the Go server
        possible_paths = [
            Path.home() / "git" / "Blackholio" / "server-go",
            Path.home() / "git" / "blackholio" / "server-go",
            Path("/Users/punk1290/git/Blackholio/server-go"),
            Path.cwd() / "server-go",
            Path.home() / "git" / "Blackholio" / "server-golang",
            Path.cwd() / "server-golang",
        ]
        
        # Check if a custom path is configured
        custom_path = self.config.get("go_server_path")
        if custom_path:
            possible_paths.insert(0, Path(custom_path))
        
        # Find the first existing path
        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found Go server at: {path}")
                return path
        
        # No path found
        paths_str = "\n  ".join(str(p) for p in possible_paths)
        raise BlackholioConfigurationError(
            f"Cannot find Go server implementation. Searched:\n  {paths_str}"
        )
    
    def validate_configuration(self) -> bool:
        """Validate the Go factory configuration.
        
        This extends the base validation with Go-specific checks.
        
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
                logger.error(f"Go server path does not exist: {server_path}")
                return False
            
            # Check for Go module files
            go_indicators = [
                "go.mod",
                "go.sum",
                "main.go",
                "Makefile",
                "Dockerfile",
            ]
            
            found_indicator = False
            for indicator in go_indicators:
                if (server_path / indicator).exists():
                    found_indicator = True
                    break
            
            if not found_indicator:
                logger.error(
                    f"No Go project indicators found at: {server_path}"
                )
                return False
            
            # Check for Go source files
            go_files = list(server_path.glob("*.go"))
            if not go_files:
                # Check in subdirectories
                go_files = list(server_path.glob("**/*.go"))
            
            if not go_files:
                logger.error(f"No Go source files found at: {server_path}")
                return False
            
            # Check for go.mod specifically (modern Go projects)
            go_mod = server_path / "go.mod"
            if go_mod.exists():
                logger.debug("Found go.mod - modern Go module")
            else:
                logger.warning(
                    "No go.mod found - may be legacy GOPATH project"
                )
            
            logger.info("Go factory configuration validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Go factory validation failed: {e}")
            return False
    
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for a Go server.
        
        This method extends the base implementation with Go-specific
        configuration and optimizations.
        
        Args:
            identity: Optional identity token
            credentials: Optional credentials dictionary
            **kwargs: Additional connection parameters
            
        Returns:
            SpacetimeDBConnection: Configured connection for Go server
        """
        # Add Go-specific defaults
        go_defaults = {
            "protocol_version": "v1.1.2",
            "compression": True,  # Go has excellent compression support
            "binary_protocol": True,  # Go excels at binary protocols
            "serialization": "protobuf",  # Go commonly uses Protocol Buffers
            "connection_pooling": True,  # Go's goroutines make pooling efficient
            "concurrent_requests": True,  # Go handles concurrency well
            "max_connections": 100,  # Go can handle many concurrent connections
        }
        
        # Merge with provided kwargs
        go_defaults.update(kwargs)
        
        # Create connection using base implementation
        connection = super().create_connection(
            identity=identity,
            credentials=credentials,
            **go_defaults
        )
        
        logger.info("Created Go server connection")
        return connection
    
    @property
    def is_available(self) -> bool:
        """Check if the Go factory is available.
        
        Returns:
            bool: True if Go server and dependencies are available
        """
        try:
            # Check base availability
            if not super().is_available:
                return False
            
            # Additional Go-specific checks
            server_path = self._get_server_path()
            
            # Check for Go binary output
            binary_names = [
                "blackholio-server",
                "server",
                "main",
                server_path.name,  # Binary might be named after directory
            ]
            
            found_binary = False
            for binary_name in binary_names:
                binary_path = server_path / binary_name
                if binary_path.exists() and binary_path.is_file():
                    logger.debug(f"Found Go binary: {binary_path}")
                    found_binary = True
                    break
            
            # Check for vendor directory (dependency vendoring)
            vendor_dir = server_path / "vendor"
            if vendor_dir.exists():
                logger.debug("Go server has vendored dependencies")
            
            # Check for go.sum (indicates dependencies are resolved)
            go_sum = server_path / "go.sum"
            if go_sum.exists():
                logger.debug("Go server has dependency lock file")
            
            # Check for build cache
            build_cache = server_path / ".build"
            if build_cache.exists():
                logger.debug("Go server has build cache")
            
            # Go server is available if source exists
            # Can be built quickly on demand
            return True
            
        except Exception as e:
            logger.debug(f"Go factory availability check failed: {e}")
            return False