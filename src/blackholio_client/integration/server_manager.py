"""
SpacetimeDB Server Manager

Manages server-specific operations and coordination across different
SpacetimeDB server language implementations.
"""

import os
from pathlib import Path
import subprocess
import logging
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

def _validate_command_args(args: List[str]) -> None:
    """Validate command arguments to prevent injection attacks"""
    if not args:
        raise ValueError("Command arguments cannot be empty")
    
    # Check for dangerous characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')']
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(f"All arguments must be strings, got {type(arg)}")
        for char in dangerous_chars:
            if char in arg:
                raise ValueError(f"Dangerous character '{char}' found in argument: {arg}")
    
    # Validate executable name
    if not args[0] or '..' in args[0] or '/' in args[0]:
        if args[0] not in ['spacetimedb', 'which', 'lsof']:
            raise ValueError(f"Invalid executable: {args[0]}")


from ..config.environment import EnvironmentConfig, get_environment_config
from ..connection.server_config import ServerConfig
from ..exceptions.connection_errors import BlackholioConnectionError
from .client_generator import SpacetimeDBClientGenerator
from .client_loader import ClientLoader


logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """Server status enumeration."""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServerInfo:
    """Information about a SpacetimeDB server."""
    language: str
    path: str
    status: ServerStatus
    config: ServerConfig
    port: int
    pid: Optional[int] = None
    version: Optional[str] = None
    last_check: Optional[float] = None
    error_message: Optional[str] = None


class ServerManager:
    """
    Manages SpacetimeDB server operations across multiple languages.
    
    This class provides server management capabilities including status checking,
    coordination with client generation, and server-specific configuration.
    """
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """
        Initialize the server manager.
        
        Args:
            config: Environment configuration (uses global if not provided)
        """
        self.config = config or get_environment_config()
        self.generator = SpacetimeDBClientGenerator(self.config)
        self.loader = ClientLoader(self.config)
        self._server_info_cache: Dict[str, ServerInfo] = {}
        
        logger.info(f"SpacetimeDB Server Manager initialized for server language: {self.config.server_language}")
    
    def get_server_info(self, 
                       server_language: Optional[str] = None,
                       refresh: bool = False) -> ServerInfo:
        """
        Get information about a SpacetimeDB server.
        
        Args:
            server_language: Server language (uses config default if not provided)
            refresh: Force refresh of server information
            
        Returns:
            ServerInfo instance
            
        Raises:
            BlackholioConnectionError: If server information cannot be retrieved
        """
        language = server_language or self.config.server_language
        
        # Return cached info if available and not refreshing
        if not refresh and language in self._server_info_cache:
            return self._server_info_cache[language]
        
        try:
            # Get server path
            server_path = self.generator.get_server_path(language)
            
            # Get server configuration
            server_config = self.config.get_server_config(language)
            
            # Check server status
            status = self._check_server_status(language, server_path)
            
            # Create server info
            server_info = ServerInfo(
                language=language,
                path=server_path,
                status=status,
                config=server_config,
                port=server_config.port,
                last_check=self._get_current_timestamp()
            )
            
            # Try to get additional server details
            self._enhance_server_info(server_info)
            
            # Cache the server info
            self._server_info_cache[language] = server_info
            
            return server_info
            
        except Exception as e:
            logger.error(f"Failed to get server info for {language}: {e}")
            
            # Return error server info
            error_info = ServerInfo(
                language=language,
                path=self.generator.DEFAULT_SERVER_PATHS.get(language, ""),
                status=ServerStatus.ERROR,
                config=self.config.get_server_config(language),
                port=self.config.server_port,
                error_message=str(e),
                last_check=self._get_current_timestamp()
            )
            
            self._server_info_cache[language] = error_info
            return error_info
    
    def _check_server_status(self, language: str, server_path: str) -> ServerStatus:
        """
        Check the status of a SpacetimeDB server.
        
        Args:
            language: Server language
            server_path: Path to server directory
            
        Returns:
            ServerStatus
        """
        try:
            # Check if server directory exists
            if not os.path.isdir(server_path):
                return ServerStatus.ERROR
            
            # Check if server files exist
            if not self._validate_server_files(language, server_path):
                return ServerStatus.ERROR
            
            # Check if server is running by trying to connect
            if self._is_server_running(language):
                return ServerStatus.RUNNING
            
            return ServerStatus.AVAILABLE
            
        except Exception as e:
            logger.debug(f"Error checking server status for {language}: {e}")
            return ServerStatus.UNKNOWN
    
    def _validate_server_files(self, language: str, server_path: str) -> bool:
        """
        Validate that required server files exist.
        
        Args:
            language: Server language
            server_path: Path to server directory
            
        Returns:
            True if server files are valid
        """
        required_files = {
            'rust': ['Cargo.toml', 'src'],
            'python': ['lib.py'],
            'csharp': ['StdbModule.csproj', 'Lib.cs'],
            'go': ['go.mod', 'main.go']
        }
        
        if language not in required_files:
            return False
        
        for required_file in required_files[language]:
            file_path = os.path.join(server_path, required_file)
            if not (os.path.isfile(file_path) or os.path.isdir(file_path)):
                logger.debug(f"Missing required file for {language} server: {required_file}")
                return False
        
        return True
    
    def _is_server_running(self, language: str) -> bool:
        """
        Check if a server is currently running.
        
        Args:
            language: Server language
            
        Returns:
            True if server appears to be running
        """
        try:
            server_config = self.config.get_server_config(language)
            
            # Try to connect to the server port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)  # 1 second timeout
            
            result = sock.connect_ex((self.config.server_ip, server_config.port))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False
    
    def _enhance_server_info(self, server_info: ServerInfo):
        """
        Enhance server info with additional details.
        
        Args:
            server_info: ServerInfo to enhance
        """
        try:
            # Try to get server version information
            version = self._get_server_version(server_info.language, server_info.path)
            if version:
                server_info.version = version
            
            # Try to get PID if server is running
            if server_info.status == ServerStatus.RUNNING:
                pid = self._get_server_pid(server_info.language, server_info.port)
                if pid:
                    server_info.pid = pid
                    
        except Exception as e:
            logger.debug(f"Failed to enhance server info for {server_info.language}: {e}")
    
    def _get_server_version(self, language: str, server_path: str) -> Optional[str]:
        """
        Get server version information.
        
        Args:
            language: Server language
            server_path: Path to server directory
            
        Returns:
            Version string or None if not available
        """
        try:
            if language == 'rust':
                cargo_toml = os.path.join(server_path, 'Cargo.toml')
                if os.path.isfile(cargo_toml):
                    cargo_toml = Path(cargo_toml).resolve()
                    if not str(cargo_toml).startswith(str(Path.cwd())):
                        raise ValueError(f"Path traversal detected: {cargo_toml}")
                    with open(cargo_toml, 'r') as f:
                        for line in f:
                            if line.strip().startswith('version'):
                                return line.split('=')[1].strip().strip('"')
            
            elif language == 'python':
                # Could check __version__ in lib.py or setup.py
                pass
            
            elif language == 'csharp':
                # Could check .csproj file
                pass
            
            elif language == 'go':
                # Could check go.mod
                pass
                
        except (OSError, ValueError) as e:
            logger.debug(f"Operation failed (non-critical): {e}")
            pass
        
        return None
    
    def _get_server_pid(self, language: str, port: int) -> Optional[int]:
        """
        Get the PID of a running server.
        
        Args:
            language: Server language
            port: Server port
            
        Returns:
            PID or None if not found
        """
        try:
            # Use lsof to find process using the port
            _validate_command_args(['lsof', '-ti', f':{port}'])
            result = subprocess.run(['lsof', '-ti', f':{port}'],
                                  capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
                
        except (OSError, ValueError) as e:
            logger.debug(f"Operation failed (non-critical): {e}")
            pass
        
        return None
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def get_all_server_info(self, refresh: bool = False) -> Dict[str, ServerInfo]:
        """
        Get information for all supported servers.
        
        Args:
            refresh: Force refresh of all server information
            
        Returns:
            Dictionary mapping language to ServerInfo
        """
        results = {}
        
        for language in self.generator.DEFAULT_SERVER_PATHS.keys():
            try:
                server_info = self.get_server_info(language, refresh=refresh)
                results[language] = server_info
                
            except Exception as e:
                logger.error(f"Failed to get server info for {language}: {e}")
                results[language] = ServerInfo(
                    language=language,
                    path="",
                    status=ServerStatus.ERROR,
                    config=self.config.get_server_config(language),
                    port=self.config.server_port,
                    error_message=str(e)
                )
        
        return results
    
    def validate_server_setup(self, server_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate server setup and configuration.
        
        Args:
            server_language: Server language (uses config default if not provided)
            
        Returns:
            Validation results dictionary
        """
        language = server_language or self.config.server_language
        
        try:
            server_info = self.get_server_info(language, refresh=True)
            
            validation_results = {
                'valid': server_info.status != ServerStatus.ERROR,
                'language': language,
                'server_info': {
                    'path': server_info.path,
                    'status': server_info.status.value,
                    'port': server_info.port,
                    'version': server_info.version,
                    'pid': server_info.pid
                },
                'warnings': [],
                'errors': []
            }
            
            # Add warnings and errors based on server status
            if server_info.status == ServerStatus.ERROR:
                validation_results['errors'].append(
                    server_info.error_message or f"Server error for {language}"
                )
            elif server_info.status == ServerStatus.UNKNOWN:
                validation_results['warnings'].append(
                    f"Server status unknown for {language}"
                )
            
            # Check if server directory exists
            if not os.path.isdir(server_info.path):
                validation_results['errors'].append(f"Server directory not found: {server_info.path}")
            
            # Check client generation capability
            try:
                cli_validation = self.generator.validate_spacetimedb_cli()
                if not cli_validation['valid']:
                    validation_results['errors'].append(
                        f"SpacetimeDB CLI validation failed: {cli_validation.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                validation_results['errors'].append(f"CLI validation error: {e}")
            
            return validation_results
            
        except Exception as e:
            return {
                'valid': False,
                'language': language,
                'server_info': {},
                'warnings': [],
                'errors': [str(e)]
            }
    
    def prepare_client_for_server(self, 
                                 server_language: Optional[str] = None,
                                 force_regenerate: bool = False) -> Tuple[Any, ServerInfo]:
        """
        Prepare a client for the specified server language.
        
        Args:
            server_language: Server language (uses config default if not provided)
            force_regenerate: Force client regeneration
            
        Returns:
            Tuple of (client_instance, server_info)
            
        Raises:
            BlackholioConnectionError: If client preparation fails
        """
        language = server_language or self.config.server_language
        
        # Get server information
        server_info = self.get_server_info(language, refresh=True)
        
        if server_info.status == ServerStatus.ERROR:
            raise BlackholioConnectionError(
                f"Server error for {language}: {server_info.error_message}"
            )
        
        # Generate and load client
        try:
            # Generate client if needed
            if force_regenerate or not self.generator.get_cached_client(language):
                logger.info(f"Generating client for {language} server")
                generation_result = self.generator.generate_client(language, force_regenerate=force_regenerate)
                
                if not generation_result.success:
                    raise BlackholioConnectionError(
                        f"Client generation failed for {language}: {generation_result.error_message}"
                    )
            
            # Load and create client instance
            client_instance = self.loader.create_client_instance(
                language,
                server_config=server_info.config,
                environment_config=self.config
            )
            
            return client_instance, server_info
            
        except Exception as e:
            logger.error(f"Failed to prepare client for {language}: {e}")
            raise BlackholioConnectionError(f"Client preparation failed: {e}")
    
    def get_connection_details(self, server_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection details for a server language.
        
        Args:
            server_language: Server language (uses config default if not provided)
            
        Returns:
            Dictionary with connection details
        """
        language = server_language or self.config.server_language
        server_info = self.get_server_info(language)
        
        return {
            'language': language,
            'host': self.config.server_ip,
            'port': server_info.port,
            'db_identity': server_info.config.db_identity,
            'protocol': server_info.config.protocol,
            'use_ssl': server_info.config.use_ssl,
            'connection_url': self.config.get_connection_url(),
            'http_url': self.config.get_http_url(),
            'server_status': server_info.status.value
        }
    
    def clear_cache(self):
        """Clear server information cache."""
        self._server_info_cache.clear()
        logger.info("Cleared server information cache")
    
    def print_server_status(self, server_language: Optional[str] = None):
        """
        Print server status information.
        
        Args:
            server_language: Server language (prints all if not provided)
        """
        if server_language:
            languages = [server_language]
        else:
            languages = list(self.generator.DEFAULT_SERVER_PATHS.keys())
        
        print("=== SpacetimeDB Server Status ===")
        
        for language in languages:
            try:
                server_info = self.get_server_info(language, refresh=True)
                
                print(f"\n{language.upper()} Server:")
                print(f"  Path: {server_info.path}")
                print(f"  Status: {server_info.status.value}")
                print(f"  Port: {server_info.port}")
                
                if server_info.version:
                    print(f"  Version: {server_info.version}")
                
                if server_info.pid:
                    print(f"  PID: {server_info.pid}")
                
                if server_info.error_message:
                    print(f"  Error: {server_info.error_message}")
                    
            except Exception as e:
                print(f"\n{language.upper()} Server:")
                print(f"  Error: {e}")
    
    def __str__(self) -> str:
        """String representation of the server manager."""
        return f"ServerManager(language={self.config.server_language}, cached_servers={len(self._server_info_cache)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ServerManager(config={self.config}, "
                f"cached_servers={list(self._server_info_cache.keys())})")