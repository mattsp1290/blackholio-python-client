"""Factory implementation for C# SpacetimeDB servers.

This module provides a concrete factory implementation for creating
SpacetimeDB clients that work with C#/.NET-based servers. C# servers
offer high performance and strong typing.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import logging

from .base import ClientFactoryBase
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..exceptions.connection_errors import BlackholioConfigurationError

logger = logging.getLogger(__name__)


class CSharpClientFactory(ClientFactoryBase):
    """Factory for creating clients for C# SpacetimeDB servers.
    
    This factory handles the creation of SpacetimeDB clients specifically
    for C#/.NET-based server implementations. It handles the unique aspects
    of .NET project structures and configurations.
    """
    
    @property
    def server_language(self) -> str:
        """Get the server language this factory supports.
        
        Returns:
            str: 'csharp'
        """
        return "csharp"
    
    def _get_server_path(self) -> Path:
        """Get the path to the C# server implementation.
        
        Returns:
            Path: Path to the C# server directory
            
        Raises:
            BlackholioConfigurationError: If server path doesn't exist
        """
        # Check multiple possible locations for the C# server
        possible_paths = [
            Path.home() / "git" / "Blackholio" / "server-csharp",
            Path.home() / "git" / "blackholio" / "server-csharp",
            Path("/Users/punk1290/git/Blackholio/server-csharp"),
            Path.cwd() / "server-csharp",
            Path.home() / "git" / "Blackholio" / "server-dotnet",
            Path.cwd() / "server-dotnet",
        ]
        
        # Check if a custom path is configured
        custom_path = self.config.get("csharp_server_path")
        if custom_path:
            possible_paths.insert(0, Path(custom_path))
        
        # Find the first existing path
        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found C# server at: {path}")
                return path
        
        # No path found
        paths_str = "\n  ".join(str(p) for p in possible_paths)
        raise BlackholioConfigurationError(
            f"Cannot find C# server implementation. Searched:\n  {paths_str}"
        )
    
    def validate_configuration(self) -> bool:
        """Validate the C# factory configuration.
        
        This extends the base validation with C#-specific checks.
        
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
                logger.error(f"C# server path does not exist: {server_path}")
                return False
            
            # Check for C# project files
            csharp_indicators = [
                "*.csproj",
                "*.sln",
                "Program.cs",
                "global.json",
                "Directory.Build.props",
            ]
            
            found_indicator = False
            for pattern in csharp_indicators:
                if pattern.startswith("*"):
                    # Handle glob patterns
                    if list(server_path.glob(pattern)):
                        found_indicator = True
                        break
                else:
                    # Handle exact file names
                    if (server_path / pattern).exists():
                        found_indicator = True
                        break
            
            if not found_indicator:
                logger.error(
                    f"No C# project indicators found at: {server_path}"
                )
                return False
            
            # Check for common C# source directories
            source_dirs = ["src", "Source", "BlackholioServer", "Server"]
            found_source = False
            for src_dir in source_dirs:
                if (server_path / src_dir).exists():
                    found_source = True
                    break
            
            # Also check if .cs files exist in root
            if not found_source and list(server_path.glob("*.cs")):
                found_source = True
            
            if not found_source:
                logger.error(f"No C# source files found at: {server_path}")
                return False
            
            logger.info("C# factory configuration validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"C# factory validation failed: {e}")
            return False
    
    def create_connection(
        self,
        identity: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> SpacetimeDBConnection:
        """Create a SpacetimeDB connection for a C# server.
        
        This method extends the base implementation with C#-specific
        configuration and optimizations.
        
        Args:
            identity: Optional identity token
            credentials: Optional credentials dictionary
            **kwargs: Additional connection parameters
            
        Returns:
            SpacetimeDBConnection: Configured connection for C# server
        """
        # Add C#-specific defaults
        csharp_defaults = {
            "protocol_version": "v1.1.2",
            "compression": True,  # C# servers typically support compression
            "binary_protocol": True,  # C# works efficiently with binary
            "serialization": "msgpack",  # C# often uses MessagePack
            "strict_typing": True,  # C# has strong typing
            "nullable_reference_types": True,  # Modern C# feature
        }
        
        # Merge with provided kwargs
        csharp_defaults.update(kwargs)
        
        # Create connection using base implementation
        connection = super().create_connection(
            identity=identity,
            credentials=credentials,
            **csharp_defaults
        )
        
        logger.info("Created C# server connection")
        return connection
    
    @property
    def is_available(self) -> bool:
        """Check if the C# factory is available.
        
        Returns:
            bool: True if C# server and dependencies are available
        """
        try:
            # Check base availability
            if not super().is_available:
                return False
            
            # Additional C#-specific checks
            server_path = self._get_server_path()
            
            # Check for build output directories
            build_dirs = ["bin", "obj"]
            has_build_output = any(
                (server_path / build_dir).exists() for build_dir in build_dirs
            )
            
            if has_build_output:
                logger.debug("C# server has build output")
                
                # Check for compiled assemblies
                bin_path = server_path / "bin"
                if bin_path.exists():
                    # Look for Debug or Release builds
                    for config in ["Debug", "Release"]:
                        config_path = bin_path / config
                        if config_path.exists():
                            # Check for .dll or .exe files
                            dlls = list(config_path.glob("*.dll"))
                            exes = list(config_path.glob("*.exe"))
                            if dlls or exes:
                                logger.debug(
                                    f"Found compiled C# assemblies in {config}"
                                )
                                return True
            
            # Check for .NET SDK indicators
            dotnet_files = ["global.json", "nuget.config", ".config/dotnet-tools.json"]
            has_dotnet = any(
                (server_path / file).exists() for file in dotnet_files
            )
            
            if has_dotnet:
                logger.debug("C# server has .NET configuration")
            
            # C# server is available if project files exist
            # Can be compiled on demand
            return True
            
        except Exception as e:
            logger.debug(f"C# factory availability check failed: {e}")
            return False