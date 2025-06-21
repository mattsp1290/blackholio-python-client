"""
Schema Definitions and Validation

Provides JSON schema definitions and validation capabilities
for all game data models to ensure data integrity across
different SpacetimeDB server implementations.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Type, get_type_hints
from dataclasses import fields, is_dataclass
from enum import Enum

from .game_entities import GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState
from .game_statistics import PlayerStatistics, SessionStatistics

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


class SchemaManager:
    """
    Manages JSON schemas for all game data models.
    
    Provides validation capabilities and schema definitions
    for consistent data structure across server languages.
    """
    
    def __init__(self):
        """Initialize schema manager with predefined schemas."""
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._register_core_schemas()
    
    def _register_core_schemas(self):
        """Register schemas for core game objects."""
        # Vector2 schema
        self._schemas['Vector2'] = {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"}
            },
            "required": ["x", "y"],
            "additionalProperties": False
        }
        
        # GameEntity schema
        self._schemas['GameEntity'] = {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string"},
                "position": {"$ref": "#/definitions/Vector2"},
                "velocity": {"$ref": "#/definitions/Vector2"},
                "mass": {"type": "number", "minimum": 0},
                "radius": {"type": "number", "minimum": 0},
                "entity_type": {
                    "type": "string",
                    "enum": [e.value for e in EntityType]
                },
                "is_active": {"type": "boolean"},
                "created_at": {"type": ["number", "null"]},
                "updated_at": {"type": ["number", "null"]}
            },
            "required": ["entity_id"],
            "additionalProperties": False,
            "definitions": {
                "Vector2": self._schemas['Vector2']
            }
        }
        
        # GamePlayer schema (includes all GameEntity properties)
        self._schemas['GamePlayer'] = {
            "type": "object",
            "properties": {
                # GameEntity properties
                "entity_id": {"type": "string"},
                "position": {"$ref": "#/definitions/Vector2"},
                "velocity": {"$ref": "#/definitions/Vector2"},
                "mass": {"type": "number", "minimum": 0},
                "radius": {"type": "number", "minimum": 0},
                "entity_type": {
                    "type": "string",
                    "enum": [e.value for e in EntityType]
                },
                "is_active": {"type": "boolean"},
                "created_at": {"type": ["number", "null"]},
                "updated_at": {"type": ["number", "null"]},
                # GamePlayer specific properties
                "player_id": {"type": "string"},
                "name": {"type": "string"},
                "direction": {"$ref": "#/definitions/Vector2"},
                "score": {"type": "integer", "minimum": 0},
                "state": {
                    "type": "string",
                    "enum": [s.value for s in PlayerState]
                },
                "color": {"type": ["string", "null"]},
                "input_direction": {"$ref": "#/definitions/Vector2"},
                "max_speed": {"type": "number", "minimum": 0},
                "acceleration": {"type": "number", "minimum": 0}
            },
            "required": ["entity_id", "player_id"],
            "additionalProperties": False,
            "definitions": {
                "Vector2": self._schemas['Vector2']
            }
        }
        
        # GameCircle schema (includes all GameEntity properties)
        self._schemas['GameCircle'] = {
            "type": "object",
            "properties": {
                # GameEntity properties
                "entity_id": {"type": "string"},
                "position": {"$ref": "#/definitions/Vector2"},
                "velocity": {"$ref": "#/definitions/Vector2"},
                "mass": {"type": "number", "minimum": 0},
                "radius": {"type": "number", "minimum": 0},
                "entity_type": {
                    "type": "string",
                    "enum": [e.value for e in EntityType]
                },
                "is_active": {"type": "boolean"},
                "created_at": {"type": ["number", "null"]},
                "updated_at": {"type": ["number", "null"]},
                # GameCircle specific properties
                "circle_id": {"type": "string"},
                "color": {"type": ["string", "null"]},
                "circle_type": {"type": "string"},
                "value": {"type": "integer", "minimum": 0},
                "respawn_time": {"type": ["number", "null"]}
            },
            "required": ["entity_id", "circle_id"],
            "additionalProperties": False,
            "definitions": {
                "Vector2": self._schemas['Vector2']
            }
        }
        
        # PlayerStatistics schema
        self._schemas['PlayerStatistics'] = {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "games_played": {"type": "integer", "minimum": 0},
                "total_score": {"type": "integer", "minimum": 0},
                "highest_score": {"type": "integer", "minimum": 0},
                "total_playtime": {"type": "number", "minimum": 0},
                "entities_consumed": {"type": "integer", "minimum": 0},
                "times_consumed": {"type": "integer", "minimum": 0},
                "average_survival_time": {"type": "number", "minimum": 0},
                "total_distance_traveled": {"type": "number", "minimum": 0},
                "sessions_count": {"type": "integer", "minimum": 0},
                "last_played": {"type": ["number", "null"]},
                "created_at": {"type": "number"},
                "updated_at": {"type": "number"}
            },
            "required": ["player_id", "created_at", "updated_at"],
            "additionalProperties": False
        }
        
        # SessionStatistics schema
        self._schemas['SessionStatistics'] = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "start_time": {"type": "number"},
                "end_time": {"type": ["number", "null"]},
                "duration": {"type": "number", "minimum": 0},
                "players_count": {"type": "integer", "minimum": 0},
                "entities_spawned": {"type": "integer", "minimum": 0},
                "total_interactions": {"type": "integer", "minimum": 0},
                "peak_concurrent_players": {"type": "integer", "minimum": 0},
                "server_language": {"type": "string"},
                "performance_metrics": {"type": "object"},
                "error_count": {"type": "integer", "minimum": 0}
            },
            "required": ["session_id", "start_time"],
            "additionalProperties": False
        }
        
        # Batch operations schemas
        self._schemas['EntityBatch'] = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "object"}  # Simplified for now
                },
                "timestamp": {"type": "number"},
                "server_language": {"type": "string"}
            },
            "required": ["entities"]
        }
        
        self._schemas['PlayerBatch'] = {
            "type": "object",
            "properties": {
                "players": {
                    "type": "array",
                    "items": {"type": "object"}  # Simplified for now
                },
                "timestamp": {"type": "number"},
                "server_language": {"type": "string"}
            },
            "required": ["players"]
        }
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema by name.
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Schema definition or None if not found
        """
        return self._schemas.get(schema_name)
    
    def register_schema(self, schema_name: str, schema: Dict[str, Any]):
        """
        Register a custom schema.
        
        Args:
            schema_name: Name for the schema
            schema: Schema definition
        """
        self._schemas[schema_name] = schema
    
    def validate_data(self, data: Any, schema_name: str) -> bool:
        """
        Validate data against a registered schema.
        
        Args:
            data: Data to validate
            schema_name: Name of the schema to validate against
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        schema = self.get_schema(schema_name)
        if not schema:
            raise ValidationError(f"Schema '{schema_name}' not found")
        
        return self._validate_against_schema(data, schema)
    
    def validate_object(self, obj: Any) -> bool:
        """
        Validate object using its class name as schema.
        
        Args:
            obj: Object to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        schema_name = obj.__class__.__name__
        
        # Convert object to dictionary for validation
        if hasattr(obj, 'to_dict'):
            data = obj.to_dict()
        elif is_dataclass(obj):
            from dataclasses import asdict
            data = asdict(obj)
        else:
            raise ValidationError(f"Cannot validate object of type {type(obj)}")
        
        return self.validate_data(data, schema_name)
    
    def _validate_against_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """
        Validate data against a schema definition.
        
        Args:
            data: Data to validate
            schema: Schema definition
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic type validation
            schema_type = schema.get('type')
            if schema_type:
                if not self._validate_type(data, schema_type):
                    raise ValidationError(f"Data type mismatch. Expected {schema_type}, got {type(data).__name__}")
            
            # Object property validation
            if schema_type == 'object' and isinstance(data, dict):
                self._validate_object_properties(data, schema)
            
            # Array validation
            elif schema_type == 'array' and isinstance(data, list):
                self._validate_array_items(data, schema)
            
            # Enum validation
            if 'enum' in schema:
                if data not in schema['enum']:
                    raise ValidationError(f"Value '{data}' not in allowed enum values: {schema['enum']}")
            
            # Numeric constraints
            if isinstance(data, (int, float)):
                self._validate_numeric_constraints(data, schema)
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation error: {e}")
    
    def _validate_type(self, data: Any, expected_type: Union[str, List[str]]) -> bool:
        """Validate data type."""
        if isinstance(expected_type, list):
            return any(self._validate_type(data, t) for t in expected_type)
        
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(data, expected_python_type)
        
        return True
    
    def _validate_object_properties(self, data: Dict[str, Any], schema: Dict[str, Any]):
        """Validate object properties against schema."""
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        additional_properties = schema.get('additionalProperties', True)
        
        # Check required properties
        for prop in required:
            if prop not in data:
                raise ValidationError(f"Required property '{prop}' is missing")
        
        # Validate each property
        for prop, value in data.items():
            if prop in properties:
                prop_schema = properties[prop]
                
                # Handle $ref references
                if '$ref' in prop_schema:
                    ref_schema = self._resolve_reference(prop_schema['$ref'], schema)
                    if ref_schema:
                        self._validate_against_schema(value, ref_schema)
                else:
                    self._validate_against_schema(value, prop_schema)
            elif not additional_properties:
                raise ValidationError(f"Additional property '{prop}' not allowed")
    
    def _validate_array_items(self, data: List[Any], schema: Dict[str, Any]):
        """Validate array items against schema."""
        items_schema = schema.get('items')
        if not items_schema:
            return
        
        for i, item in enumerate(data):
            try:
                # Handle $ref references
                if '$ref' in items_schema:
                    ref_schema = self._resolve_reference(items_schema['$ref'], schema)
                    if ref_schema:
                        self._validate_against_schema(item, ref_schema)
                else:
                    self._validate_against_schema(item, items_schema)
            except ValidationError as e:
                raise ValidationError(f"Array item {i}: {e}")
    
    def _validate_numeric_constraints(self, data: Union[int, float], schema: Dict[str, Any]):
        """Validate numeric constraints."""
        if 'minimum' in schema and data < schema['minimum']:
            raise ValidationError(f"Value {data} is below minimum {schema['minimum']}")
        
        if 'maximum' in schema and data > schema['maximum']:
            raise ValidationError(f"Value {data} is above maximum {schema['maximum']}")
        
        if 'exclusiveMinimum' in schema and data <= schema['exclusiveMinimum']:
            raise ValidationError(f"Value {data} is not above exclusive minimum {schema['exclusiveMinimum']}")
        
        if 'exclusiveMaximum' in schema and data >= schema['exclusiveMaximum']:
            raise ValidationError(f"Value {data} is not below exclusive maximum {schema['exclusiveMaximum']}")
    
    def _resolve_reference(self, ref: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve $ref reference within schema."""
        if ref.startswith('#/definitions/'):
            definition_name = ref.replace('#/definitions/', '')
            return schema.get('definitions', {}).get(definition_name)
        elif ref.startswith('#/'):
            # Handle other local references as needed
            pass
        
        return None
    
    def list_schemas(self) -> List[str]:
        """List all registered schema names."""
        return list(self._schemas.keys())
    
    def export_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Export all schemas as dictionary."""
        return self._schemas.copy()


class DataValidator:
    """
    High-level data validator for game objects.
    
    Provides convenient validation methods for common
    game data validation scenarios.
    """
    
    def __init__(self, schema_manager: Optional[SchemaManager] = None):
        """
        Initialize data validator.
        
        Args:
            schema_manager: Schema manager instance (creates new if None)
        """
        self.schema_manager = schema_manager or SchemaManager()
    
    def validate_entity(self, entity: GameEntity) -> bool:
        """
        Validate GameEntity object.
        
        Args:
            entity: Entity to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        return self.schema_manager.validate_object(entity)
    
    def validate_player(self, player: GamePlayer) -> bool:
        """
        Validate GamePlayer object.
        
        Args:
            player: Player to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        # First validate as entity
        self.validate_entity(player)
        
        # Then validate player-specific aspects
        return self.schema_manager.validate_object(player)
    
    def validate_circle(self, circle: GameCircle) -> bool:
        """
        Validate GameCircle object.
        
        Args:
            circle: Circle to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        # First validate as entity
        self.validate_entity(circle)
        
        # Then validate circle-specific aspects
        return self.schema_manager.validate_object(circle)
    
    def validate_vector(self, vector: Vector2) -> bool:
        """
        Validate Vector2 object.
        
        Args:
            vector: Vector to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        return self.schema_manager.validate_object(vector)
    
    def validate_entity_list(self, entities: List[GameEntity]) -> bool:
        """
        Validate list of entities.
        
        Args:
            entities: List of entities to validate
            
        Returns:
            True if all valid
            
        Raises:
            ValidationError: If any validation fails
        """
        for i, entity in enumerate(entities):
            try:
                self.validate_entity(entity)
            except ValidationError as e:
                raise ValidationError(f"Entity {i} ({entity.entity_id}): {e}")
        
        return True
    
    def validate_player_list(self, players: List[GamePlayer]) -> bool:
        """
        Validate list of players.
        
        Args:
            players: List of players to validate
            
        Returns:
            True if all valid
            
        Raises:
            ValidationError: If any validation fails
        """
        for i, player in enumerate(players):
            try:
                self.validate_player(player)
            except ValidationError as e:
                raise ValidationError(f"Player {i} ({player.player_id}): {e}")
        
        return True
    
    def validate_game_state(self, entities: List[GameEntity], 
                          players: List[GamePlayer], 
                          circles: List[GameCircle]) -> bool:
        """
        Validate complete game state.
        
        Args:
            entities: All entities
            players: All players
            circles: All circles
            
        Returns:
            True if all valid
            
        Raises:
            ValidationError: If any validation fails
        """
        try:
            self.validate_entity_list(entities)
            self.validate_player_list(players)
            
            for i, circle in enumerate(circles):
                try:
                    self.validate_circle(circle)
                except ValidationError as e:
                    raise ValidationError(f"Circle {i} ({circle.circle_id}): {e}")
            
            # Cross-validation: ensure no duplicate IDs
            all_ids = [e.entity_id for e in entities]
            if len(all_ids) != len(set(all_ids)):
                raise ValidationError("Duplicate entity IDs found")
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Game state validation error: {e}")
    
    def validate_serialized_data(self, data: bytes, expected_type: Type, 
                                format_type: str = 'json') -> bool:
        """
        Validate serialized data by deserializing and validating.
        
        Args:
            data: Serialized data
            expected_type: Expected object type after deserialization
            format_type: Serialization format used
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Deserialize data
            if format_type.lower() == 'json':
                import json
                json_data = json.loads(data.decode('utf-8'))
                
                # Validate based on expected type
                if expected_type == GameEntity:
                    entity = GameEntity.from_dict(json_data)
                    return self.validate_entity(entity)
                elif expected_type == GamePlayer:
                    player = GamePlayer.from_dict(json_data)
                    return self.validate_player(player)
                elif expected_type == GameCircle:
                    circle = GameCircle.from_dict(json_data)
                    return self.validate_circle(circle)
                elif expected_type == Vector2:
                    vector = Vector2.from_dict(json_data)
                    return self.validate_vector(vector)
                else:
                    # Generic validation
                    schema_name = expected_type.__name__
                    return self.schema_manager.validate_data(json_data, schema_name)
            
            else:
                raise ValidationError(f"Unsupported format type: {format_type}")
                
        except Exception as e:
            raise ValidationError(f"Serialized data validation failed: {e}")


# Global instances
_schema_manager = SchemaManager()
_data_validator = DataValidator(_schema_manager)


# Convenience functions
def validate_entity(entity: GameEntity) -> bool:
    """Validate GameEntity using global validator."""
    return _data_validator.validate_entity(entity)


def validate_player(player: GamePlayer) -> bool:
    """Validate GamePlayer using global validator."""
    return _data_validator.validate_player(player)


def validate_circle(circle: GameCircle) -> bool:
    """Validate GameCircle using global validator."""
    return _data_validator.validate_circle(circle)


def validate_vector(vector: Vector2) -> bool:
    """Validate Vector2 using global validator."""
    return _data_validator.validate_vector(vector)


def validate_game_state(entities: List[GameEntity], 
                       players: List[GamePlayer], 
                       circles: List[GameCircle]) -> bool:
    """Validate complete game state using global validator."""
    return _data_validator.validate_game_state(entities, players, circles)


def get_schema(schema_name: str) -> Optional[Dict[str, Any]]:
    """Get schema by name using global schema manager."""
    return _schema_manager.get_schema(schema_name)


def register_schema(schema_name: str, schema: Dict[str, Any]):
    """Register custom schema with global schema manager."""
    _schema_manager.register_schema(schema_name, schema)


def list_available_schemas() -> List[str]:
    """List all available schema names."""
    return _schema_manager.list_schemas()