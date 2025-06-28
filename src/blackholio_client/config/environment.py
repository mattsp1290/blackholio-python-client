"""
Environment Configuration - Centralized Environment Variable Management

Consolidates environment variable handling from both blackholio-agent
and client-pygame into a unified configuration system.
"""

import os
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

from ..connection.server_config import ServerConfig, SERVER_CONFIGS


logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """
    Centralized environment configuration management.
    
    Consolidates environment variable patterns from both existing projects
    with validation and default value handling.
    """
    
    # Server configuration
    server_language: str = "rust"
    server_ip: str = "localhost"
    server_port: int = 3000
    server_use_ssl: bool = False
    
    # SpacetimeDB configuration
    spacetime_db_identity: Optional[str] = None
    spacetime_protocol: str = "v1.json.spacetimedb"
    
    # Connection configuration
    connection_timeout: float = 30.0
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Development configuration
    debug_mode: bool = False
    verbose_logging: bool = False
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._setup_logging()
    
    @classmethod
    def from_environment(cls) -> 'EnvironmentConfig':
        """
        Create configuration from environment variables.
        
        Environment Variables:
            SERVER_LANGUAGE: rust|python|csharp|go (default: rust)
            SERVER_IP: Server IP address (default: localhost)
            SERVER_PORT: Server port (default: language-specific)
            SERVER_USE_SSL: Use SSL/TLS (default: false)
            
            SPACETIME_DB_IDENTITY: Database identity (default: language-specific)
            SPACETIME_PROTOCOL: Protocol version (default: v1.json.spacetimedb)
            
            CONNECTION_TIMEOUT: Connection timeout in seconds (default: 30.0)
            RECONNECT_ATTEMPTS: Max reconnection attempts (default: 5)
            RECONNECT_DELAY: Delay between reconnection attempts (default: 2.0)
            
            LOG_LEVEL: Logging level (default: INFO)
            DEBUG_MODE: Enable debug mode (default: false)
            VERBOSE_LOGGING: Enable verbose logging (default: false)
        
        Returns:
            EnvironmentConfig instance
        """
        # Server configuration
        server_language = os.environ.get('SERVER_LANGUAGE', 'rust').lower()
        server_ip = os.environ.get('SERVER_IP', 'localhost')
        
        # Get default port for server language
        default_port = SERVER_CONFIGS.get(server_language, {}).get('default_port', 3000)
        server_port = int(os.environ.get('SERVER_PORT', default_port))
        
        server_use_ssl = cls._parse_bool(os.environ.get('SERVER_USE_SSL', 'false'))
        
        # SpacetimeDB configuration
        default_db_identity = SERVER_CONFIGS.get(server_language, {}).get('db_identity')
        spacetime_db_identity = os.environ.get('SPACETIME_DB_IDENTITY', default_db_identity)
        spacetime_protocol = os.environ.get('SPACETIME_PROTOCOL', 'v1.json.spacetimedb')
        
        # Connection configuration
        connection_timeout = float(os.environ.get('CONNECTION_TIMEOUT', '30.0'))
        reconnect_attempts = int(os.environ.get('RECONNECT_ATTEMPTS', '5'))
        reconnect_delay = float(os.environ.get('RECONNECT_DELAY', '2.0'))
        
        # Logging configuration
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        log_format = os.environ.get('LOG_FORMAT', 
                                   '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Development configuration
        debug_mode = cls._parse_bool(os.environ.get('DEBUG_MODE', 'false'))
        verbose_logging = cls._parse_bool(os.environ.get('VERBOSE_LOGGING', 'false'))
        
        return cls(
            server_language=server_language,
            server_ip=server_ip,
            server_port=server_port,
            server_use_ssl=server_use_ssl,
            spacetime_db_identity=spacetime_db_identity,
            spacetime_protocol=spacetime_protocol,
            connection_timeout=connection_timeout,
            reconnect_attempts=reconnect_attempts,
            reconnect_delay=reconnect_delay,
            log_level=log_level,
            log_format=log_format,
            debug_mode=debug_mode,
            verbose_logging=verbose_logging
        )
    
    def get_server_config(self, override_language: Optional[str] = None) -> ServerConfig:
        """
        Get ServerConfig instance based on environment configuration.
        
        Args:
            override_language: Override server language
            
        Returns:
            ServerConfig instance
        """
        language = override_language or self.server_language
        
        return ServerConfig(
            language=language,
            host=f"{self.server_ip}:{self.server_port}",
            port=self.server_port,
            db_identity=self.spacetime_db_identity or SERVER_CONFIGS.get(language, {}).get('db_identity', 'blackholio'),
            protocol=self.spacetime_protocol,
            use_ssl=self.server_use_ssl
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'server_language': self.server_language,
            'server_ip': self.server_ip,
            'server_port': self.server_port,
            'server_use_ssl': self.server_use_ssl,
            'spacetime_db_identity': self.spacetime_db_identity,
            'spacetime_protocol': self.spacetime_protocol,
            'connection_timeout': self.connection_timeout,
            'reconnect_attempts': self.reconnect_attempts,
            'reconnect_delay': self.reconnect_delay,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'debug_mode': self.debug_mode,
            'verbose_logging': self.verbose_logging
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """
        Update configuration from dictionary.
        
        Args:
            config_dict: Dictionary with configuration updates
        """
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self._validate_configuration()
    
    def get_connection_url(self) -> str:
        """Get full connection URL."""
        protocol = "wss" if self.server_use_ssl else "ws"
        db_identity = self.spacetime_db_identity or "blackholio"
        return f"{protocol}://{self.server_ip}:{self.server_port}/v1/database/{db_identity}/subscribe"
    
    def get_http_url(self) -> str:
        """Get HTTP URL for REST API calls."""
        protocol = "https" if self.server_use_ssl else "http"
        return f"{protocol}://{self.server_ip}:{self.server_port}"
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return self.debug_mode or self.log_level == "DEBUG"
    
    def validate(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            self._validate_configuration()
            return True
        except (ValueError, TypeError) as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key name
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return getattr(self, key, default)
    
    def _validate_configuration(self):
        """Validate configuration parameters."""
        # Validate server language
        if self.server_language not in SERVER_CONFIGS:
            logger.warning(f"Unsupported server language: {self.server_language}. "
                         f"Supported: {list(SERVER_CONFIGS.keys())}")
            self.server_language = "rust"  # Fallback to rust
        
        # Validate port range
        if not (1 <= self.server_port <= 65535):
            raise ValueError(f"Invalid server port: {self.server_port}")
        
        # Validate timeout values
        if self.connection_timeout <= 0:
            raise ValueError(f"Invalid connection timeout: {self.connection_timeout}")
        
        if self.reconnect_attempts < 0:
            raise ValueError(f"Invalid reconnect attempts: {self.reconnect_attempts}")
        
        if self.reconnect_delay < 0:
            raise ValueError(f"Invalid reconnect delay: {self.reconnect_delay}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            logger.warning(f"Invalid log level: {self.log_level}. Using INFO.")
            self.log_level = "INFO"
    
    def _setup_logging(self):
        """Setup logging configuration."""
        if self.verbose_logging or self.debug_mode:
            # Enable verbose logging for blackholio client
            logging.getLogger('blackholio_client').setLevel(logging.DEBUG)
        
        # Set root logger level
        numeric_level = getattr(logging, self.log_level, logging.INFO)
        logging.getLogger('blackholio_client').setLevel(numeric_level)
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean value from string."""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return (f"EnvironmentConfig(server={self.server_ip}:{self.server_port}, "
                f"language={self.server_language}, db_identity={self.spacetime_db_identity}, ssl={self.server_use_ssl})")
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"EnvironmentConfig({self.to_dict()})"


# Global configuration instance
_global_config: Optional[EnvironmentConfig] = None


def get_environment_config(reload: bool = False) -> EnvironmentConfig:
    """
    Get global environment configuration instance.
    
    Args:
        reload: Force reload configuration from environment
        
    Returns:
        EnvironmentConfig instance
    """
    global _global_config
    
    if _global_config is None or reload:
        _global_config = EnvironmentConfig.from_environment()
        logger.info(f"Loaded environment configuration: {_global_config}")
    
    return _global_config


def set_environment_config(config: EnvironmentConfig):
    """
    Set global environment configuration instance.
    
    Args:
        config: EnvironmentConfig instance to set as global
    """
    global _global_config
    _global_config = config
    logger.info(f"Set global environment configuration: {config}")


def reset_environment_config():
    """Reset global environment configuration (force reload on next access)."""
    global _global_config
    _global_config = None
    logger.info("Reset global environment configuration")


# Add backward compatibility methods for EnvironmentConfig class
def _add_backward_compatibility():
    """Add backward compatibility methods to EnvironmentConfig class."""
    @classmethod
    def get_instance(cls) -> 'EnvironmentConfig':
        """Get global instance (backward compatibility method)."""
        return get_environment_config()
    
    # Add the method to the class
    EnvironmentConfig.get_instance = get_instance

# Apply backward compatibility
_add_backward_compatibility()


# Legacy compatibility functions
def get_server_url() -> str:
    """Get server URL (legacy compatibility)."""
    config = get_environment_config()
    return config.get_connection_url()


def get_db_identity() -> str:
    """Get database identity (legacy compatibility)."""
    config = get_environment_config()
    return config.spacetime_db_identity or "blackholio"


def get_server_host() -> str:
    """Get server host (legacy compatibility)."""
    config = get_environment_config()
    return f"{config.server_ip}:{config.server_port}"


def is_debug_mode() -> bool:
    """Check if debug mode is enabled (legacy compatibility)."""
    config = get_environment_config()
    return config.debug_mode


# Environment variable validation helpers
def validate_environment() -> Dict[str, Any]:
    """
    Validate current environment configuration.
    
    Returns:
        Dictionary with validation results
    """
    try:
        config = get_environment_config()
        
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'config': config.to_dict()
        }
        
        # Check server language support
        if config.server_language not in SERVER_CONFIGS:
            validation_results['warnings'].append(
                f"Unsupported server language: {config.server_language}"
            )
        
        # Check database identity
        if not config.spacetime_db_identity:
            validation_results['warnings'].append(
                "No explicit database identity set, using default"
            )
        
        # Check connection parameters
        if config.connection_timeout < 5:
            validation_results['warnings'].append(
                f"Very short connection timeout: {config.connection_timeout}s"
            )
        
        if config.reconnect_attempts == 0:
            validation_results['warnings'].append(
                "Reconnection disabled (reconnect_attempts = 0)"
            )
        
        return validation_results
        
    except Exception as e:
        return {
            'valid': False,
            'warnings': [],
            'errors': [str(e)],
            'config': {}
        }


def print_environment_info():
    """Print current environment configuration information."""
    try:
        config = get_environment_config()
        validation = validate_environment()
        
        print("=== Blackholio Client Environment Configuration ===")
        print(f"Server Language: {config.server_language}")
        print(f"Server Address: {config.server_ip}:{config.server_port}")
        print(f"SSL Enabled: {config.server_use_ssl}")
        print(f"Database Identity: {config.spacetime_db_identity}")
        print(f"Protocol: {config.spacetime_protocol}")
        print(f"Connection URL: {config.get_connection_url()}")
        print(f"Debug Mode: {config.debug_mode}")
        print(f"Log Level: {config.log_level}")
        
        if validation['warnings']:
            print("\n=== Warnings ===")
            for warning in validation['warnings']:
                print(f"⚠️  {warning}")
        
        if validation['errors']:
            print("\n=== Errors ===")
            for error in validation['errors']:
                print(f"❌ {error}")
        
        if not validation['warnings'] and not validation['errors']:
            print("\n✅ Configuration is valid!")
            
    except Exception as e:
        print(f"❌ Failed to load environment configuration: {e}")
