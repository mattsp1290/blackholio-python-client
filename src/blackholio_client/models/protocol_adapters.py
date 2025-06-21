"""
Protocol Adapters - Multi-Language Server Protocol Support

Provides protocol adapters for handling different SpacetimeDB server
language implementations with their specific data formats, naming
conventions, and protocol variations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Type, Callable
from enum import Enum
from dataclasses import asdict, is_dataclass
import re
import json

from .game_entities import GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState
from .serialization import ServerLanguage, SerializationFormat

logger = logging.getLogger(__name__)


class ProtocolVersion(Enum):
    """Supported SpacetimeDB protocol versions."""
    V1_0 = "1.0"
    V1_1 = "1.1" 
    V1_2 = "1.2"
    V2_0 = "2.0"


class FieldMapping:
    """
    Field mapping configuration for protocol adaptation.
    
    Maps field names between client and server representations
    for different server language conventions.
    """
    
    def __init__(self, client_to_server: Optional[Dict[str, str]] = None,
                 server_to_client: Optional[Dict[str, str]] = None):
        """
        Initialize field mapping.
        
        Args:
            client_to_server: Mapping from client field names to server field names
            server_to_client: Mapping from server field names to client field names
        """
        self.client_to_server = client_to_server or {}
        self.server_to_client = server_to_client or {}
    
    def map_to_server(self, field_name: str) -> str:
        """Map client field name to server field name."""
        return self.client_to_server.get(field_name, field_name)
    
    def map_to_client(self, field_name: str) -> str:
        """Map server field name to client field name."""
        return self.server_to_client.get(field_name, field_name)


class ProtocolAdapter(ABC):
    """
    Abstract base class for server language protocol adapters.
    
    Handles the conversion between client data models and server-specific
    protocol formats for different SpacetimeDB server implementations.
    """
    
    def __init__(self, server_language: ServerLanguage, 
                 protocol_version: ProtocolVersion = ProtocolVersion.V1_2):
        """
        Initialize protocol adapter.
        
        Args:
            server_language: Target server language
            protocol_version: SpacetimeDB protocol version
        """
        self.server_language = server_language
        self.protocol_version = protocol_version
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Field mappings for different object types
        self.field_mappings: Dict[str, FieldMapping] = {}
        self._initialize_field_mappings()
    
    @abstractmethod
    def _initialize_field_mappings(self):
        """Initialize field mappings for this server language."""
        pass
    
    @abstractmethod
    def adapt_to_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """
        Adapt client data to server protocol format.
        
        Args:
            data: Client data dictionary
            object_type: Type of object being adapted
            
        Returns:
            Server-formatted data dictionary
        """
        pass
    
    @abstractmethod
    def adapt_from_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """
        Adapt server data to client format.
        
        Args:
            data: Server data dictionary
            object_type: Type of object being adapted
            
        Returns:
            Client-formatted data dictionary
        """
        pass
    
    def _apply_field_mapping(self, data: Dict[str, Any], mapping: FieldMapping, 
                           direction: str) -> Dict[str, Any]:
        """
        Apply field mapping to data.
        
        Args:
            data: Data to transform
            mapping: Field mapping configuration
            direction: 'to_server' or 'to_client'
            
        Returns:
            Transformed data
        """
        result = {}
        
        for key, value in data.items():
            if direction == 'to_server':
                new_key = mapping.map_to_server(key)
            else:
                new_key = mapping.map_to_client(key)
            
            # Recursively handle nested dictionaries
            if isinstance(value, dict):
                result[new_key] = self._apply_field_mapping(value, mapping, direction)
            elif isinstance(value, list):
                result[new_key] = [
                    self._apply_field_mapping(item, mapping, direction) 
                    if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                result[new_key] = value
        
        return result
    
    def _convert_naming_convention(self, text: str, target_convention: str) -> str:
        """
        Convert text to target naming convention.
        
        Args:
            text: Text to convert
            target_convention: Target convention ('snake_case', 'camelCase', 'PascalCase')
            
        Returns:
            Converted text
        """
        if target_convention == 'snake_case':
            return self._to_snake_case(text)
        elif target_convention == 'camelCase':
            return self._to_camel_case(text)
        elif target_convention == 'PascalCase':
            return self._to_pascal_case(text)
        else:
            return text
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_camel_case(self, text: str) -> str:
        """Convert snake_case to camelCase."""
        components = text.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def _to_pascal_case(self, text: str) -> str:
        """Convert snake_case to PascalCase."""
        components = text.split('_')
        return ''.join(word.capitalize() for word in components if word)


class RustProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for Rust SpacetimeDB servers.
    
    Handles Rust-specific naming conventions (snake_case),
    data types, and protocol specifics.
    """
    
    def _initialize_field_mappings(self):
        """Initialize Rust-specific field mappings."""
        # Rust uses snake_case and has specific field names
        entity_mapping = FieldMapping(
            client_to_server={
                'entity_id': 'id',
                'created_at': 'created',
                'updated_at': 'updated'
            },
            server_to_client={
                'id': 'entity_id',
                'created': 'created_at',
                'updated': 'updated_at'
            }
        )
        
        player_mapping = FieldMapping(
            client_to_server={
                'player_id': 'id',
                'entity_id': 'entity_id',
                'input_direction': 'input',
                'max_speed': 'max_vel',
                'acceleration': 'accel'
            },
            server_to_client={
                'id': 'player_id',
                'input': 'input_direction',
                'max_vel': 'max_speed',
                'accel': 'acceleration'
            }
        )
        
        circle_mapping = FieldMapping(
            client_to_server={
                'circle_id': 'id',
                'circle_type': 'type',
                'respawn_time': 'respawn'
            },
            server_to_client={
                'id': 'circle_id',
                'type': 'circle_type',
                'respawn': 'respawn_time'
            }
        )
        
        self.field_mappings = {
            'GameEntity': entity_mapping,
            'GamePlayer': player_mapping,
            'GameCircle': circle_mapping,
            'Vector2': FieldMapping()  # No mapping needed for Vector2
        }
    
    def adapt_to_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt client data to Rust server format."""
        # Apply field mappings
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_server')
        
        # Convert all field names to snake_case
        adapted_data = self._convert_all_keys(adapted_data, 'snake_case')
        
        # Handle Rust-specific enum values (lowercase)
        if 'entity_type' in adapted_data:
            adapted_data['entity_type'] = str(adapted_data['entity_type']).lower()
        if 'state' in adapted_data:
            adapted_data['state'] = str(adapted_data['state']).lower()
        
        # Handle timestamp format (Rust uses u64 nanoseconds)
        for time_field in ['created_at', 'updated_at', 'created', 'updated']:
            if time_field in adapted_data and adapted_data[time_field] is not None:
                adapted_data[time_field] = int(adapted_data[time_field] * 1_000_000_000)
        
        return adapted_data
    
    def adapt_from_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt Rust server data to client format."""
        # Handle timestamp format (convert from nanoseconds to seconds)
        for time_field in ['created', 'updated', 'created_at', 'updated_at']:
            if time_field in data and data[time_field] is not None:
                data[time_field] = data[time_field] / 1_000_000_000
        
        # Apply field mappings
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_client')
        
        return adapted_data
    
    def _convert_all_keys(self, data: Dict[str, Any], convention: str) -> Dict[str, Any]:
        """Convert all keys in dictionary to target convention."""
        result = {}
        
        for key, value in data.items():
            new_key = self._convert_naming_convention(key, convention)
            
            if isinstance(value, dict):
                result[new_key] = self._convert_all_keys(value, convention)
            elif isinstance(value, list):
                result[new_key] = [
                    self._convert_all_keys(item, convention) 
                    if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                result[new_key] = value
        
        return result


class PythonProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for Python SpacetimeDB servers.
    
    Handles Python-specific conventions and data types.
    """
    
    def _initialize_field_mappings(self):
        """Initialize Python-specific field mappings."""
        # Python uses snake_case natively, minimal mapping needed
        self.field_mappings = {
            'GameEntity': FieldMapping(),
            'GamePlayer': FieldMapping(),
            'GameCircle': FieldMapping(),
            'Vector2': FieldMapping()
        }
    
    def adapt_to_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt client data to Python server format."""
        # Python server expects the same format as client, minimal adaptation
        adapted_data = data.copy()
        
        # Handle timestamp format (Python uses float seconds)
        for time_field in ['created_at', 'updated_at']:
            if time_field in adapted_data and adapted_data[time_field] is not None:
                adapted_data[time_field] = float(adapted_data[time_field])
        
        return adapted_data
    
    def adapt_from_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt Python server data to client format."""
        # Python server returns data in same format as expected by client
        return data.copy()


class CSharpProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for C# SpacetimeDB servers.
    
    Handles C#-specific naming conventions (PascalCase),
    data types, and .NET specifics.
    """
    
    def _initialize_field_mappings(self):
        """Initialize C#-specific field mappings."""
        # C# uses PascalCase for properties
        entity_mapping = FieldMapping(
            client_to_server={
                'entity_id': 'EntityId',
                'created_at': 'CreatedAt',
                'updated_at': 'UpdatedAt',
                'is_active': 'IsActive',
                'entity_type': 'EntityType'
            },
            server_to_client={
                'EntityId': 'entity_id',
                'CreatedAt': 'created_at',
                'UpdatedAt': 'updated_at',
                'IsActive': 'is_active',
                'EntityType': 'entity_type'
            }
        )
        
        player_mapping = FieldMapping(
            client_to_server={
                'player_id': 'PlayerId',
                'entity_id': 'EntityId',
                'input_direction': 'InputDirection',
                'max_speed': 'MaxSpeed'
            },
            server_to_client={
                'PlayerId': 'player_id',
                'EntityId': 'entity_id',
                'InputDirection': 'input_direction',
                'MaxSpeed': 'max_speed'
            }
        )
        
        circle_mapping = FieldMapping(
            client_to_server={
                'circle_id': 'CircleId',
                'circle_type': 'CircleType',
                'respawn_time': 'RespawnTime'
            },
            server_to_client={
                'CircleId': 'circle_id',
                'CircleType': 'circle_type',
                'RespawnTime': 'respawn_time'
            }
        )
        
        self.field_mappings = {
            'GameEntity': entity_mapping,
            'GamePlayer': player_mapping,
            'GameCircle': circle_mapping,
            'Vector2': FieldMapping(
                client_to_server={'x': 'X', 'y': 'Y'},
                server_to_client={'X': 'x', 'Y': 'y'}
            )
        }
    
    def adapt_to_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt client data to C# server format."""
        # Apply field mappings first
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_server')
        
        # Convert all remaining fields to PascalCase
        final_data = {}
        for key, value in adapted_data.items():
            pascal_key = self._to_pascal_case(key)
            final_data[pascal_key] = value
        
        # Handle C#-specific enum format (PascalCase)
        if 'EntityType' in final_data:
            final_data['EntityType'] = str(final_data['EntityType']).title()
        if 'State' in final_data:
            final_data['State'] = str(final_data['State']).title()
        
        # Handle timestamp format (C# uses DateTime ticks or milliseconds)
        for time_field in ['CreatedAt', 'UpdatedAt']:
            if time_field in final_data and final_data[time_field] is not None:
                final_data[time_field] = int(final_data[time_field] * 1000)  # Convert to milliseconds
        
        return final_data
    
    def adapt_from_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt C# server data to client format."""
        # Handle timestamp format (convert from milliseconds to seconds)
        for time_field in ['CreatedAt', 'UpdatedAt']:
            if time_field in data and data[time_field] is not None:
                data[time_field] = data[time_field] / 1000
        
        # Apply field mappings
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_client')
        
        return adapted_data
    
    def _convert_all_keys(self, data: Dict[str, Any], convention: str) -> Dict[str, Any]:
        """Convert all keys in dictionary to target convention."""
        result = {}
        
        for key, value in data.items():
            new_key = self._convert_naming_convention(key, convention)
            
            if isinstance(value, dict):
                result[new_key] = self._convert_all_keys(value, convention)
            elif isinstance(value, list):
                result[new_key] = [
                    self._convert_all_keys(item, convention) 
                    if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                result[new_key] = value
        
        return result


class GoProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for Go SpacetimeDB servers.
    
    Handles Go-specific naming conventions and data types.
    """
    
    def _initialize_field_mappings(self):
        """Initialize Go-specific field mappings."""
        # Go typically uses camelCase for JSON tags
        entity_mapping = FieldMapping(
            client_to_server={
                'entity_id': 'entityID',
                'created_at': 'createdAt',
                'updated_at': 'updatedAt',
                'is_active': 'isActive',
                'entity_type': 'entityType'
            },
            server_to_client={
                'entityID': 'entity_id',
                'createdAt': 'created_at',
                'updatedAt': 'updated_at',
                'isActive': 'is_active',
                'entityType': 'entity_type'
            }
        )
        
        player_mapping = FieldMapping(
            client_to_server={
                'player_id': 'playerID',
                'entity_id': 'entityID',
                'input_direction': 'inputDirection',
                'max_speed': 'maxSpeed',
                'created_at': 'createdAt',
                'updated_at': 'updatedAt',
                'is_active': 'isActive'
            },
            server_to_client={
                'playerID': 'player_id',
                'entityID': 'entity_id',
                'inputDirection': 'input_direction',
                'maxSpeed': 'max_speed',
                'createdAt': 'created_at',
                'updatedAt': 'updated_at',
                'isActive': 'is_active'
            }
        )
        
        circle_mapping = FieldMapping(
            client_to_server={
                'circle_id': 'circleID',
                'circle_type': 'circleType',
                'respawn_time': 'respawnTime'
            },
            server_to_client={
                'circleID': 'circle_id',
                'circleType': 'circle_type',
                'respawnTime': 'respawn_time'
            }
        )
        
        self.field_mappings = {
            'GameEntity': entity_mapping,
            'GamePlayer': player_mapping,
            'GameCircle': circle_mapping,
            'Vector2': FieldMapping()  # Go uses lowercase x, y for Vector2
        }
    
    def adapt_to_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt client data to Go server format."""
        # Apply field mappings
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_server')
        
        # Handle timestamp format (Go uses int64 nanoseconds or RFC3339)
        for time_field in ['createdAt', 'updatedAt']:
            if time_field in adapted_data and adapted_data[time_field] is not None:
                adapted_data[time_field] = int(adapted_data[time_field] * 1_000_000_000)
        
        return adapted_data
    
    def adapt_from_server(self, data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
        """Adapt Go server data to client format."""
        # Handle timestamp format (convert from nanoseconds to seconds)
        for time_field in ['createdAt', 'updatedAt']:
            if time_field in data and data[time_field] is not None:
                data[time_field] = data[time_field] / 1_000_000_000
        
        # Apply field mappings
        mapping = self.field_mappings.get(object_type, FieldMapping())
        adapted_data = self._apply_field_mapping(data, mapping, 'to_client')
        
        return adapted_data


class ProtocolAdapterRegistry:
    """
    Registry for managing protocol adapters.
    
    Provides centralized access to protocol adapters for
    different server languages and versions.
    """
    
    def __init__(self):
        """Initialize protocol adapter registry."""
        self._adapters: Dict[tuple, ProtocolAdapter] = {}
        self._register_default_adapters()
    
    def _register_default_adapters(self):
        """Register default protocol adapters."""
        for version in ProtocolVersion:
            self._adapters[(ServerLanguage.RUST, version)] = RustProtocolAdapter(
                ServerLanguage.RUST, version
            )
            self._adapters[(ServerLanguage.PYTHON, version)] = PythonProtocolAdapter(
                ServerLanguage.PYTHON, version
            )
            self._adapters[(ServerLanguage.CSHARP, version)] = CSharpProtocolAdapter(
                ServerLanguage.CSHARP, version
            )
            self._adapters[(ServerLanguage.GO, version)] = GoProtocolAdapter(
                ServerLanguage.GO, version
            )
    
    def get_adapter(self, server_language: ServerLanguage, 
                   protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> ProtocolAdapter:
        """
        Get protocol adapter for server language and version.
        
        Args:
            server_language: Target server language
            protocol_version: Protocol version
            
        Returns:
            Appropriate protocol adapter
        """
        key = (server_language, protocol_version)
        return self._adapters.get(key, self._adapters[(ServerLanguage.RUST, ProtocolVersion.V1_2)])
    
    def register_adapter(self, server_language: ServerLanguage, 
                        protocol_version: ProtocolVersion,
                        adapter: ProtocolAdapter):
        """
        Register custom protocol adapter.
        
        Args:
            server_language: Server language
            protocol_version: Protocol version
            adapter: Protocol adapter instance
        """
        key = (server_language, protocol_version)
        self._adapters[key] = adapter
    
    def adapt_to_server(self, data: Dict[str, Any], object_type: str,
                       server_language: ServerLanguage,
                       protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> Dict[str, Any]:
        """
        Adapt data to server format using appropriate adapter.
        
        Args:
            data: Data to adapt
            object_type: Type of object
            server_language: Target server language
            protocol_version: Protocol version
            
        Returns:
            Server-adapted data
        """
        adapter = self.get_adapter(server_language, protocol_version)
        return adapter.adapt_to_server(data, object_type)
    
    def adapt_from_server(self, data: Dict[str, Any], object_type: str,
                         server_language: ServerLanguage,
                         protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> Dict[str, Any]:
        """
        Adapt data from server format using appropriate adapter.
        
        Args:
            data: Server data to adapt
            object_type: Type of object
            server_language: Source server language
            protocol_version: Protocol version
            
        Returns:
            Client-adapted data
        """
        adapter = self.get_adapter(server_language, protocol_version)
        return adapter.adapt_from_server(data, object_type)


# Global protocol adapter registry
_protocol_registry = ProtocolAdapterRegistry()


# Convenience functions
def adapt_to_server(data: Dict[str, Any], object_type: str,
                   server_language: ServerLanguage,
                   protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> Dict[str, Any]:
    """Adapt data to server format using global registry."""
    return _protocol_registry.adapt_to_server(data, object_type, server_language, protocol_version)


def adapt_from_server(data: Dict[str, Any], object_type: str,
                     server_language: ServerLanguage,
                     protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> Dict[str, Any]:
    """Adapt data from server format using global registry."""
    return _protocol_registry.adapt_from_server(data, object_type, server_language, protocol_version)


def get_protocol_adapter(server_language: ServerLanguage,
                        protocol_version: ProtocolVersion = ProtocolVersion.V1_2) -> ProtocolAdapter:
    """Get protocol adapter from global registry."""
    return _protocol_registry.get_adapter(server_language, protocol_version)


def register_custom_adapter(server_language: ServerLanguage,
                           protocol_version: ProtocolVersion,
                           adapter: ProtocolAdapter):
    """Register custom protocol adapter with global registry."""
    _protocol_registry.register_adapter(server_language, protocol_version, adapter)