"""
Server Configuration - Multi-language SpacetimeDB Server Support

Handles configuration for different SpacetimeDB server implementations
(Rust, Python, C#, Go) with environment variable support.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional


# Server language configuration profiles
SERVER_CONFIGS = {
    'rust': {
        'default_port': 3000,
        'db_identity': 'blackholio',
        'protocol': 'v1.json.spacetimedb',
        'description': 'Rust SpacetimeDB server implementation'
    },
    'python': {
        'default_port': 3001,
        'db_identity': 'blackholio',
        'protocol': 'v1.json.spacetimedb',
        'description': 'Python SpacetimeDB server implementation'
    },
    'csharp': {
        'default_port': 3002,
        'db_identity': 'blackholio',
        'protocol': 'v1.json.spacetimedb',
        'description': 'C# SpacetimeDB server implementation'
    },
    'go': {
        'default_port': 3003,
        'db_identity': 'blackholio',
        'protocol': 'v1.json.spacetimedb',
        'description': 'Go SpacetimeDB server implementation'
    }
}


@dataclass
class ServerConfig:
    """
    Configuration for SpacetimeDB server connection.
    
    Consolidates server configuration logic from both existing projects
    with support for environment variable overrides.
    """
    language: str
    host: str
    port: int
    db_identity: str
    protocol: str
    use_ssl: bool = False
    
    @classmethod
    def from_environment(cls, server_language: Optional[str] = None) -> 'ServerConfig':
        """
        Create server configuration from environment variables.
        
        Environment Variables:
            SERVER_LANGUAGE: rust|python|csharp|go (default: rust)
            SERVER_IP: Server IP address (default: localhost)
            SERVER_PORT: Server port (default: language-specific)
            SPACETIME_DB_IDENTITY: Database identity (default: language-specific)
            SPACETIME_PROTOCOL: Protocol version (default: v1.json.spacetimedb)
            SPACETIME_USE_SSL: Use SSL/TLS (default: false)
        
        Args:
            server_language: Override for SERVER_LANGUAGE env var
            
        Returns:
            ServerConfig instance
        """
        # Determine server language
        language = server_language or os.environ.get('SERVER_LANGUAGE', 'rust')
        
        if language not in SERVER_CONFIGS:
            raise ValueError(f"Unsupported server language: {language}. "
                           f"Supported: {list(SERVER_CONFIGS.keys())}")
        
        # Get language-specific defaults
        lang_config = SERVER_CONFIGS[language]
        
        # Build configuration with environment overrides
        server_ip = os.environ.get('SERVER_IP', 'localhost')
        server_port = int(os.environ.get('SERVER_PORT', lang_config['default_port']))
        host = f"{server_ip}:{server_port}"
        
        db_identity = os.environ.get('SPACETIME_DB_IDENTITY', lang_config['db_identity'])
        protocol = os.environ.get('SPACETIME_PROTOCOL', lang_config['protocol'])
        use_ssl = os.environ.get('SPACETIME_USE_SSL', 'false').lower() in ('true', '1', 'yes')
        
        return cls(
            language=language,
            host=host,
            port=server_port,
            db_identity=db_identity,
            protocol=protocol,
            use_ssl=use_ssl
        )
    
    @classmethod
    def for_language(cls, language: str, **overrides) -> 'ServerConfig':
        """
        Create configuration for specific server language.
        
        Args:
            language: Server language (rust, python, csharp, go)
            **overrides: Configuration overrides
            
        Returns:
            ServerConfig instance
        """
        if language not in SERVER_CONFIGS:
            raise ValueError(f"Unsupported server language: {language}")
        
        lang_config = SERVER_CONFIGS[language]
        
        # Default configuration
        config_data = {
            'language': language,
            'host': f"localhost:{lang_config['default_port']}",
            'port': lang_config['default_port'],
            'db_identity': lang_config['db_identity'],
            'protocol': lang_config['protocol'],
            'use_ssl': False
        }
        
        # Apply overrides
        config_data.update(overrides)
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'language': self.language,
            'host': self.host,
            'port': self.port,
            'db_identity': self.db_identity,
            'protocol': self.protocol,
            'use_ssl': self.use_ssl
        }
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for this configuration."""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}/v1/database/{self.db_identity}/subscribe"
    
    def get_http_url(self) -> str:
        """Get HTTP URL for this configuration."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}"
    
    def validate(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.language:
            raise ValueError("Server language is required")
        
        if self.language not in SERVER_CONFIGS:
            raise ValueError(f"Unsupported server language: {self.language}")
        
        if not self.host:
            raise ValueError("Server host is required")
        
        if not self.db_identity:
            raise ValueError("Database identity is required")
        
        if not self.protocol:
            raise ValueError("Protocol is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        
        return True
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"ServerConfig(language={self.language}, host={self.host}, db_identity={self.db_identity})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ServerConfig(language='{self.language}', host='{self.host}', "
                f"port={self.port}, db_identity='{self.db_identity}', "
                f"protocol='{self.protocol}', use_ssl={self.use_ssl})")


def get_supported_languages() -> list:
    """Get list of supported server languages."""
    return list(SERVER_CONFIGS.keys())


def get_language_info(language: str) -> Dict[str, Any]:
    """
    Get information about a specific server language.
    
    Args:
        language: Server language
        
    Returns:
        Dictionary with language information
        
    Raises:
        ValueError: If language is not supported
    """
    if language not in SERVER_CONFIGS:
        raise ValueError(f"Unsupported server language: {language}")
    
    return SERVER_CONFIGS[language].copy()


def validate_server_language(language: str) -> bool:
    """
    Validate if server language is supported.
    
    Args:
        language: Server language to validate
        
    Returns:
        True if language is supported
    """
    return language in SERVER_CONFIGS
