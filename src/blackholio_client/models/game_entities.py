"""
Game Entities - Unified Data Models

Consolidates game entity definitions from blackholio-agent and client-pygame
into consistent, well-typed data classes with serialization support.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import json


class EntityType(Enum):
    """Entity type enumeration."""
    PLAYER = "player"
    CIRCLE = "circle"
    FOOD = "food"
    OBSTACLE = "obstacle"
    UNKNOWN = "unknown"


class PlayerState(Enum):
    """Player state enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SPECTATING = "spectating"
    DISCONNECTED = "disconnected"


@dataclass
class Vector2:
    """
    2D Vector class for positions, velocities, and directions.
    
    Consolidates Vector2 implementations from both projects
    with mathematical operations and utility methods.
    """
    x: float = 0.0
    y: float = 0.0
    
    def __post_init__(self):
        """Ensure values are floats."""
        self.x = float(self.x)
        self.y = float(self.y)
    
    def __add__(self, other: 'Vector2') -> 'Vector2':
        """Vector addition."""
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Vector2') -> 'Vector2':
        """Vector subtraction."""
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Vector2':
        """Scalar multiplication."""
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector2':
        """Scalar division."""
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return Vector2(self.x / scalar, self.y / scalar)
    
    def __eq__(self, other: 'Vector2') -> bool:
        """Vector equality with floating point tolerance."""
        if not isinstance(other, Vector2):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9
    
    def __str__(self) -> str:
        """String representation."""
        return f"Vector2({self.x:.2f}, {self.y:.2f})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Vector2(x={self.x}, y={self.y})"
    
    @property
    def magnitude(self) -> float:
        """Calculate vector magnitude (length)."""
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    @property
    def magnitude_squared(self) -> float:
        """Calculate squared magnitude (faster than magnitude)."""
        return self.x * self.x + self.y * self.y
    
    def normalize(self) -> 'Vector2':
        """
        Return normalized vector (unit vector).
        
        Returns:
            Normalized Vector2 or zero vector if magnitude is zero
        """
        mag = self.magnitude
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def distance_to(self, other: 'Vector2') -> float:
        """Calculate distance to another vector."""
        return (self - other).magnitude
    
    def distance_squared_to(self, other: 'Vector2') -> float:
        """Calculate squared distance to another vector (faster)."""
        return (self - other).magnitude_squared
    
    def dot(self, other: 'Vector2') -> float:
        """Calculate dot product with another vector."""
        return self.x * other.x + self.y * other.y
    
    def cross(self, other: 'Vector2') -> float:
        """Calculate 2D cross product (returns scalar)."""
        return self.x * other.y - self.y * other.x
    
    def angle(self) -> float:
        """Get angle in radians from positive x-axis."""
        return math.atan2(self.y, self.x)
    
    def rotate(self, angle: float) -> 'Vector2':
        """
        Rotate vector by angle in radians.
        
        Args:
            angle: Rotation angle in radians
            
        Returns:
            Rotated Vector2
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )
    
    def clamp_magnitude(self, max_magnitude: float) -> 'Vector2':
        """
        Clamp vector magnitude to maximum value.
        
        Args:
            max_magnitude: Maximum allowed magnitude
            
        Returns:
            Vector2 with clamped magnitude
        """
        if self.magnitude <= max_magnitude:
            return Vector2(self.x, self.y)
        return self.normalize() * max_magnitude
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {'x': self.x, 'y': self.y}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vector2':
        """Create Vector2 from dictionary."""
        return cls(
            x=float(data.get('x', 0.0)),
            y=float(data.get('y', 0.0))
        )
    
    @classmethod
    def zero(cls) -> 'Vector2':
        """Create zero vector."""
        return cls(0.0, 0.0)
    
    @classmethod
    def one(cls) -> 'Vector2':
        """Create unit vector (1, 1)."""
        return cls(1.0, 1.0)
    
    @classmethod
    def up(cls) -> 'Vector2':
        """Create up vector (0, 1)."""
        return cls(0.0, 1.0)
    
    @classmethod
    def down(cls) -> 'Vector2':
        """Create down vector (0, -1)."""
        return cls(0.0, -1.0)
    
    @classmethod
    def left(cls) -> 'Vector2':
        """Create left vector (-1, 0)."""
        return cls(-1.0, 0.0)
    
    @classmethod
    def right(cls) -> 'Vector2':
        """Create right vector (1, 0)."""
        return cls(1.0, 0.0)


@dataclass
class GameEntity:
    """
    Base game entity class.
    
    Consolidates entity representations from both projects
    with consistent fields and methods.
    """
    entity_id: str
    position: Vector2 = field(default_factory=Vector2.zero)
    velocity: Vector2 = field(default_factory=Vector2.zero)
    mass: float = 1.0
    radius: float = 1.0
    entity_type: EntityType = EntityType.UNKNOWN
    is_active: bool = True
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure position and velocity are Vector2 instances
        if not isinstance(self.position, Vector2):
            if isinstance(self.position, dict):
                self.position = Vector2.from_dict(self.position)
            elif isinstance(self.position, (list, tuple)) and len(self.position) >= 2:
                self.position = Vector2(self.position[0], self.position[1])
            else:
                self.position = Vector2.zero()
        
        if not isinstance(self.velocity, Vector2):
            if isinstance(self.velocity, dict):
                self.velocity = Vector2.from_dict(self.velocity)
            elif isinstance(self.velocity, (list, tuple)) and len(self.velocity) >= 2:
                self.velocity = Vector2(self.velocity[0], self.velocity[1])
            else:
                self.velocity = Vector2.zero()
        
        # Ensure entity_type is EntityType enum
        if isinstance(self.entity_type, str):
            try:
                self.entity_type = EntityType(self.entity_type.lower())
            except ValueError:
                self.entity_type = EntityType.UNKNOWN
    
    @property
    def area(self) -> float:
        """Calculate entity area based on radius."""
        return math.pi * self.radius * self.radius
    
    @property
    def diameter(self) -> float:
        """Calculate entity diameter."""
        return self.radius * 2
    
    def distance_to(self, other: 'GameEntity') -> float:
        """Calculate distance to another entity."""
        return self.position.distance_to(other.position)
    
    def distance_squared_to(self, other: 'GameEntity') -> float:
        """Calculate squared distance to another entity (faster)."""
        return self.position.distance_squared_to(other.position)
    
    def is_colliding_with(self, other: 'GameEntity') -> bool:
        """
        Check if this entity is colliding with another entity.
        
        Args:
            other: Other entity to check collision with
            
        Returns:
            True if entities are colliding
        """
        distance = self.distance_to(other)
        return distance < (self.radius + other.radius)
    
    def can_consume(self, other: 'GameEntity') -> bool:
        """
        Check if this entity can consume another entity.
        
        Basic rule: entity must be significantly larger to consume another.
        
        Args:
            other: Other entity to check
            
        Returns:
            True if this entity can consume the other
        """
        return self.mass > other.mass * 1.1  # 10% larger required
    
    def contains_point(self, point: Vector2) -> bool:
        """
        Check if a point is within this entity's bounds.
        
        Args:
            point: Point to check
            
        Returns:
            True if the point is within the entity's radius
        """
        distance = self.position.distance_to(point)
        return distance <= self.radius
    
    def update_position(self, delta_time: float):
        """
        Update position based on velocity and delta time.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self.position = self.position + (self.velocity * delta_time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for serialization."""
        return {
            'entity_id': self.entity_id,
            'position': self.position.to_dict(),
            'velocity': self.velocity.to_dict(),
            'mass': self.mass,
            'radius': self.radius,
            'entity_type': self.entity_type.value,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameEntity':
        """Create GameEntity from dictionary."""
        return cls(
            entity_id=str(data.get('entity_id', '')),
            position=Vector2.from_dict(data.get('position', {})),
            velocity=Vector2.from_dict(data.get('velocity', {})),
            mass=float(data.get('mass', 1.0)),
            radius=float(data.get('radius', 1.0)),
            entity_type=data.get('entity_type', EntityType.UNKNOWN),
            is_active=bool(data.get('is_active', True)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class GamePlayer(GameEntity):
    """
    Player entity class.
    
    Extends GameEntity with player-specific properties
    consolidated from both projects.
    """
    player_id: str = ""
    name: str = ""
    direction: Vector2 = field(default_factory=Vector2.zero)
    score: int = 0
    state: PlayerState = PlayerState.ACTIVE
    color: Optional[str] = None
    input_direction: Vector2 = field(default_factory=Vector2.zero)
    max_speed: float = 100.0
    acceleration: float = 200.0
    
    def __post_init__(self):
        """Post-initialization processing."""
        super().__post_init__()
        
        # Use player_id as entity_id if not set
        if not self.entity_id and self.player_id:
            self.entity_id = self.player_id
        elif not self.player_id and self.entity_id:
            self.player_id = self.entity_id
        
        # Ensure direction and input_direction are Vector2 instances
        if not isinstance(self.direction, Vector2):
            if isinstance(self.direction, dict):
                self.direction = Vector2.from_dict(self.direction)
            elif isinstance(self.direction, (list, tuple)) and len(self.direction) >= 2:
                self.direction = Vector2(self.direction[0], self.direction[1])
            else:
                self.direction = Vector2.zero()
        
        if not isinstance(self.input_direction, Vector2):
            if isinstance(self.input_direction, dict):
                self.input_direction = Vector2.from_dict(self.input_direction)
            elif isinstance(self.input_direction, (list, tuple)) and len(self.input_direction) >= 2:
                self.input_direction = Vector2(self.input_direction[0], self.input_direction[1])
            else:
                self.input_direction = Vector2.zero()
        
        # Ensure state is PlayerState enum
        if isinstance(self.state, str):
            try:
                self.state = PlayerState(self.state.lower())
            except ValueError:
                self.state = PlayerState.ACTIVE
        
        # Set entity type to player
        self.entity_type = EntityType.PLAYER
    
    def update_input(self, input_direction: Vector2):
        """
        Update player input direction.
        
        Args:
            input_direction: New input direction vector
        """
        self.input_direction = input_direction.normalize() if input_direction.magnitude > 0 else Vector2.zero()
    
    def update_movement(self, delta_time: float):
        """
        Update player movement based on input and physics.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if self.state != PlayerState.ACTIVE:
            return
        
        # Apply acceleration based on input
        if self.input_direction.magnitude > 0:
            acceleration_vector = self.input_direction * self.acceleration * delta_time
            self.velocity = self.velocity + acceleration_vector
            
            # Clamp to max speed
            self.velocity = self.velocity.clamp_magnitude(self.max_speed)
            
            # Update direction
            self.direction = self.velocity.normalize()
        else:
            # Apply friction when no input
            friction = 0.9
            self.velocity = self.velocity * friction
            
            # Stop if velocity is very small
            if self.velocity.magnitude < 0.1:
                self.velocity = Vector2.zero()
        
        # Update position
        self.update_position(delta_time)
    
    def add_score(self, points: int):
        """
        Add points to player score.
        
        Args:
            points: Points to add
        """
        self.score += points
        if self.score < 0:
            self.score = 0
    
    def grow(self, mass_increase: float):
        """
        Increase player mass and radius.
        
        Args:
            mass_increase: Amount to increase mass
        """
        self.mass += mass_increase
        # Radius grows with square root of mass for balanced gameplay
        self.radius = math.sqrt(self.mass) * 0.5
    
    def is_alive(self) -> bool:
        """Check if player is alive and active."""
        return self.state == PlayerState.ACTIVE and self.is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'player_id': self.player_id,
            'name': self.name,
            'direction': self.direction.to_dict(),
            'score': self.score,
            'state': self.state.value,
            'color': self.color,
            'input_direction': self.input_direction.to_dict(),
            'max_speed': self.max_speed,
            'acceleration': self.acceleration
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GamePlayer':
        """Create GamePlayer from dictionary."""
        return cls(
            entity_id=str(data.get('entity_id', data.get('player_id', ''))),
            player_id=str(data.get('player_id', data.get('entity_id', ''))),
            name=str(data.get('name', '')),
            position=Vector2.from_dict(data.get('position', {})),
            velocity=Vector2.from_dict(data.get('velocity', {})),
            direction=Vector2.from_dict(data.get('direction', {})),
            mass=float(data.get('mass', 1.0)),
            radius=float(data.get('radius', 1.0)),
            score=int(data.get('score', 0)),
            state=data.get('state', PlayerState.ACTIVE),
            color=data.get('color'),
            input_direction=Vector2.from_dict(data.get('input_direction', {})),
            max_speed=float(data.get('max_speed', 100.0)),
            acceleration=float(data.get('acceleration', 200.0)),
            is_active=bool(data.get('is_active', True)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class GameCircle(GameEntity):
    """
    Circle entity class for food, obstacles, and other circular objects.
    
    Consolidates circle representations from both projects.
    """
    circle_id: str = ""
    color: Optional[str] = None
    circle_type: str = "food"
    value: int = 1
    respawn_time: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        super().__post_init__()
        
        # Use circle_id as entity_id if not set
        if not self.entity_id and self.circle_id:
            self.entity_id = self.circle_id
        elif not self.circle_id and self.entity_id:
            self.circle_id = self.entity_id
        
        # Set entity type based on circle type
        if self.circle_type.lower() == "food":
            self.entity_type = EntityType.FOOD
        elif self.circle_type.lower() == "obstacle":
            self.entity_type = EntityType.OBSTACLE
        else:
            self.entity_type = EntityType.CIRCLE
    
    def is_consumable(self) -> bool:
        """Check if this circle can be consumed by players."""
        return self.circle_type.lower() in ["food", "consumable"] and self.is_active
    
    def consume(self) -> int:
        """
        Consume this circle and return its value.
        
        Returns:
            Value of the consumed circle
        """
        if not self.is_consumable():
            return 0
        
        self.is_active = False
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert circle to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'circle_id': self.circle_id,
            'color': self.color,
            'circle_type': self.circle_type,
            'value': self.value,
            'respawn_time': self.respawn_time
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameCircle':
        """Create GameCircle from dictionary."""
        return cls(
            entity_id=str(data.get('entity_id', data.get('circle_id', ''))),
            circle_id=str(data.get('circle_id', data.get('entity_id', ''))),
            position=Vector2.from_dict(data.get('position', {})),
            velocity=Vector2.from_dict(data.get('velocity', {})),
            mass=float(data.get('mass', 1.0)),
            radius=float(data.get('radius', 1.0)),
            color=data.get('color'),
            circle_type=str(data.get('circle_type', 'food')),
            value=int(data.get('value', 1)),
            respawn_time=data.get('respawn_time'),
            is_active=bool(data.get('is_active', True)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
