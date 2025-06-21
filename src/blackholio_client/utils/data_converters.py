"""
Data Converters - Utilities for Data Type Conversion and Validation

Provides utilities for converting between different data formats used in
SpacetimeDB communication, including JSON serialization, entity conversion,
and protocol message transformation.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Callable
from datetime import datetime
from dataclasses import asdict, is_dataclass
from enum import Enum

from ..models.game_entities import GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState
from ..exceptions.connection_errors import DataValidationError


logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataConverter:
    """
    Generic data converter with validation and transformation capabilities.
    
    Provides utilities for converting between different data formats with
    proper validation and error handling.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize data converter.
        
        Args:
            strict_mode: Whether to raise exceptions on conversion errors
        """
        self.strict_mode = strict_mode
        self._converters: Dict[Type, Callable] = {}
        self._validators: Dict[Type, Callable] = {}
        
        # Register default converters
        self._register_default_converters()
    
    def _register_default_converters(self):
        """Register default type converters."""
        # Vector2 conversions
        self._converters[Vector2] = self._convert_vector2
        self._validators[Vector2] = self._validate_vector2
        
        # Game entity conversions
        self._converters[GameEntity] = self._convert_game_entity
        self._converters[GamePlayer] = self._convert_game_player
        self._converters[GameCircle] = self._convert_game_circle
        
        # Enum conversions
        self._converters[EntityType] = self._convert_entity_type
        self._converters[PlayerState] = self._convert_player_state
    
    def convert(self, data: Any, target_type: Type[T]) -> Optional[T]:
        """
        Convert data to target type.
        
        Args:
            data: Data to convert
            target_type: Target type to convert to
            
        Returns:
            Converted data or None if conversion failed
            
        Raises:
            DataValidationError: If strict mode and conversion fails
        """
        try:
            # Handle None values
            if data is None:
                return None
            
            # If already correct type, return as-is
            if isinstance(data, target_type):
                return data
            
            # Check for registered converter
            if target_type in self._converters:
                return self._converters[target_type](data)
            
            # Try direct type conversion
            if hasattr(target_type, 'from_dict') and isinstance(data, dict):
                return target_type.from_dict(data)
            
            # Try constructor conversion
            try:
                return target_type(data)
            except (TypeError, ValueError):
                pass
            
            # If no conversion possible
            if self.strict_mode:
                raise DataValidationError(f"Cannot convert {type(data)} to {target_type}")
            
            logger.warning(f"Failed to convert {type(data)} to {target_type}")
            return None
            
        except Exception as e:
            if self.strict_mode:
                raise DataValidationError(f"Conversion error: {e}")
            
            logger.error(f"Conversion error: {e}")
            return None
    
    def validate(self, data: Any, data_type: Type) -> bool:
        """
        Validate data against type.
        
        Args:
            data: Data to validate
            data_type: Expected data type
            
        Returns:
            True if valid
        """
        try:
            if data_type in self._validators:
                return self._validators[data_type](data)
            
            # Basic type check
            return isinstance(data, data_type)
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def _convert_vector2(self, data: Any) -> Optional[Vector2]:
        """Convert data to Vector2."""
        if isinstance(data, Vector2):
            return data
        
        if isinstance(data, dict):
            return Vector2.from_dict(data)
        
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            return Vector2(float(data[0]), float(data[1]))
        
        return None
    
    def _validate_vector2(self, data: Any) -> bool:
        """Validate Vector2 data."""
        if isinstance(data, Vector2):
            return True
        
        if isinstance(data, dict):
            return 'x' in data and 'y' in data
        
        if isinstance(data, (list, tuple)):
            return len(data) >= 2
        
        return False
    
    def _convert_game_entity(self, data: Any) -> Optional[GameEntity]:
        """Convert data to GameEntity."""
        if isinstance(data, GameEntity):
            return data
        
        if isinstance(data, dict):
            return GameEntity.from_dict(data)
        
        return None
    
    def _convert_game_player(self, data: Any) -> Optional[GamePlayer]:
        """Convert data to GamePlayer."""
        if isinstance(data, GamePlayer):
            return data
        
        if isinstance(data, dict):
            return GamePlayer.from_dict(data)
        
        return None
    
    def _convert_game_circle(self, data: Any) -> Optional[GameCircle]:
        """Convert data to GameCircle."""
        if isinstance(data, GameCircle):
            return data
        
        if isinstance(data, dict):
            return GameCircle.from_dict(data)
        
        return None
    
    def _convert_entity_type(self, data: Any) -> Optional[EntityType]:
        """Convert data to EntityType."""
        if isinstance(data, EntityType):
            return data
        
        if isinstance(data, str):
            try:
                return EntityType(data.lower())
            except ValueError:
                return EntityType.UNKNOWN
        
        return None
    
    def _convert_player_state(self, data: Any) -> Optional[PlayerState]:
        """Convert data to PlayerState."""
        if isinstance(data, PlayerState):
            return data
        
        if isinstance(data, str):
            try:
                return PlayerState(data.lower())
            except ValueError:
                return PlayerState.ACTIVE
        
        return None


class JsonConverter:
    """
    JSON serialization and deserialization utilities.
    
    Handles conversion between Python objects and JSON with support
    for custom types and proper error handling.
    """
    
    def __init__(self, indent: Optional[int] = None, sort_keys: bool = False):
        """
        Initialize JSON converter.
        
        Args:
            indent: JSON indentation for pretty printing
            sort_keys: Whether to sort dictionary keys
        """
        self.indent = indent
        self.sort_keys = sort_keys
    
    def to_json(self, obj: Any) -> str:
        """
        Convert object to JSON string.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON string
            
        Raises:
            DataValidationError: If serialization fails
        """
        try:
            return json.dumps(
                obj,
                default=self._json_serializer,
                indent=self.indent,
                sort_keys=self.sort_keys,
                ensure_ascii=False
            )
        except Exception as e:
            raise DataValidationError(f"JSON serialization failed: {e}")
    
    def from_json(self, json_str: str) -> Any:
        """
        Parse JSON string to object.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            Parsed object
            
        Raises:
            DataValidationError: If parsing fails
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            raise DataValidationError(f"JSON parsing failed: {e}")
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        # Handle dataclasses
        if is_dataclass(obj):
            return asdict(obj)
        
        # Handle Vector2
        if isinstance(obj, Vector2):
            return obj.to_dict()
        
        # Handle game entities
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        
        # Handle enums
        if isinstance(obj, Enum):
            return obj.value
        
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # Handle sets
        if isinstance(obj, set):
            return list(obj)
        
        # Fallback to string representation
        return str(obj)


class MessageConverter:
    """
    SpacetimeDB message conversion utilities.
    
    Handles conversion between different message formats used in
    SpacetimeDB communication.
    """
    
    def __init__(self):
        """Initialize message converter."""
        self.data_converter = DataConverter()
        self.json_converter = JsonConverter()
    
    def protocol_to_entities(self, protocol_data: Dict[str, Any]) -> List[GameEntity]:
        """
        Convert protocol message to game entities.
        
        Args:
            protocol_data: Protocol message data
            
        Returns:
            List of game entities
        """
        entities = []
        
        try:
            # Handle different message structures
            if 'entities' in protocol_data:
                for entity_data in protocol_data['entities']:
                    entity = self._convert_to_entity(entity_data)
                    if entity:
                        entities.append(entity)
            
            elif 'table_updates' in protocol_data:
                for table_name, table_data in protocol_data['table_updates'].items():
                    if 'entity' in table_name.lower():
                        for row in table_data.get('rows', []):
                            entity = self._convert_to_entity(row)
                            if entity:
                                entities.append(entity)
            
            elif isinstance(protocol_data, list):
                # Direct list of entities
                for item in protocol_data:
                    entity = self._convert_to_entity(item)
                    if entity:
                        entities.append(entity)
            
        except Exception as e:
            logger.error(f"Error converting protocol data to entities: {e}")
        
        return entities
    
    def protocol_to_players(self, protocol_data: Dict[str, Any]) -> List[GamePlayer]:
        """
        Convert protocol message to game players.
        
        Args:
            protocol_data: Protocol message data
            
        Returns:
            List of game players
        """
        players = []
        
        try:
            # Handle different message structures
            if 'players' in protocol_data:
                for player_data in protocol_data['players']:
                    player = self.data_converter.convert(player_data, GamePlayer)
                    if player:
                        players.append(player)
            
            elif 'table_updates' in protocol_data:
                for table_name, table_data in protocol_data['table_updates'].items():
                    if 'player' in table_name.lower():
                        for row in table_data.get('rows', []):
                            player = self.data_converter.convert(row, GamePlayer)
                            if player:
                                players.append(player)
            
        except Exception as e:
            logger.error(f"Error converting protocol data to players: {e}")
        
        return players
    
    def entities_to_protocol(self, entities: List[GameEntity]) -> Dict[str, Any]:
        """
        Convert game entities to protocol message.
        
        Args:
            entities: List of game entities
            
        Returns:
            Protocol message data
        """
        return {
            'entities': [entity.to_dict() for entity in entities],
            'timestamp': time.time(),
            'count': len(entities)
        }
    
    def _convert_to_entity(self, data: Dict[str, Any]) -> Optional[GameEntity]:
        """Convert data to appropriate entity type."""
        try:
            # Determine entity type
            entity_type = data.get('entity_type', 'unknown')
            
            if entity_type == 'player' or 'player_id' in data:
                return self.data_converter.convert(data, GamePlayer)
            elif entity_type in ['circle', 'food'] or 'circle_id' in data:
                return self.data_converter.convert(data, GameCircle)
            else:
                return self.data_converter.convert(data, GameEntity)
                
        except Exception as e:
            logger.error(f"Error converting to entity: {e}")
            return None


class ValidationHelper:
    """
    Data validation utilities.
    
    Provides validation functions for common data patterns
    and formats used in the blackholio client.
    """
    
    @staticmethod
    def validate_player_name(name: str) -> bool:
        """
        Validate player name.
        
        Args:
            name: Player name to validate
            
        Returns:
            True if valid
        """
        if not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Check length
        if len(name) < 1 or len(name) > 20:
            return False
        
        # Check for invalid characters
        invalid_chars = ['<', '>', '&', '"', "'", '\n', '\r', '\t']
        if any(char in name for char in invalid_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_entity_id(entity_id: str) -> bool:
        """
        Validate entity ID format.
        
        Args:
            entity_id: Entity ID to validate
            
        Returns:
            True if valid
        """
        if not isinstance(entity_id, str):
            return False
        
        # Basic format check
        return len(entity_id) > 0 and len(entity_id) <= 64
    
    @staticmethod
    def validate_position(position: Any) -> bool:
        """
        Validate position data.
        
        Args:
            position: Position data to validate
            
        Returns:
            True if valid
        """
        if isinstance(position, Vector2):
            return True
        
        if isinstance(position, dict):
            return 'x' in position and 'y' in position
        
        if isinstance(position, (list, tuple)):
            return len(position) >= 2
        
        return False
    
    @staticmethod
    def validate_game_message(message: Dict[str, Any]) -> bool:
        """
        Validate game message format.
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid
        """
        if not isinstance(message, dict):
            return False
        
        # Check for required fields
        required_fields = ['type', 'timestamp']
        if not all(field in message for field in required_fields):
            return False
        
        # Validate timestamp
        timestamp = message.get('timestamp')
        if not isinstance(timestamp, (int, float)):
            return False
        
        return True


class TypeCoercion:
    """
    Type coercion utilities for handling loose type conversions.
    
    Provides safe type conversions with fallback values for
    handling data from external sources.
    """
    
    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value
        """
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        """
        Safely convert value to int.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Integer value
        """
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def to_bool(value: Any, default: bool = False) -> bool:
        """
        Safely convert value to bool.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return default
    
    @staticmethod
    def to_string(value: Any, default: str = "") -> str:
        """
        Safely convert value to string.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            String value
        """
        if value is None:
            return default
        
        try:
            return str(value)
        except Exception:
            return default


# Global converter instances
_global_data_converter: Optional[DataConverter] = None
_global_json_converter: Optional[JsonConverter] = None
_global_message_converter: Optional[MessageConverter] = None


def get_data_converter(strict_mode: bool = False) -> DataConverter:
    """Get global data converter instance."""
    global _global_data_converter
    if _global_data_converter is None:
        _global_data_converter = DataConverter(strict_mode)
    return _global_data_converter


def get_json_converter() -> JsonConverter:
    """Get global JSON converter instance."""
    global _global_json_converter
    if _global_json_converter is None:
        _global_json_converter = JsonConverter()
    return _global_json_converter


def get_message_converter() -> MessageConverter:
    """Get global message converter instance."""
    global _global_message_converter
    if _global_message_converter is None:
        _global_message_converter = MessageConverter()
    return _global_message_converter


# Convenience functions
def convert_to_json(obj: Any) -> str:
    """Convert object to JSON string."""
    converter = get_json_converter()
    return converter.to_json(obj)


def convert_from_json(json_str: str) -> Any:
    """Parse JSON string to object."""
    converter = get_json_converter()
    return converter.from_json(json_str)


def convert_entities(protocol_data: Dict[str, Any]) -> List[GameEntity]:
    """Convert protocol data to entities."""
    converter = get_message_converter()
    return converter.protocol_to_entities(protocol_data)


def convert_players(protocol_data: Dict[str, Any]) -> List[GamePlayer]:
    """Convert protocol data to players."""
    converter = get_message_converter()
    return converter.protocol_to_players(protocol_data)


def validate_data(data: Any, data_type: Type) -> bool:
    """Validate data against type."""
    converter = get_data_converter()
    return converter.validate(data, data_type)