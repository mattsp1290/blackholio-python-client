import logging

logger = logging.getLogger(__name__)
"""
Game-specific event types for the Blackholio event system.

Defines all game-related events including player actions, entity changes,
game state updates, and gameplay statistics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..models.game_entities import GamePlayer, GameEntity, GameCircle, Vector2
from .base import Event, EventType, EventPriority


@dataclass
class GameEvent(Event):
    """Base class for all game-related events."""
    
    event_type: EventType = field(default=EventType.GAME_STATE)
    
    def validate(self) -> None:
        """Validate game event data."""
        # Base validation is sufficient for most game events
        pass


@dataclass
class PlayerJoinedEvent(GameEvent):
    """Event fired when a player joins the game."""
    
    player_data: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.PLAYER)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "PlayerJoined"
    
    def validate(self) -> None:
        """Validate player joined event."""
        if not self.player_data:
            raise ValueError("PlayerJoinedEvent requires player_data")
        
        # Add player data to event data for easy access
        self.data.update({
            'player_id': self.player_data.get('id'),
            'player_name': self.player_data.get('name'),
            'join_timestamp': self.timestamp
        })
    
    def get_player(self) -> Optional[GamePlayer]:
        """Get GamePlayer object from event data."""
        try:
            return GamePlayer.from_dict(self.player_data)
        except Exception:
            return None


@dataclass
class PlayerLeftEvent(GameEvent):
    """Event fired when a player leaves the game."""
    
    player_data: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = field(default=None)
    event_type: EventType = field(default=EventType.PLAYER)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "PlayerLeft"
    
    def validate(self) -> None:
        """Validate player left event."""
        if not self.player_data:
            raise ValueError("PlayerLeftEvent requires player_data")
        
        # Add player data to event data for easy access
        self.data.update({
            'player_id': self.player_data.get('id'),
            'player_name': self.player_data.get('name'),
            'leave_reason': self.reason,
            'leave_timestamp': self.timestamp
        })
    
    def get_player(self) -> Optional[GamePlayer]:
        """Get GamePlayer object from event data."""
        try:
            return GamePlayer.from_dict(self.player_data)
        except Exception:
            return None


@dataclass
class EntityCreatedEvent(GameEvent):
    """Event fired when a game entity is created."""
    
    entity_data: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.ENTITY)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "EntityCreated"
    
    def validate(self) -> None:
        """Validate entity created event."""
        if not self.entity_data:
            raise ValueError("EntityCreatedEvent requires entity_data")
        
        # Add entity data to event data for easy access
        self.data.update({
            'entity_id': self.entity_data.get('id'),
            'entity_type': self.entity_data.get('type'),
            'owner_id': self.entity_data.get('owner_id'),
            'creation_timestamp': self.timestamp
        })
    
    def get_entity(self) -> Optional[GameEntity]:
        """Get GameEntity object from event data."""
        try:
            return GameEntity.from_dict(self.entity_data)
        except Exception:
            return None


@dataclass
class EntityUpdatedEvent(GameEvent):
    """Event fired when a game entity is updated."""
    
    old_entity_data: Dict[str, Any] = field(default_factory=dict)
    new_entity_data: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.ENTITY)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "EntityUpdated"
    
    def validate(self) -> None:
        """Validate entity updated event."""
        if not self.old_entity_data or not self.new_entity_data:
            raise ValueError("EntityUpdatedEvent requires both old_entity_data and new_entity_data")
        
        # Calculate changes
        changes = {}
        for key in set(self.old_entity_data.keys()) | set(self.new_entity_data.keys()):
            old_value = self.old_entity_data.get(key)
            new_value = self.new_entity_data.get(key)
            if old_value != new_value:
                changes[key] = {'old': old_value, 'new': new_value}
        
        # Add entity data to event data for easy access
        self.data.update({
            'entity_id': self.new_entity_data.get('id'),
            'entity_type': self.new_entity_data.get('type'),
            'owner_id': self.new_entity_data.get('owner_id'),
            'changes': changes,
            'update_timestamp': self.timestamp
        })
    
    def get_old_entity(self) -> Optional[GameEntity]:
        """Get old GameEntity object from event data."""
        try:
            return GameEntity.from_dict(self.old_entity_data)
        except Exception:
            return None
    
    def get_new_entity(self) -> Optional[GameEntity]:
        """Get new GameEntity object from event data."""
        try:
            return GameEntity.from_dict(self.new_entity_data)
        except Exception:
            return None
    
    def get_changes(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of changes between old and new entity."""
        return self.data.get('changes', {})


@dataclass
class EntityDestroyedEvent(GameEvent):
    """Event fired when a game entity is destroyed."""
    
    entity_data: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = field(default=None)
    event_type: EventType = field(default=EventType.ENTITY)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "EntityDestroyed"
    
    def validate(self) -> None:
        """Validate entity destroyed event."""
        if not self.entity_data:
            raise ValueError("EntityDestroyedEvent requires entity_data")
        
        # Add entity data to event data for easy access
        self.data.update({
            'entity_id': self.entity_data.get('id'),
            'entity_type': self.entity_data.get('type'),
            'owner_id': self.entity_data.get('owner_id'),
            'destruction_reason': self.reason,
            'destruction_timestamp': self.timestamp
        })
    
    def get_entity(self) -> Optional[GameEntity]:
        """Get GameEntity object from event data."""
        try:
            return GameEntity.from_dict(self.entity_data)
        except Exception:
            return None


@dataclass
class GameStateChangedEvent(GameEvent):
    """Event fired when the overall game state changes."""
    
    old_state: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.GAME_STATE)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "GameStateChanged"
    
    def validate(self) -> None:
        """Validate game state changed event."""
        if not self.new_state:
            raise ValueError("GameStateChangedEvent requires new_state")
        
        # Calculate state changes
        changes = {}
        for key in set(self.old_state.keys()) | set(self.new_state.keys()):
            old_value = self.old_state.get(key)
            new_value = self.new_state.get(key)
            if old_value != new_value:
                changes[key] = {'old': old_value, 'new': new_value}
        
        # Add state data to event data for easy access
        self.data.update({
            'game_id': self.new_state.get('game_id'),
            'state_changes': changes,
            'player_count': self.new_state.get('player_count'),
            'entity_count': self.new_state.get('entity_count'),
            'state_timestamp': self.timestamp
        })
    
    def get_state_changes(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of state changes."""
        return self.data.get('state_changes', {})


@dataclass
class PlayerMovedEvent(GameEvent):
    """Event fired when a player moves."""
    
    player_id: int = field(default=0)
    old_position: Optional[Vector2] = field(default=None)
    new_position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    velocity: Optional[Vector2] = field(default=None)
    event_type: EventType = field(default=EventType.PLAYER)
    priority: EventPriority = field(default=EventPriority.LOW)
    
    def get_event_name(self) -> str:
        return "PlayerMoved"
    
    def validate(self) -> None:
        """Validate player moved event."""
        if self.player_id <= 0:
            raise ValueError("PlayerMovedEvent requires valid player_id")
        
        if not isinstance(self.new_position, Vector2):
            raise ValueError("PlayerMovedEvent requires Vector2 new_position")
        
        # Calculate movement distance and direction
        distance = 0.0
        direction = Vector2(0, 0)
        
        if self.old_position and isinstance(self.old_position, Vector2):
            distance = self.old_position.distance_to(self.new_position)
            if distance > 0:
                direction = (self.new_position - self.old_position).normalized()
        
        # Add movement data to event data for easy access
        self.data.update({
            'player_id': self.player_id,
            'old_position': self.old_position.to_dict() if self.old_position else None,
            'new_position': self.new_position.to_dict(),
            'velocity': self.velocity.to_dict() if self.velocity else None,
            'movement_distance': distance,
            'movement_direction': direction.to_dict(),
            'movement_timestamp': self.timestamp
        })


@dataclass
class PlayerSplitEvent(GameEvent):
    """Event fired when a player splits their entity."""
    
    player_id: int = field(default=0)
    original_entity_data: Dict[str, Any] = field(default_factory=dict)
    new_entities_data: List[Dict[str, Any]] = field(default_factory=list)
    split_position: Optional[Vector2] = field(default=None)
    event_type: EventType = field(default=EventType.PLAYER)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "PlayerSplit"
    
    def validate(self) -> None:
        """Validate player split event."""
        if self.player_id <= 0:
            raise ValueError("PlayerSplitEvent requires valid player_id")
        
        if not self.original_entity_data:
            raise ValueError("PlayerSplitEvent requires original_entity_data")
        
        if not self.new_entities_data:
            raise ValueError("PlayerSplitEvent requires new_entities_data")
        
        # Add split data to event data for easy access
        self.data.update({
            'player_id': self.player_id,
            'original_entity_id': self.original_entity_data.get('id'),
            'new_entity_ids': [e.get('id') for e in self.new_entities_data],
            'split_count': len(self.new_entities_data),
            'split_position': self.split_position.to_dict() if self.split_position else None,
            'split_timestamp': self.timestamp
        })
    
    def get_original_entity(self) -> Optional[GameEntity]:
        """Get original GameEntity object from event data."""
        try:
            return GameEntity.from_dict(self.original_entity_data)
        except Exception:
            return None
    
    def get_new_entities(self) -> List[GameEntity]:
        """Get list of new GameEntity objects from event data."""
        entities = []
        for entity_data in self.new_entities_data:
            try:
                entities.append(GameEntity.from_dict(entity_data))
            except (ValueError, KeyError, TypeError) as e:
                logger.debug(f"Skipping invalid entity data: {e}")
                continue
        return entities


@dataclass
class GameStatsUpdatedEvent(GameEvent):
    """Event fired when game statistics are updated."""
    
    player_id: Optional[int] = field(default=None)
    stats_data: Dict[str, Any] = field(default_factory=dict)
    stats_type: str = field(default="player")  # "player", "session", "global"
    event_type: EventType = field(default=EventType.GAME_STATE)
    priority: EventPriority = field(default=EventPriority.LOW)
    
    def get_event_name(self) -> str:
        return "GameStatsUpdated"
    
    def validate(self) -> None:
        """Validate game stats updated event."""
        if not self.stats_data:
            raise ValueError("GameStatsUpdatedEvent requires stats_data")
        
        valid_types = ["player", "session", "global"]
        if self.stats_type not in valid_types:
            raise ValueError(f"stats_type must be one of {valid_types}")
        
        if self.stats_type == "player" and self.player_id is None:
            raise ValueError("player stats require player_id")
        
        # Add stats data to event data for easy access
        self.data.update({
            'player_id': self.player_id,
            'stats_type': self.stats_type,
            'stats_data': self.stats_data.copy(),
            'stats_timestamp': self.timestamp
        })


@dataclass
class GameCircleConsumedEvent(GameEvent):
    """Event fired when a game circle (food/entity) is consumed."""
    
    consumer_id: int = field(default=0)
    consumed_circle_data: Dict[str, Any] = field(default_factory=dict)
    mass_gained: float = field(default=0.0)
    event_type: EventType = field(default=EventType.ENTITY)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "GameCircleConsumed"
    
    def validate(self) -> None:
        """Validate game circle consumed event."""
        if self.consumer_id <= 0:
            raise ValueError("GameCircleConsumedEvent requires valid consumer_id")
        
        if not self.consumed_circle_data:
            raise ValueError("GameCircleConsumedEvent requires consumed_circle_data")
        
        # Add consumption data to event data for easy access
        self.data.update({
            'consumer_id': self.consumer_id,
            'consumed_circle_id': self.consumed_circle_data.get('id'),
            'mass_gained': self.mass_gained,
            'consumption_timestamp': self.timestamp
        })
    
    def get_consumed_circle(self) -> Optional[GameCircle]:
        """Get consumed GameCircle object from event data."""
        try:
            return GameCircle.from_dict(self.consumed_circle_data)
        except Exception:
            return None


@dataclass
class GameRoundStartedEvent(GameEvent):
    """Event fired when a new game round starts."""
    
    round_number: int = field(default=1)
    round_config: Dict[str, Any] = field(default_factory=dict)
    player_count: int = field(default=0)
    event_type: EventType = field(default=EventType.GAME_STATE)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "GameRoundStarted"
    
    def validate(self) -> None:
        """Validate game round started event."""
        if self.round_number <= 0:
            raise ValueError("GameRoundStartedEvent requires valid round_number")
        
        # Add round data to event data for easy access
        self.data.update({
            'round_number': self.round_number,
            'round_config': self.round_config.copy(),
            'player_count': self.player_count,
            'round_start_timestamp': self.timestamp
        })


@dataclass
class GameRoundEndedEvent(GameEvent):
    """Event fired when a game round ends."""
    
    round_number: int = field(default=1)
    winner_id: Optional[int] = field(default=None)
    final_stats: Dict[str, Any] = field(default_factory=dict)
    round_duration: float = field(default=0.0)
    event_type: EventType = field(default=EventType.GAME_STATE)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "GameRoundEnded"
    
    def validate(self) -> None:
        """Validate game round ended event."""
        if self.round_number <= 0:
            raise ValueError("GameRoundEndedEvent requires valid round_number")
        
        # Add round end data to event data for easy access
        self.data.update({
            'round_number': self.round_number,
            'winner_id': self.winner_id,
            'final_stats': self.final_stats.copy(),
            'round_duration': self.round_duration,
            'round_end_timestamp': self.timestamp
        })


# Convenience factory functions for common events
def create_player_joined_event(player_data: Dict[str, Any], **kwargs) -> PlayerJoinedEvent:
    """Create a PlayerJoinedEvent with the given data."""
    return PlayerJoinedEvent(player_data=player_data, **kwargs)


def create_player_left_event(player_data: Dict[str, Any], reason: Optional[str] = None, **kwargs) -> PlayerLeftEvent:
    """Create a PlayerLeftEvent with the given data."""
    return PlayerLeftEvent(player_data=player_data, reason=reason, **kwargs)


def create_entity_created_event(entity_data: Dict[str, Any], **kwargs) -> EntityCreatedEvent:
    """Create an EntityCreatedEvent with the given data."""
    return EntityCreatedEvent(entity_data=entity_data, **kwargs)


def create_entity_updated_event(old_entity_data: Dict[str, Any], new_entity_data: Dict[str, Any], **kwargs) -> EntityUpdatedEvent:
    """Create an EntityUpdatedEvent with the given data."""
    return EntityUpdatedEvent(old_entity_data=old_entity_data, new_entity_data=new_entity_data, **kwargs)


def create_entity_destroyed_event(entity_data: Dict[str, Any], reason: Optional[str] = None, **kwargs) -> EntityDestroyedEvent:
    """Create an EntityDestroyedEvent with the given data."""
    return EntityDestroyedEvent(entity_data=entity_data, reason=reason, **kwargs)


def create_game_state_changed_event(old_state: Dict[str, Any], new_state: Dict[str, Any], **kwargs) -> GameStateChangedEvent:
    """Create a GameStateChangedEvent with the given data."""
    return GameStateChangedEvent(old_state=old_state, new_state=new_state, **kwargs)


def create_player_moved_event(player_id: int, new_position: Vector2, old_position: Optional[Vector2] = None, velocity: Optional[Vector2] = None, **kwargs) -> PlayerMovedEvent:
    """Create a PlayerMovedEvent with the given data."""
    return PlayerMovedEvent(player_id=player_id, new_position=new_position, old_position=old_position, velocity=velocity, **kwargs)