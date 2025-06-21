"""
Physics Calculations - Shared Game Physics

Consolidates common physics calculations from blackholio-agent and client-pygame
into reusable functions for consistent game mechanics across all implementations.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from .game_entities import GameEntity, GamePlayer, GameCircle, Vector2


def calculate_center_of_mass(entities: List[GameEntity]) -> Vector2:
    """
    Calculate the center of mass for a list of entities.
    
    Consolidates center of mass calculations from both projects
    with consistent mathematical implementation.
    
    Args:
        entities: List of game entities
        
    Returns:
        Vector2 representing the center of mass position
    """
    if not entities:
        return Vector2.zero()
    
    total_mass = 0.0
    weighted_position = Vector2.zero()
    
    for entity in entities:
        if entity.is_active and entity.mass > 0:
            total_mass += entity.mass
            weighted_position = weighted_position + (entity.position * entity.mass)
    
    if total_mass > 0:
        return weighted_position / total_mass
    else:
        return Vector2.zero()


def calculate_center_of_mass_from_data(entities: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Calculate center of mass from entity data dictionaries.
    
    Provides compatibility with existing implementations that use
    dictionary data instead of entity objects.
    
    Args:
        entities: List of entity data dictionaries
        
    Returns:
        Tuple of (x, y) coordinates for center of mass
    """
    if not entities:
        return (0.0, 0.0)
    
    total_mass = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    
    for entity in entities:
        mass = float(entity.get('mass', 1.0))
        x = float(entity.get('x', entity.get('position', {}).get('x', 0.0)))
        y = float(entity.get('y', entity.get('position', {}).get('y', 0.0)))
        
        if mass > 0:
            total_mass += mass
            weighted_x += x * mass
            weighted_y += y * mass
    
    if total_mass > 0:
        return (weighted_x / total_mass, weighted_y / total_mass)
    else:
        return (0.0, 0.0)


def calculate_distance(pos1: Vector2, pos2: Vector2) -> float:
    """
    Calculate Euclidean distance between two positions.
    
    Args:
        pos1: First position
        pos2: Second position
        
    Returns:
        Distance between positions
    """
    return pos1.distance_to(pos2)


def calculate_distance_squared(pos1: Vector2, pos2: Vector2) -> float:
    """
    Calculate squared distance between two positions.
    
    Faster than regular distance calculation when only comparison is needed.
    
    Args:
        pos1: First position
        pos2: Second position
        
    Returns:
        Squared distance between positions
    """
    return pos1.distance_squared_to(pos2)


def calculate_entity_radius(mass: float, base_factor: float = 0.5, min_radius: float = 1.0) -> float:
    """
    Calculate entity radius based on mass.
    
    Consolidates radius calculation from both projects with configurable parameters.
    Common pattern: radius = sqrt(mass) * factor with minimum radius.
    
    Args:
        mass: Entity mass
        base_factor: Scaling factor for radius calculation
        min_radius: Minimum allowed radius
        
    Returns:
        Calculated radius
    """
    if mass <= 0:
        return min_radius
    
    calculated_radius = math.sqrt(mass) * base_factor
    return max(min_radius, calculated_radius)


def calculate_player_radius(mass: float, min_radius: float = 15.0) -> float:
    """
    Calculate player radius based on mass.
    
    Uses specific scaling for player entities to ensure visibility.
    From client-pygame: max(15, (mass * 0.8) ** 0.5)
    
    Args:
        mass: Player mass
        min_radius: Minimum radius for visibility
        
    Returns:
        Calculated player radius
    """
    if mass <= 0:
        return min_radius
    
    calculated_radius = (mass * 0.8) ** 0.5
    return max(min_radius, calculated_radius)


def check_collision(entity1: GameEntity, entity2: GameEntity) -> bool:
    """
    Check if two entities are colliding.
    
    Args:
        entity1: First entity
        entity2: Second entity
        
    Returns:
        True if entities are colliding
    """
    return entity1.is_colliding_with(entity2)


def check_collision_with_tolerance(entity1: GameEntity, entity2: GameEntity, tolerance: float = 0.0) -> bool:
    """
    Check if two entities are colliding with additional tolerance.
    
    Args:
        entity1: First entity
        entity2: Second entity
        tolerance: Additional tolerance for collision detection
        
    Returns:
        True if entities are colliding within tolerance
    """
    distance = entity1.distance_to(entity2)
    collision_distance = entity1.radius + entity2.radius + tolerance
    return distance < collision_distance


def calculate_consumption_eligibility(consumer: GameEntity, target: GameEntity, size_ratio: float = 1.1) -> bool:
    """
    Check if one entity can consume another based on size ratio.
    
    Consolidates consumption logic from both projects.
    
    Args:
        consumer: Entity attempting to consume
        target: Entity being consumed
        size_ratio: Required mass ratio for consumption
        
    Returns:
        True if consumer can consume target
    """
    return consumer.mass > target.mass * size_ratio


def calculate_movement_speed(mass: float, base_speed: float = 100.0, mass_factor: float = 0.1) -> float:
    """
    Calculate movement speed based on entity mass.
    
    Speed typically decreases with mass for balanced gameplay.
    
    Args:
        mass: Entity mass
        base_speed: Base movement speed
        mass_factor: Factor for mass-based speed reduction
        
    Returns:
        Calculated movement speed
    """
    if mass <= 0:
        return base_speed
    
    # Speed decreases with mass
    speed_reduction = mass * mass_factor
    return max(base_speed * 0.1, base_speed - speed_reduction)


def calculate_zoom_factor(total_mass: float, min_zoom: float = 0.5, max_zoom: float = 2.0) -> float:
    """
    Calculate camera zoom factor based on total player mass.
    
    Consolidates zoom calculation logic from client implementations.
    
    Args:
        total_mass: Total mass of player entities
        min_zoom: Minimum zoom level
        max_zoom: Maximum zoom level
        
    Returns:
        Calculated zoom factor
    """
    if total_mass <= 0:
        return max_zoom
    
    # Zoom out as mass increases
    zoom_factor = max_zoom - (math.log(total_mass + 1) * 0.1)
    return max(min_zoom, min(max_zoom, zoom_factor))


def calculate_view_distance(mass: float, base_distance: float = 1000.0) -> float:
    """
    Calculate view distance based on entity mass.
    
    Larger entities can see further.
    
    Args:
        mass: Entity mass
        base_distance: Base view distance
        
    Returns:
        Calculated view distance
    """
    if mass <= 0:
        return base_distance
    
    # View distance increases with mass
    distance_factor = math.sqrt(mass) * 0.1
    return base_distance + (base_distance * distance_factor)


def interpolate_position(start_pos: Vector2, end_pos: Vector2, t: float) -> Vector2:
    """
    Linear interpolation between two positions.
    
    Used for smooth movement and position updates.
    
    Args:
        start_pos: Starting position
        end_pos: Ending position
        t: Interpolation factor (0.0 to 1.0)
        
    Returns:
        Interpolated position
    """
    t = max(0.0, min(1.0, t))  # Clamp t to [0, 1]
    return start_pos + ((end_pos - start_pos) * t)


def calculate_attraction_force(entity1: GameEntity, entity2: GameEntity, force_constant: float = 1.0) -> Vector2:
    """
    Calculate gravitational-like attraction force between entities.
    
    Can be used for special game mechanics like magnetic effects.
    
    Args:
        entity1: First entity
        entity2: Second entity
        force_constant: Force scaling constant
        
    Returns:
        Force vector pointing from entity1 to entity2
    """
    direction = entity2.position - entity1.position
    distance_squared = direction.magnitude_squared
    
    if distance_squared < 0.01:  # Avoid division by zero
        return Vector2.zero()
    
    # F = G * m1 * m2 / r^2, normalized to direction
    force_magnitude = force_constant * entity1.mass * entity2.mass / distance_squared
    force_direction = direction.normalize()
    
    return force_direction * force_magnitude


def calculate_repulsion_force(entity1: GameEntity, entity2: GameEntity, force_constant: float = 100.0) -> Vector2:
    """
    Calculate repulsion force between entities.
    
    Can be used for collision avoidance or special game mechanics.
    
    Args:
        entity1: First entity
        entity2: Second entity
        force_constant: Force scaling constant
        
    Returns:
        Force vector pointing away from entity2
    """
    direction = entity1.position - entity2.position
    distance_squared = direction.magnitude_squared
    
    if distance_squared < 0.01:  # Avoid division by zero
        return Vector2(1.0, 0.0)  # Default repulsion direction
    
    # Repulsion force decreases with distance
    force_magnitude = force_constant / distance_squared
    force_direction = direction.normalize()
    
    return force_direction * force_magnitude


def find_nearest_entity(target: GameEntity, entities: List[GameEntity], max_distance: Optional[float] = None) -> Optional[GameEntity]:
    """
    Find the nearest entity to a target entity.
    
    Args:
        target: Target entity to find nearest to
        entities: List of entities to search
        max_distance: Maximum search distance (None for unlimited)
        
    Returns:
        Nearest entity or None if no entities within range
    """
    nearest_entity = None
    nearest_distance = float('inf')
    
    for entity in entities:
        if entity.entity_id == target.entity_id or not entity.is_active:
            continue
        
        distance = target.distance_to(entity)
        
        if max_distance is not None and distance > max_distance:
            continue
        
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_entity = entity
    
    return nearest_entity


def find_entities_in_radius(center: Vector2, entities: List[GameEntity], radius: float) -> List[GameEntity]:
    """
    Find all entities within a specified radius of a center point.
    
    Args:
        center: Center position for search
        entities: List of entities to search
        radius: Search radius
        
    Returns:
        List of entities within the radius
    """
    entities_in_radius = []
    radius_squared = radius * radius
    
    for entity in entities:
        if not entity.is_active:
            continue
        
        distance_squared = center.distance_squared_to(entity.position)
        if distance_squared <= radius_squared:
            entities_in_radius.append(entity)
    
    return entities_in_radius


def calculate_game_bounds_collision(position: Vector2, radius: float, bounds_min: Vector2, bounds_max: Vector2) -> Vector2:
    """
    Calculate collision with game world boundaries.
    
    Args:
        position: Entity position
        radius: Entity radius
        bounds_min: Minimum world bounds (top-left)
        bounds_max: Maximum world bounds (bottom-right)
        
    Returns:
        Corrected position that stays within bounds
    """
    corrected_x = max(bounds_min.x + radius, min(bounds_max.x - radius, position.x))
    corrected_y = max(bounds_min.y + radius, min(bounds_max.y - radius, position.y))
    
    return Vector2(corrected_x, corrected_y)


# Legacy compatibility functions (for migration from existing projects)
def get_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Legacy distance calculation function.
    
    Provides compatibility with existing distance calculations.
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_center_of_mass(entities_data: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Legacy center of mass calculation function.
    
    Provides compatibility with existing implementations.
    """
    return calculate_center_of_mass_from_data(entities_data)