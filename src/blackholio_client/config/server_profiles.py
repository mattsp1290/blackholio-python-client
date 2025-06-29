"""
Server Profiles - Predefined Server Configurations

Provides predefined server profiles for different deployment scenarios
and easy switching between server configurations.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..connection.server_config import ServerConfig, SERVER_CONFIGS


logger = logging.getLogger(__name__)


@dataclass
class ServerProfile:
    """
    Server profile with predefined configuration.
    
    Provides easy switching between different server setups
    for development, testing, and production environments.
    """
    name: str
    description: str
    server_config: ServerConfig
    environment_vars: Dict[str, str]
    tags: List[str]
    
    def apply_to_environment(self) -> Dict[str, str]:
        """
        Get environment variables for this profile.
        
        Returns:
            Dictionary of environment variables
        """
        return self.environment_vars.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'server_config': self.server_config.to_dict(),
            'environment_vars': self.environment_vars,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerProfile':
        """Create ServerProfile from dictionary."""
        server_config_data = data['server_config']
        server_config = ServerConfig(**server_config_data)
        
        return cls(
            name=data['name'],
            description=data['description'],
            server_config=server_config,
            environment_vars=data.get('environment_vars', {}),
            tags=data.get('tags', [])
        )


# Predefined server profiles
PREDEFINED_PROFILES = {
    'local-rust': ServerProfile(
        name='local-rust',
        description='Local Rust server for development',
        server_config=ServerConfig.for_language('rust', host='localhost:3000'),
        environment_vars={
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'localhost',
            'SERVER_PORT': '3000',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'DEBUG_MODE': 'true'
        },
        tags=['local', 'development', 'rust']
    ),
    
    'local-python': ServerProfile(
        name='local-python',
        description='Local Python server for development',
        server_config=ServerConfig.for_language('python', host='localhost:3001'),
        environment_vars={
            'SERVER_LANGUAGE': 'python',
            'SERVER_IP': 'localhost',
            'SERVER_PORT': '3001',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'DEBUG_MODE': 'true'
        },
        tags=['local', 'development', 'python']
    ),
    
    'local-csharp': ServerProfile(
        name='local-csharp',
        description='Local C# server for development',
        server_config=ServerConfig.for_language('csharp', host='localhost:3002'),
        environment_vars={
            'SERVER_LANGUAGE': 'csharp',
            'SERVER_IP': 'localhost',
            'SERVER_PORT': '3002',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'DEBUG_MODE': 'true'
        },
        tags=['local', 'development', 'csharp']
    ),
    
    'local-go': ServerProfile(
        name='local-go',
        description='Local Go server for development',
        server_config=ServerConfig.for_language('go', host='localhost:3003'),
        environment_vars={
            'SERVER_LANGUAGE': 'go',
            'SERVER_IP': 'localhost',
            'SERVER_PORT': '3003',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'DEBUG_MODE': 'true'
        },
        tags=['local', 'development', 'go']
    ),
    
    'docker-rust': ServerProfile(
        name='docker-rust',
        description='Dockerized Rust server',
        server_config=ServerConfig.for_language('rust', host='blackholio-rust:3000'),
        environment_vars={
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'blackholio-rust',
            'SERVER_PORT': '3000',
            'SPACETIME_DB_IDENTITY': 'blackholio'
        },
        tags=['docker', 'containerized', 'rust']
    ),
    
    'docker-python': ServerProfile(
        name='docker-python',
        description='Dockerized Python server',
        server_config=ServerConfig.for_language('python', host='blackholio-python:3001'),
        environment_vars={
            'SERVER_LANGUAGE': 'python',
            'SERVER_IP': 'blackholio-python',
            'SERVER_PORT': '3001',
            'SPACETIME_DB_IDENTITY': 'blackholio'
        },
        tags=['docker', 'containerized', 'python']
    ),
    
    'production-rust': ServerProfile(
        name='production-rust',
        description='Production Rust server with SSL',
        server_config=ServerConfig.for_language('rust', 
                                               host='blackholio.example.com:443',
                                               use_ssl=True),
        environment_vars={
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'blackholio.example.com',
            'SERVER_PORT': '443',
            'SERVER_USE_SSL': 'true',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'LOG_LEVEL': 'WARNING'
        },
        tags=['production', 'ssl', 'rust']
    ),
    
    'testing-multi': ServerProfile(
        name='testing-multi',
        description='Multi-language testing environment',
        server_config=ServerConfig.for_language('rust', host='test-server:3000'),
        environment_vars={
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'test-server',
            'SERVER_PORT': '3000',
            'SPACETIME_DB_IDENTITY': 'blackholio',
            'CONNECTION_TIMEOUT': '10.0',
            'RECONNECT_ATTEMPTS': '3',
            'LOG_LEVEL': 'DEBUG'
        },
        tags=['testing', 'ci', 'multi-language']
    )
}


def get_server_profile(profile_name: str) -> Optional[ServerProfile]:
    """
    Get server profile by name.
    
    Args:
        profile_name: Name of the profile to retrieve
        
    Returns:
        ServerProfile instance or None if not found
    """
    return PREDEFINED_PROFILES.get(profile_name)


def list_server_profiles(tags: Optional[List[str]] = None) -> List[ServerProfile]:
    """
    List available server profiles, optionally filtered by tags.
    
    Args:
        tags: Optional list of tags to filter by
        
    Returns:
        List of matching ServerProfile instances
    """
    profiles = list(PREDEFINED_PROFILES.values())
    
    if tags:
        filtered_profiles = []
        for profile in profiles:
            if any(tag in profile.tags for tag in tags):
                filtered_profiles.append(profile)
        return filtered_profiles
    
    return profiles


def get_profiles_by_language(language: str) -> List[ServerProfile]:
    """
    Get all profiles for a specific server language.
    
    Args:
        language: Server language (rust, python, csharp, go)
        
    Returns:
        List of ServerProfile instances for the language
    """
    return [profile for profile in PREDEFINED_PROFILES.values() 
            if profile.server_config.language == language]


def get_development_profiles() -> List[ServerProfile]:
    """Get all development profiles."""
    return list_server_profiles(['development'])


def get_production_profiles() -> List[ServerProfile]:
    """Get all production profiles."""
    return list_server_profiles(['production'])


def get_docker_profiles() -> List[ServerProfile]:
    """Get all Docker profiles."""
    return list_server_profiles(['docker'])


def create_custom_profile(name: str, 
                         description: str,
                         language: str,
                         host: str,
                         **kwargs) -> ServerProfile:
    """
    Create a custom server profile.
    
    Args:
        name: Profile name
        description: Profile description
        language: Server language
        host: Server host
        **kwargs: Additional ServerConfig parameters
        
    Returns:
        Custom ServerProfile instance
    """
    server_config = ServerConfig.for_language(language, host=host, **kwargs)
    
    # Build environment variables
    host_parts = host.split(':')
    server_ip = host_parts[0]
    server_port = host_parts[1] if len(host_parts) > 1 else str(SERVER_CONFIGS[language]['default_port'])
    
    environment_vars = {
        'SERVER_LANGUAGE': language,
        'SERVER_IP': server_ip,
        'SERVER_PORT': server_port,
        'SPACETIME_DB_IDENTITY': server_config.db_identity
    }
    
    if server_config.use_ssl:
        environment_vars['SERVER_USE_SSL'] = 'true'
    
    # Add any additional kwargs as environment variables
    for key, value in kwargs.items():
        env_key = key.upper()
        if env_key not in environment_vars:
            environment_vars[env_key] = str(value)
    
    return ServerProfile(
        name=name,
        description=description,
        server_config=server_config,
        environment_vars=environment_vars,
        tags=['custom', language]
    )


def register_profile(profile: ServerProfile):
    """
    Register a custom profile.
    
    Args:
        profile: ServerProfile to register
    """
    PREDEFINED_PROFILES[profile.name] = profile
    logger.info(f"Registered custom profile: {profile.name}")


def print_profile_info(profile_name: str):
    """
    Print detailed information about a server profile.
    
    Args:
        profile_name: Name of the profile to display
    """
    profile = get_server_profile(profile_name)
    
    if not profile:
        print(f"❌ Profile '{profile_name}' not found")
        return
    
    print(f"=== Server Profile: {profile.name} ===")
    print(f"Description: {profile.description}")
    print(f"Tags: {', '.join(profile.tags)}")
    print()
    
    print("Server Configuration:")
    config = profile.server_config
    print(f"  Language: {config.language}")
    print(f"  Host: {config.host}")
    print(f"  Database Identity: {config.db_identity}")
    print(f"  Protocol: {config.protocol}")
    print(f"  SSL Enabled: {config.use_ssl}")
    print()
    
    print("Environment Variables:")
    for key, value in profile.environment_vars.items():
        print(f"  {key}={value}")
    print()
    
    print(f"WebSocket URL: {config.get_websocket_url()}")
    print(f"HTTP URL: {config.get_http_url()}")


def print_all_profiles():
    """Print summary of all available profiles."""
    profiles = list_server_profiles()
    
    print("=== Available Server Profiles ===")
    print()
    
    # Group by tags
    by_tags = {}
    for profile in profiles:
        for tag in profile.tags:
            if tag not in by_tags:
                by_tags[tag] = []
            by_tags[tag].append(profile)
    
    for tag in sorted(by_tags.keys()):
        print(f"📁 {tag.upper()}:")
        for profile in by_tags[tag]:
            print(f"  • {profile.name} - {profile.description}")
            print(f"    ({profile.server_config.language} @ {profile.server_config.host})")
        print()


def validate_profile(profile: ServerProfile) -> Dict[str, Any]:
    """
    Validate a server profile.
    
    Args:
        profile: ServerProfile to validate
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'valid': True,
        'warnings': [],
        'errors': []
    }
    
    try:
        # Validate server config
        profile.server_config.validate()
        
        # Check required environment variables
        required_vars = ['SERVER_LANGUAGE', 'SERVER_IP', 'SERVER_PORT']
        for var in required_vars:
            if var not in profile.environment_vars:
                validation_results['warnings'].append(
                    f"Missing recommended environment variable: {var}"
                )
        
        # Check consistency between server config and environment vars
        if profile.environment_vars.get('SERVER_LANGUAGE') != profile.server_config.language:
            validation_results['warnings'].append(
                "SERVER_LANGUAGE environment variable doesn't match server config"
            )
        
    except Exception as e:
        validation_results['valid'] = False
        validation_results['errors'].append(str(e))
    
    return validation_results


# Profile management utilities
def export_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    """
    Export profile configuration to dictionary.
    
    Args:
        profile_name: Name of profile to export
        
    Returns:
        Profile dictionary or None if not found
    """
    profile = get_server_profile(profile_name)
    return profile.to_dict() if profile else None


def import_profile(profile_data: Dict[str, Any]) -> ServerProfile:
    """
    Import profile from dictionary.
    
    Args:
        profile_data: Profile configuration dictionary
        
    Returns:
        ServerProfile instance
    """
    return ServerProfile.from_dict(profile_data)


def get_profile_suggestions(language: Optional[str] = None, 
                          environment: Optional[str] = None) -> List[str]:
    """
    Get profile name suggestions based on criteria.
    
    Args:
        language: Preferred server language
        environment: Preferred environment (development, production, etc.)
        
    Returns:
        List of suggested profile names
    """
    suggestions = []
    
    for profile in PREDEFINED_PROFILES.values():
        score = 0
        
        if language and profile.server_config.language == language:
            score += 2
        
        if environment and environment in profile.tags:
            score += 2
        
        if score > 0:
            suggestions.append((profile.name, score))
    
    # Sort by score (highest first)
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    return [name for name, _ in suggestions]
