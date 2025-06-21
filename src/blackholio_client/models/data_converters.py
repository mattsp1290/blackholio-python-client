"""
Data Converters - Unified Data Transformation

Consolidates data conversion logic from blackholio-agent and client-pygame
into consistent, reusable converter classes.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Type
from .game_entities import GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState


logger = logging.getLogger(__name__)


class DataConverter(ABC):
    """
    Abstract base class for data converters.
    
    Provides consistent interface for converting between different
    data formats and our unified data models.
    """
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> Optional[Any]:
        """
        Convert dictionary data to model object.
        
        Args:
            data: Dictionary containing object data
            
        Returns:
            Model object or None if conversion fails
        """
        pass
    
    @abstractmethod
    def to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Convert model object to dictionary.
        
        Args:
            obj: Model object to convert
            
        Returns:
            Dictionary representation of object
        """
        pass
    
    def convert_list(self, data_list: List[Dict[str, Any]]) -> List[Any]:
        """
        Convert list of dictionaries to list of model objects.
        
        Args:
            data_list: List of dictionaries
            
        Returns:
            List of converted model objects
        """
        results = []
        for item in data_list:
            try:
                converted = self.from_dict(item)
                if converted is not None:
                    results.append(converted)
            except Exception as e:
                logger.error(f"Failed to convert item: {e}")
                logger.debug(f"Problematic item: {item}")
        
        return results


class EntityConverter(DataConverter):
    """
    Converter for GameEntity objects.
    
    Handles conversion between dictionary data and GameEntity instances,
    consolidating entity conversion logic from both projects.
    """
    
    def from_dict(self, data: Dict[str, Any]) -> Optional[GameEntity]:
        """
        Convert dictionary to GameEntity.
        
        Handles various data formats from different SpacetimeDB server languages.
        """
        try:
            if not data:
                return None
            
            # Extract entity ID (try different field names)
            entity_id = self._extract_entity_id(data)
            if not entity_id:
                logger.warning(f"No entity ID found in data: {data}")
                return None
            
            # Extract position
            position = self._extract_position(data)
            
            # Extract velocity
            velocity = self._extract_velocity(data)
            
            # Extract other fields with defaults
            mass = float(data.get('mass', 1.0))
            radius = float(data.get('radius', 1.0))
            
            # Extract entity type
            entity_type = self._extract_entity_type(data)
            
            # Extract status
            is_active = bool(data.get('is_active', data.get('active', True)))
            
            # Extract timestamps
            created_at = data.get('created_at')
            updated_at = data.get('updated_at')
            
            return GameEntity(
                entity_id=entity_id,
                position=position,
                velocity=velocity,
                mass=mass,
                radius=radius,
                entity_type=entity_type,
                is_active=is_active,
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to convert dictionary to GameEntity: {e}")
            logger.debug(f"Problematic data: {data}")
            return None
    
    def to_dict(self, entity: GameEntity) -> Dict[str, Any]:
        """Convert GameEntity to dictionary."""
        if not isinstance(entity, GameEntity):
            raise ValueError("Object must be a GameEntity instance")
        
        return entity.to_dict()
    
    def _extract_entity_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract entity ID from various possible field names."""
        id_fields = ['entity_id', 'id', 'object_id', 'uid']
        
        for field in id_fields:
            if field in data and data[field] is not None:
                return str(data[field])
        
        return None
    
    def _extract_position(self, data: Dict[str, Any]) -> Vector2:
        """Extract position from data with fallback handling."""
        position_data = data.get('position')
        
        if position_data:
            if isinstance(position_data, dict):
                return Vector2.from_dict(position_data)
            elif isinstance(position_data, (list, tuple)) and len(position_data) >= 2:
                return Vector2(float(position_data[0]), float(position_data[1]))
        
        # Try individual x, y fields
        x = data.get('x', data.get('pos_x', 0.0))
        y = data.get('y', data.get('pos_y', 0.0))
        
        return Vector2(float(x), float(y))
    
    def _extract_velocity(self, data: Dict[str, Any]) -> Vector2:
        """Extract velocity from data with fallback handling."""
        velocity_data = data.get('velocity')
        
        if velocity_data:
            if isinstance(velocity_data, dict):
                return Vector2.from_dict(velocity_data)
            elif isinstance(velocity_data, (list, tuple)) and len(velocity_data) >= 2:
                return Vector2(float(velocity_data[0]), float(velocity_data[1]))
        
        # Try individual velocity fields
        vx = data.get('vx', data.get('vel_x', 0.0))
        vy = data.get('vy', data.get('vel_y', 0.0))
        
        return Vector2(float(vx), float(vy))
    
    def _extract_entity_type(self, data: Dict[str, Any]) -> EntityType:
        """Extract entity type from data."""
        type_fields = ['entity_type', 'type', 'kind', 'object_type']
        
        for field in type_fields:
            if field in data and data[field]:
                type_str = str(data[field]).lower()
                try:
                    return EntityType(type_str)
                except ValueError:
                    continue
        
        return EntityType.UNKNOWN


class PlayerConverter(DataConverter):
    """
    Converter for GamePlayer objects.
    
    Handles conversion between dictionary data and GamePlayer instances,
    consolidating player conversion logic from both projects.
    """
    
    def from_dict(self, data: Dict[str, Any]) -> Optional[GamePlayer]:
        """
        Convert dictionary to GamePlayer.
        
        Handles various player data formats from different server implementations.
        """
        try:
            if not data:
                return None
            
            # Extract player ID
            player_id = self._extract_player_id(data)
            entity_id = player_id or self._extract_entity_id(data)
            
            if not entity_id:
                logger.warning(f"No player/entity ID found in data: {data}")
                return None
            
            # Extract player name
            name = str(data.get('name', data.get('player_name', '')))
            
            # Extract position and velocity
            position = self._extract_position(data)
            velocity = self._extract_velocity(data)
            direction = self._extract_direction(data)
            
            # Extract player-specific fields
            mass = float(data.get('mass', 1.0))
            radius = float(data.get('radius', 1.0))
            score = int(data.get('score', 0))
            
            # Extract player state
            state = self._extract_player_state(data)
            
            # Extract other fields
            color = data.get('color')
            input_direction = self._extract_input_direction(data)
            max_speed = float(data.get('max_speed', 100.0))
            acceleration = float(data.get('acceleration', 200.0))
            is_active = bool(data.get('is_active', data.get('active', True)))
            
            # Extract timestamps
            created_at = data.get('created_at')
            updated_at = data.get('updated_at')
            
            return GamePlayer(
                entity_id=entity_id,
                player_id=player_id or entity_id,
                name=name,
                position=position,
                velocity=velocity,
                direction=direction,
                mass=mass,
                radius=radius,
                score=score,
                state=state,
                color=color,
                input_direction=input_direction,
                max_speed=max_speed,
                acceleration=acceleration,
                is_active=is_active,
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to convert dictionary to GamePlayer: {e}")
            logger.debug(f"Problematic data: {data}")
            return None
    
    def to_dict(self, player: GamePlayer) -> Dict[str, Any]:
        """Convert GamePlayer to dictionary."""
        if not isinstance(player, GamePlayer):
            raise ValueError("Object must be a GamePlayer instance")
        
        return player.to_dict()
    
    def _extract_player_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract player ID from various possible field names."""
        id_fields = ['player_id', 'id', 'user_id', 'uid']
        
        for field in id_fields:
            if field in data and data[field] is not None:
                return str(data[field])
        
        return None
    
    def _extract_entity_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract entity ID from various possible field names."""
        id_fields = ['entity_id', 'object_id', 'id']
        
        for field in id_fields:
            if field in data and data[field] is not None:
                return str(data[field])
        
        return None
    
    def _extract_position(self, data: Dict[str, Any]) -> Vector2:
        """Extract position from data."""
        position_data = data.get('position')
        
        if position_data:
            if isinstance(position_data, dict):
                return Vector2.from_dict(position_data)
            elif isinstance(position_data, (list, tuple)) and len(position_data) >= 2:
                return Vector2(float(position_data[0]), float(position_data[1]))
        
        # Try individual x, y fields
        x = data.get('x', data.get('pos_x', 0.0))
        y = data.get('y', data.get('pos_y', 0.0))
        
        return Vector2(float(x), float(y))
    
    def _extract_velocity(self, data: Dict[str, Any]) -> Vector2:
        """Extract velocity from data."""
        velocity_data = data.get('velocity')
        
        if velocity_data:
            if isinstance(velocity_data, dict):
                return Vector2.from_dict(velocity_data)
            elif isinstance(velocity_data, (list, tuple)) and len(velocity_data) >= 2:
                return Vector2(float(velocity_data[0]), float(velocity_data[1]))
        
        # Try individual velocity fields
        vx = data.get('vx', data.get('vel_x', 0.0))
        vy = data.get('vy', data.get('vel_y', 0.0))
        
        return Vector2(float(vx), float(vy))
    
    def _extract_direction(self, data: Dict[str, Any]) -> Vector2:
        """Extract direction from data."""
        direction_data = data.get('direction')
        
        if direction_data:
            if isinstance(direction_data, dict):
                return Vector2.from_dict(direction_data)
            elif isinstance(direction_data, (list, tuple)) and len(direction_data) >= 2:
                return Vector2(float(direction_data[0]), float(direction_data[1]))
        
        # Try individual direction fields
        dx = data.get('dx', data.get('dir_x', 0.0))
        dy = data.get('dy', data.get('dir_y', 0.0))
        
        return Vector2(float(dx), float(dy))
    
    def _extract_input_direction(self, data: Dict[str, Any]) -> Vector2:
        """Extract input direction from data."""
        input_data = data.get('input_direction', data.get('input'))
        
        if input_data:
            if isinstance(input_data, dict):
                return Vector2.from_dict(input_data)
            elif isinstance(input_data, (list, tuple)) and len(input_data) >= 2:
                return Vector2(float(input_data[0]), float(input_data[1]))
        
        return Vector2.zero()
    
    def _extract_player_state(self, data: Dict[str, Any]) -> PlayerState:
        """Extract player state from data."""
        state_fields = ['state', 'status', 'player_state']
        
        for field in state_fields:
            if field in data and data[field]:
                state_str = str(data[field]).lower()
                try:
                    return PlayerState(state_str)
                except ValueError:
                    continue
        
        # Check for active/inactive flags
        if 'is_active' in data:
            return PlayerState.ACTIVE if data['is_active'] else PlayerState.INACTIVE
        elif 'active' in data:
            return PlayerState.ACTIVE if data['active'] else PlayerState.INACTIVE
        
        return PlayerState.ACTIVE


class CircleConverter(DataConverter):
    """
    Converter for GameCircle objects.
    
    Handles conversion between dictionary data and GameCircle instances,
    consolidating circle conversion logic from both projects.
    """
    
    def from_dict(self, data: Dict[str, Any]) -> Optional[GameCircle]:
        """
        Convert dictionary to GameCircle.
        
        Handles various circle data formats from different server implementations.
        """
        try:
            if not data:
                return None
            
            # Extract circle ID
            circle_id = self._extract_circle_id(data)
            entity_id = circle_id or self._extract_entity_id(data)
            
            if not entity_id:
                logger.warning(f"No circle/entity ID found in data: {data}")
                return None
            
            # Extract position and velocity
            position = self._extract_position(data)
            velocity = self._extract_velocity(data)
            
            # Extract circle-specific fields
            mass = float(data.get('mass', 1.0))
            radius = float(data.get('radius', 1.0))
            color = data.get('color')
            circle_type = str(data.get('circle_type', data.get('type', 'food')))
            value = int(data.get('value', data.get('points', 1)))
            respawn_time = data.get('respawn_time')
            is_active = bool(data.get('is_active', data.get('active', True)))
            
            # Extract timestamps
            created_at = data.get('created_at')
            updated_at = data.get('updated_at')
            
            return GameCircle(
                entity_id=entity_id,
                circle_id=circle_id or entity_id,
                position=position,
                velocity=velocity,
                mass=mass,
                radius=radius,
                color=color,
                circle_type=circle_type,
                value=value,
                respawn_time=respawn_time,
                is_active=is_active,
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to convert dictionary to GameCircle: {e}")
            logger.debug(f"Problematic data: {data}")
            return None
    
    def to_dict(self, circle: GameCircle) -> Dict[str, Any]:
        """Convert GameCircle to dictionary."""
        if not isinstance(circle, GameCircle):
            raise ValueError("Object must be a GameCircle instance")
        
        return circle.to_dict()
    
    def _extract_circle_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract circle ID from various possible field names."""
        id_fields = ['circle_id', 'id', 'food_id', 'object_id']
        
        for field in id_fields:
            if field in data and data[field] is not None:
                return str(data[field])
        
        return None
    
    def _extract_entity_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract entity ID from various possible field names."""
        id_fields = ['entity_id', 'object_id', 'id']
        
        for field in id_fields:
            if field in data and data[field] is not None:
                return str(data[field])
        
        return None
    
    def _extract_position(self, data: Dict[str, Any]) -> Vector2:
        """Extract position from data."""
        position_data = data.get('position')
        
        if position_data:
            if isinstance(position_data, dict):
                return Vector2.from_dict(position_data)
            elif isinstance(position_data, (list, tuple)) and len(position_data) >= 2:
                return Vector2(float(position_data[0]), float(position_data[1]))
        
        # Try individual x, y fields
        x = data.get('x', data.get('pos_x', 0.0))
        y = data.get('y', data.get('pos_y', 0.0))
        
        return Vector2(float(x), float(y))
    
    def _extract_velocity(self, data: Dict[str, Any]) -> Vector2:
        """Extract velocity from data."""
        velocity_data = data.get('velocity')
        
        if velocity_data:
            if isinstance(velocity_data, dict):
                return Vector2.from_dict(velocity_data)
            elif isinstance(velocity_data, (list, tuple)) and len(velocity_data) >= 2:
                return Vector2(float(velocity_data[0]), float(velocity_data[1]))
        
        return Vector2.zero()


# Convenience functions for quick conversions
def convert_to_entity(data: Dict[str, Any]) -> Optional[GameEntity]:
    """Convert dictionary to GameEntity using EntityConverter."""
    converter = EntityConverter()
    return converter.from_dict(data)


def convert_to_player(data: Dict[str, Any]) -> Optional[GamePlayer]:
    """Convert dictionary to GamePlayer using PlayerConverter."""
    converter = PlayerConverter()
    return converter.from_dict(data)


def convert_to_circle(data: Dict[str, Any]) -> Optional[GameCircle]:
    """Convert dictionary to GameCircle using CircleConverter."""
    converter = CircleConverter()
    return converter.from_dict(data)


def convert_entities_list(data_list: List[Dict[str, Any]]) -> List[GameEntity]:
    """Convert list of dictionaries to list of GameEntity objects."""
    converter = EntityConverter()
    return converter.convert_list(data_list)


def convert_players_list(data_list: List[Dict[str, Any]]) -> List[GamePlayer]:
    """Convert list of dictionaries to list of GamePlayer objects."""
    converter = PlayerConverter()
    return converter.convert_list(data_list)


def convert_circles_list(data_list: List[Dict[str, Any]]) -> List[GameCircle]:
    """Convert list of dictionaries to list of GameCircle objects."""
    converter = CircleConverter()
    return converter.convert_list(data_list)


# Legacy compatibility functions (for migration from existing projects)
def convert_to_dict(obj: Union[GameEntity, GamePlayer, GameCircle]) -> Dict[str, Any]:
    """
    Convert any game object to dictionary.
    
    Provides compatibility with existing conversion patterns.
    """
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        # Fallback for objects without to_dict method
        result = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, Vector2):
                result[key] = value.to_dict()
            elif hasattr(value, 'value'):  # Enum
                result[key] = value.value
            else:
                result[key] = value
        return result
    else:
        raise ValueError(f"Cannot convert object of type {type(obj)} to dictionary")


def extract_entity_data(entity_obj: Any) -> Dict[str, Any]:
    """
    Extract entity data from various object types.
    
    Provides compatibility with existing extraction patterns.
    """
    return convert_to_dict(entity_obj)
