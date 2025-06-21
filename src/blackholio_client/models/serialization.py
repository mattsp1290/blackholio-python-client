"""
Serialization System - Multi-format Data Serialization

Provides comprehensive serialization and deserialization capabilities
for all game data models across different SpacetimeDB server languages
and protocol formats.
"""

import json
import pickle
import logging
import warnings
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import (
    Dict, Any, Optional, List, Union, Type, TypeVar, Generic,
    Protocol, runtime_checkable, get_type_hints, get_origin, get_args
)
from datetime import datetime
import base64
import struct

from .game_entities import GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    BINARY = "binary"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"


class ServerLanguage(Enum):
    """Supported SpacetimeDB server languages."""
    RUST = "rust"
    PYTHON = "python"
    CSHARP = "csharp"
    GO = "go"


@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable':
        """Create object from dictionary."""
        ...


class SerializationError(Exception):
    """Base exception for serialization errors."""
    pass


class DeserializationError(Exception):
    """Base exception for deserialization errors."""
    pass


class SchemaValidationError(Exception):
    """Exception for schema validation errors."""
    pass


class BaseSerializer(ABC, Generic[T]):
    """
    Abstract base class for all serializers.
    
    Provides common interface and functionality for different
    serialization formats and server language protocols.
    """
    
    def __init__(self, format_type: SerializationFormat, server_language: ServerLanguage = ServerLanguage.RUST):
        """
        Initialize serializer.
        
        Args:
            format_type: Serialization format to use
            server_language: Target server language for protocol compatibility
        """
        self.format_type = format_type
        self.server_language = server_language
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def serialize(self, obj: T) -> bytes:
        """
        Serialize object to bytes.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized data as bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
        """
        Deserialize bytes to object.
        
        Args:
            data: Serialized data
            target_type: Target object type
            
        Returns:
            Deserialized object
            
        Raises:
            DeserializationError: If deserialization fails
        """
        pass
    
    def validate_schema(self, obj: Any, schema: Dict[str, Any]) -> bool:
        """
        Validate object against schema.
        
        Args:
            obj: Object to validate
            schema: Schema definition
            
        Returns:
            True if validation passes
            
        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            if is_dataclass(obj):
                obj_dict = asdict(obj)
            elif hasattr(obj, 'to_dict'):
                obj_dict = obj.to_dict()
            else:
                obj_dict = obj
            
            return self._validate_dict_schema(obj_dict, schema)
        except Exception as e:
            raise SchemaValidationError(f"Schema validation failed: {e}")
    
    def _validate_dict_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate dictionary against schema."""
        required_fields = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                raise SchemaValidationError(f"Required field '{field}' missing")
        
        # Validate field types
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type and not self._validate_type(value, expected_type):
                    raise SchemaValidationError(f"Field '{field}' has invalid type")
        
        return True
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True


class JSONSerializer(BaseSerializer[T]):
    """
    JSON serializer with server language compatibility.
    
    Handles JSON serialization with specific adaptations for
    different SpacetimeDB server language expectations.
    """
    
    def __init__(self, server_language: ServerLanguage = ServerLanguage.RUST, 
                 indent: Optional[int] = None, ensure_ascii: bool = False):
        """
        Initialize JSON serializer.
        
        Args:
            server_language: Target server language
            indent: JSON indentation for pretty printing
            ensure_ascii: Whether to escape non-ASCII characters
        """
        super().__init__(SerializationFormat.JSON, server_language)
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def serialize(self, obj: T) -> str:
        """Serialize object to JSON string."""
        try:
            # Convert object to dictionary
            if is_dataclass(obj):
                data = asdict(obj)
            elif hasattr(obj, 'to_dict'):
                data = obj.to_dict()
            elif isinstance(obj, dict):
                data = obj
            else:
                data = self._convert_to_serializable(obj)
            
            # Apply server language specific transformations
            data = self._apply_server_transformations(data)
            
            # Serialize to JSON
            json_str = json.dumps(
                data,
                indent=self.indent,
                ensure_ascii=self.ensure_ascii,
                default=self._json_serializer,
                separators=(',', ':') if self.indent is None else None
            )
            
            return json_str
            
        except Exception as e:
            raise SerializationError(f"JSON serialization failed: {e}")
    
    def deserialize(self, data: Union[str, bytes], target_type: Type[T]) -> T:
        """Deserialize JSON string or bytes to object."""
        try:
            # Parse JSON
            if isinstance(data, bytes):
                json_str = data.decode('utf-8')
            else:
                json_str = data
            parsed_data = json.loads(json_str)
            
            # Apply server language specific reverse transformations
            parsed_data = self._reverse_server_transformations(parsed_data)
            
            # Convert to target type
            return self._convert_to_object(parsed_data, target_type)
            
        except Exception as e:
            raise DeserializationError(f"JSON deserialization failed: {e}")
    
    def _apply_server_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply server language specific transformations."""
        if self.server_language == ServerLanguage.RUST:
            return self._rust_transformations(data)
        elif self.server_language == ServerLanguage.PYTHON:
            return self._python_transformations(data)
        elif self.server_language == ServerLanguage.CSHARP:
            return self._csharp_transformations(data)
        elif self.server_language == ServerLanguage.GO:
            return self._go_transformations(data)
        
        return data
    
    def _reverse_server_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse server language specific transformations."""
        if self.server_language == ServerLanguage.RUST:
            return self._reverse_rust_transformations(data)
        elif self.server_language == ServerLanguage.PYTHON:
            return self._reverse_python_transformations(data)
        elif self.server_language == ServerLanguage.CSHARP:
            return self._reverse_csharp_transformations(data)
        elif self.server_language == ServerLanguage.GO:
            return self._reverse_go_transformations(data)
        
        return data
    
    def _rust_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Rust server specific transformations."""
        # Rust uses snake_case for field names
        transformed = {}
        for key, value in data.items():
            rust_key = self._to_snake_case(key)
            transformed[rust_key] = value
        
        # Rust enum variants are lowercase
        if 'entity_type' in transformed and isinstance(transformed['entity_type'], str):
            transformed['entity_type'] = transformed['entity_type'].lower()
        if 'state' in transformed and isinstance(transformed['state'], str):
            transformed['state'] = transformed['state'].lower()
        
        return transformed
    
    def _reverse_rust_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse Rust server specific transformations."""
        # Convert snake_case back to camelCase if needed
        transformed = {}
        for key, value in data.items():
            python_key = key  # Keep snake_case for Python
            transformed[python_key] = value
        
        return transformed
    
    def _python_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Python server specific transformations."""
        # Python uses snake_case natively, minimal transformation needed
        return data
    
    def _reverse_python_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse Python server specific transformations."""
        return data
    
    def _csharp_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply C# server specific transformations."""
        # C# uses PascalCase for properties
        transformed = {}
        for key, value in data.items():
            csharp_key = self._to_pascal_case(key)
            transformed[csharp_key] = value
        
        return transformed
    
    def _reverse_csharp_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse C# server specific transformations."""
        # Convert PascalCase back to snake_case
        transformed = {}
        for key, value in data.items():
            python_key = self._to_snake_case(key)
            transformed[python_key] = value
        
        return transformed
    
    def _go_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Go server specific transformations."""
        # Go uses camelCase for JSON tags typically
        transformed = {}
        for key, value in data.items():
            go_key = self._to_camel_case(key)
            transformed[go_key] = value
        
        return transformed
    
    def _reverse_go_transformations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse Go server specific transformations."""
        # Convert camelCase back to snake_case
        transformed = {}
        for key, value in data.items():
            python_key = self._to_snake_case(key)
            transformed[python_key] = value
        
        return transformed
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_camel_case(self, text: str) -> str:
        """Convert snake_case to camelCase."""
        components = text.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def _to_pascal_case(self, text: str) -> str:
        """Convert snake_case to PascalCase."""
        components = text.split('_')
        return ''.join(word.capitalize() for word in components)
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for complex objects."""
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif is_dataclass(obj):
            return asdict(obj)
        
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """Convert object to JSON serializable format."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif is_dataclass(obj):
            return asdict(obj)
        else:
            return str(obj)
    
    def _convert_to_object(self, data: Any, target_type: Type[T]) -> T:
        """Convert dictionary data to target object type."""
        if target_type in (GameEntity, GamePlayer, GameCircle):
            return target_type.from_dict(data)
        elif target_type == Vector2:
            return Vector2.from_dict(data)
        elif hasattr(target_type, 'from_dict'):
            return target_type.from_dict(data)
        else:
            # Try to create object directly
            try:
                return target_type(**data) if isinstance(data, dict) else target_type(data)
            except Exception as e:
                raise DeserializationError(f"Cannot convert to {target_type}: {e}")


class BinarySerializer(BaseSerializer[T]):
    """
    Binary serializer for efficient data transmission.
    
    Uses Python's pickle protocol with compression and
    custom handling for game objects.
    """
    
    def __init__(self, server_language: ServerLanguage = ServerLanguage.RUST, 
                 protocol_version: int = pickle.HIGHEST_PROTOCOL,
                 compress: bool = True):
        """
        Initialize binary serializer.
        
        Args:
            server_language: Target server language
            protocol_version: Pickle protocol version
            compress: Whether to compress data
        """
        super().__init__(SerializationFormat.BINARY, server_language)
        self.protocol_version = protocol_version
        self.compress = compress
    
    def serialize(self, obj: T) -> bytes:
        """Serialize object to binary bytes."""
        try:
            # Convert to dictionary first for consistency
            if hasattr(obj, 'to_dict'):
                data = obj.to_dict()
            elif is_dataclass(obj):
                data = asdict(obj)
            else:
                data = obj
            
            # Add type information for deserialization
            serializable_data = {
                'type': obj.__class__.__name__ if hasattr(obj, '__class__') else str(type(obj)),
                'data': data
            }
            
            # Serialize with pickle
            binary_data = pickle.dumps(serializable_data, protocol=self.protocol_version)
            
            # Compress if requested
            if self.compress:
                import zlib
                binary_data = zlib.compress(binary_data)
            
            return binary_data
            
        except Exception as e:
            raise SerializationError(f"Binary serialization failed: {e}")
    
    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
        """Deserialize binary bytes to object."""
        try:
            # Decompress if needed
            if self.compress:
                import zlib
                data = zlib.decompress(data)
            
            # Deserialize with pickle - WARNING: Only use with trusted data
            if data.startswith(b"PICKLE_DATA:"):
                data = data[12:]  # Remove prefix
            
            warnings.warn(
                "Binary deserialization using pickle can be unsafe with untrusted data. "
                "Consider using JSON serialization for untrusted sources.",
                SecurityWarning,
                stacklevel=2
            )
            try:
                serializable_data = pickle.loads(data)
            except (pickle.UnpicklingError, EOFError, AttributeError) as e:
                raise DeserializationError(f"Binary deserialization failed: {e}")
            
            # Extract object data
            obj_data = serializable_data.get('data', serializable_data)
            
            # Convert to target type
            if target_type in (GameEntity, GamePlayer, GameCircle):
                return target_type.from_dict(obj_data)
            elif target_type == Vector2:
                return Vector2.from_dict(obj_data)
            elif hasattr(target_type, 'from_dict'):
                return target_type.from_dict(obj_data)
            else:
                return target_type(**obj_data) if isinstance(obj_data, dict) else target_type(obj_data)
                
        except Exception as e:
            raise DeserializationError(f"Binary deserialization failed: {e}")


class SerializerRegistry:
    """
    Registry for managing different serializers.
    
    Provides centralized access to serializers for different
    formats and server languages.
    """
    
    def __init__(self):
        """Initialize serializer registry."""
        self._serializers: Dict[tuple, BaseSerializer] = {}
        self._default_format = SerializationFormat.JSON
        self._default_server = ServerLanguage.RUST
        
        # Register default serializers
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default serializers for all combinations."""
        for server_lang in ServerLanguage:
            # JSON serializers
            json_serializer = JSONSerializer(server_lang)
            self._serializers[(SerializationFormat.JSON, server_lang)] = json_serializer
            
            # Binary serializers
            binary_serializer = BinarySerializer(server_lang)
            self._serializers[(SerializationFormat.BINARY, server_lang)] = binary_serializer
    
    def get_serializer(self, format_type: Optional[SerializationFormat] = None,
                      server_language: Optional[ServerLanguage] = None) -> BaseSerializer:
        """
        Get serializer for format and server language.
        
        Args:
            format_type: Serialization format (defaults to JSON)
            server_language: Server language (defaults to Rust)
            
        Returns:
            Appropriate serializer instance
        """
        format_type = format_type or self._default_format
        server_language = server_language or self._default_server
        
        key = (format_type, server_language)
        return self._serializers.get(key, self._serializers[(self._default_format, self._default_server)])
    
    def serialize(self, obj: Any, format_type: Optional[SerializationFormat] = None,
                 server_language: Optional[ServerLanguage] = None) -> bytes:
        """
        Serialize object using appropriate serializer.
        
        Args:
            obj: Object to serialize
            format_type: Serialization format
            server_language: Target server language
            
        Returns:
            Serialized data as bytes
        """
        serializer = self.get_serializer(format_type, server_language)
        return serializer.serialize(obj)
    
    def deserialize(self, data: bytes, target_type: Type[T],
                   format_type: Optional[SerializationFormat] = None,
                   server_language: Optional[ServerLanguage] = None) -> T:
        """
        Deserialize data using appropriate serializer.
        
        Args:
            data: Serialized data
            target_type: Target object type
            format_type: Serialization format
            server_language: Source server language
            
        Returns:
            Deserialized object
        """
        serializer = self.get_serializer(format_type, server_language)
        return serializer.deserialize(data, target_type)
    
    def register_serializer(self, format_type: SerializationFormat,
                          server_language: ServerLanguage,
                          serializer: BaseSerializer):
        """
        Register custom serializer.
        
        Args:
            format_type: Serialization format
            server_language: Server language
            serializer: Serializer instance
        """
        key = (format_type, server_language)
        self._serializers[key] = serializer
    
    def list_available_formats(self) -> List[SerializationFormat]:
        """List all available serialization formats."""
        return list({key[0] for key in self._serializers.keys()})
    
    def list_supported_servers(self) -> List[ServerLanguage]:
        """List all supported server languages."""
        return list({key[1] for key in self._serializers.keys()})


# Global serializer registry instance
_serializer_registry = SerializerRegistry()


# Convenience functions for easy access
def serialize(obj: Any, format_type: Optional[SerializationFormat] = None,
             server_language: Optional[ServerLanguage] = None) -> bytes:
    """
    Serialize object using global registry.
    
    Args:
        obj: Object to serialize
        format_type: Serialization format (defaults to JSON)
        server_language: Target server language (defaults to Rust)
        
    Returns:
        Serialized data as bytes
    """
    return _serializer_registry.serialize(obj, format_type, server_language)


def deserialize(data: bytes, target_type: Type[T],
               format_type: Optional[SerializationFormat] = None,
               server_language: Optional[ServerLanguage] = None) -> T:
    """
    Deserialize data using global registry.
    
    Args:
        data: Serialized data
        target_type: Target object type
        format_type: Serialization format (defaults to JSON)
        server_language: Source server language (defaults to Rust)
        
    Returns:
        Deserialized object
    """
    return _serializer_registry.deserialize(data, target_type, format_type, server_language)


def get_serializer(format_type: Optional[SerializationFormat] = None,
                  server_language: Optional[ServerLanguage] = None) -> BaseSerializer:
    """
    Get serializer from global registry.
    
    Args:
        format_type: Serialization format (defaults to JSON)
        server_language: Server language (defaults to Rust)
        
    Returns:
        Appropriate serializer instance
    """
    return _serializer_registry.get_serializer(format_type, server_language)


def register_custom_serializer(format_type: SerializationFormat,
                              server_language: ServerLanguage,
                              serializer: BaseSerializer):
    """
    Register custom serializer with global registry.
    
    Args:
        format_type: Serialization format
        server_language: Server language
        serializer: Custom serializer implementation
    """
    _serializer_registry.register_serializer(format_type, server_language, serializer)