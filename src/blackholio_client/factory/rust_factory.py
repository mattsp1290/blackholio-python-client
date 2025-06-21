"""Factory implementation for Rust SpacetimeDB servers.

This module provides a concrete factory implementation for creating
SpacetimeDB clients that work with Rust-based servers. Rust is the
default and reference implementation for SpacetimeDB servers.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import logging

from .base import ClientFactoryBase
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import BlackholioConfigurationError

logger = logging.getLogger(__name__)


class RustClientFactory(ClientFactoryBase):
    """Factory for creating clients for Rust SpacetimeDB servers.
    
    This factory handles the creation of SpacetimeDB clients specifically
    for Rust-based server implementations. It knows how to locate the Rust
    server files and generate appropriate clients.
    """
    
    @property
    def server_language(self) -> str:
        """Get the server language this factory supports.
        
        Returns:
            str: 'rust'
        """
        return "rust"
    
    def _get_server_path(self) -> Path:
        """Get the path to the Rust server implementation.
        
        Returns:
            Path: Path to the Rust server directory
            
        Raises:
            BlackholioConfigurationError: If server path doesn't exist
        """
        # Check multiple possible locations for the Rust server
        possible_paths = [
            Path.home() / "git" / "Blackholio" / "server-rust",
            Path.home() / "git" / "blackholio" / "server-rust",
            Path("/Users/punk1290/git/Blackholio/server-rust"),
            Path.cwd() / "server-rust",
        ]
        
        # Check if a custom path is configured
        custom_path = self.config.get("rust_server_path")
        if custom_path:
            possible_paths.insert(0, Path(custom_path))
        
        # Find the first existing path
        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found Rust server at: {path}")
                return path
        
        # No path found
        paths_str = "\n  ".join(str(p) for p in possible_paths)
        raise BlackholioConfigurationError(
            f"Cannot find Rust server implementation. Searched:\n  {paths_str}"
        )
    
    def validate_configuration(self) -> bool:
        """Validate the Rust factory configuration.
        
        This extends the base validation with Rust-specific checks.
        
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
                logger.error(f"Rust server path does not exist: {server_path}")
                return False
            
            # Check for Cargo.toml to validate it's a Rust project
            cargo_toml = server_path / "Cargo.toml"
            if not cargo_toml.exists():
                logger.error(f"No Cargo.toml found at: {server_path}")
                return False
            
            # Check for src directory
            src_dir = server_path / "src"
            if not src_dir.exists():
                logger.error(f"No src directory found at: {server_path}")
                return False
            
            logger.info("Rust factory configuration validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rust factory validation failed: {e}")
            return False
    
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for a Rust server.
        
        This method extends the base implementation with Rust-specific
        connection configuration.
        
        Args:
            identity: Optional identity token
            credentials: Optional credentials dictionary
            **kwargs: Additional connection parameters
            
        Returns:
            SpacetimeDBConnection: Configured connection for Rust server
        """
        # Add Rust-specific defaults
        rust_defaults = {
            "protocol_version": "v1.1.2",  # Rust servers use latest protocol
            "compression": True,  # Rust servers support compression
            "binary_protocol": True,  # Rust servers prefer binary protocol
        }
        
        # Merge with provided kwargs
        rust_defaults.update(kwargs)
        
        # Create connection using base implementation
        connection = super().create_connection(
            identity=identity,
            credentials=credentials,
            **rust_defaults
        )
        
        logger.info("Created Rust server connection")
        return connection
    
    @property
    def is_available(self) -> bool:
        """Check if the Rust factory is available.
        
        Returns:
            bool: True if Rust server and dependencies are available
        """
        try:
            # Check base availability
            if not super().is_available:
                return False
            
            # Additional Rust-specific checks
            server_path = self._get_server_path()
            
            # Check for compiled server binary
            target_dir = server_path / "target"
            if target_dir.exists():
                # Look for release or debug binary
                for profile in ["release", "debug"]:
                    binary = target_dir / profile / "blackholio-server"
                    if binary.exists():
                        logger.debug(f"Found compiled Rust server at: {binary}")
                        return True
            
            # Server source exists but not compiled
            logger.debug("Rust server source found but not compiled")
            return True  # We can still generate clients from source
            
        except Exception as e:
            logger.debug(f"Rust factory availability check failed: {e}")
            return False