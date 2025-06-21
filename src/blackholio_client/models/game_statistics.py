"""
Game Statistics - Unified Statistics Tracking

Consolidates game statistics and metrics tracking from blackholio-agent 
and client-pygame into reusable classes for consistent performance monitoring.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .game_entities import GamePlayer, GameEntity, GameCircle


@dataclass
class PlayerStatistics:
    """
    Player-specific statistics tracking.
    
    Consolidates player metrics from both projects with comprehensive
    performance tracking for ML training and gameplay analysis.
    """
    player_id: str
    session_start_time: float = field(default_factory=time.time)
    
    # Mass and growth tracking
    initial_mass: float = 1.0
    current_mass: float = 1.0
    max_mass_achieved: float = 1.0
    total_mass_gained: float = 0.0
    total_mass_lost: float = 0.0
    
    # Score tracking
    initial_score: int = 0
    current_score: int = 0
    max_score_achieved: int = 0
    
    # Survival and activity
    survival_time: float = 0.0
    is_alive: bool = True
    death_count: int = 0
    respawn_count: int = 0
    
    # Food consumption
    food_consumed: int = 0
    total_food_value: int = 0
    largest_food_consumed: float = 0.0
    
    # Player interactions
    players_consumed: int = 0
    times_consumed: int = 0
    largest_player_consumed: float = 0.0
    
    # Movement and positioning
    total_distance_traveled: float = 0.0
    average_speed: float = 0.0
    center_of_mass_proximity: float = 0.0
    
    # Performance metrics
    actions_taken: int = 0
    average_reaction_time: float = 0.0
    efficiency_score: float = 0.0
    
    # Session tracking
    games_played: int = 1
    wins: int = 0
    losses: int = 0
    
    def update_mass(self, new_mass: float):
        """
        Update mass tracking statistics.
        
        Args:
            new_mass: New mass value
        """
        if new_mass > self.current_mass:
            self.total_mass_gained += (new_mass - self.current_mass)
        elif new_mass < self.current_mass:
            self.total_mass_lost += (self.current_mass - new_mass)
        
        self.current_mass = new_mass
        self.max_mass_achieved = max(self.max_mass_achieved, new_mass)
    
    def update_score(self, new_score: int):
        """
        Update score tracking statistics.
        
        Args:
            new_score: New score value
        """
        self.current_score = new_score
        self.max_score_achieved = max(self.max_score_achieved, new_score)
    
    def record_food_consumption(self, food_mass: float, food_value: int):
        """
        Record food consumption event.
        
        Args:
            food_mass: Mass of consumed food
            food_value: Value/points from consumed food
        """
        self.food_consumed += 1
        self.total_food_value += food_value
        self.largest_food_consumed = max(self.largest_food_consumed, food_mass)
    
    def record_player_consumption(self, consumed_player_mass: float):
        """
        Record player consumption event.
        
        Args:
            consumed_player_mass: Mass of consumed player
        """
        self.players_consumed += 1
        self.largest_player_consumed = max(self.largest_player_consumed, consumed_player_mass)
    
    def record_death(self):
        """Record player death event."""
        self.is_alive = False
        self.death_count += 1
        self.survival_time = time.time() - self.session_start_time
    
    def record_respawn(self):
        """Record player respawn event."""
        self.is_alive = True
        self.respawn_count += 1
        self.session_start_time = time.time()  # Reset session timer
    
    def update_movement(self, distance_delta: float, current_speed: float):
        """
        Update movement statistics.
        
        Args:
            distance_delta: Distance moved since last update
            current_speed: Current movement speed
        """
        self.total_distance_traveled += distance_delta
        
        # Update average speed with moving average
        if self.actions_taken > 0:
            alpha = 0.1  # Smoothing factor
            self.average_speed = (alpha * current_speed) + ((1 - alpha) * self.average_speed)
        else:
            self.average_speed = current_speed
    
    def record_action(self, reaction_time: Optional[float] = None):
        """
        Record player action.
        
        Args:
            reaction_time: Time taken to react to stimulus
        """
        self.actions_taken += 1
        
        if reaction_time is not None:
            # Update average reaction time with moving average
            if self.actions_taken > 1:
                alpha = 0.1
                self.average_reaction_time = (alpha * reaction_time) + ((1 - alpha) * self.average_reaction_time)
            else:
                self.average_reaction_time = reaction_time
    
    def calculate_efficiency_score(self) -> float:
        """
        Calculate overall efficiency score.
        
        Returns:
            Efficiency score based on multiple factors
        """
        if self.survival_time <= 0:
            return 0.0
        
        # Factors for efficiency calculation
        mass_efficiency = self.total_mass_gained / max(1.0, self.survival_time)
        food_efficiency = self.food_consumed / max(1.0, self.survival_time)
        movement_efficiency = self.total_distance_traveled / max(1.0, self.survival_time)
        
        # Weighted combination of efficiency factors
        self.efficiency_score = (
            mass_efficiency * 0.4 +
            food_efficiency * 0.3 +
            movement_efficiency * 0.2 +
            (self.players_consumed / max(1.0, self.survival_time)) * 0.1
        )
        
        return self.efficiency_score
    
    def get_current_survival_time(self) -> float:
        """Get current survival time."""
        if self.is_alive:
            return time.time() - self.session_start_time
        return self.survival_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'session_start_time': self.session_start_time,
            'initial_mass': self.initial_mass,
            'current_mass': self.current_mass,
            'max_mass_achieved': self.max_mass_achieved,
            'total_mass_gained': self.total_mass_gained,
            'total_mass_lost': self.total_mass_lost,
            'initial_score': self.initial_score,
            'current_score': self.current_score,
            'max_score_achieved': self.max_score_achieved,
            'survival_time': self.get_current_survival_time(),
            'is_alive': self.is_alive,
            'death_count': self.death_count,
            'respawn_count': self.respawn_count,
            'food_consumed': self.food_consumed,
            'total_food_value': self.total_food_value,
            'largest_food_consumed': self.largest_food_consumed,
            'players_consumed': self.players_consumed,
            'times_consumed': self.times_consumed,
            'largest_player_consumed': self.largest_player_consumed,
            'total_distance_traveled': self.total_distance_traveled,
            'average_speed': self.average_speed,
            'center_of_mass_proximity': self.center_of_mass_proximity,
            'actions_taken': self.actions_taken,
            'average_reaction_time': self.average_reaction_time,
            'efficiency_score': self.calculate_efficiency_score(),
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses
        }


@dataclass
class SessionStatistics:
    """
    Session-wide statistics tracking.
    
    Consolidates session metrics from both projects for comprehensive
    game session analysis and performance monitoring.
    """
    session_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Player tracking
    total_players: int = 0
    active_players: int = 0
    max_concurrent_players: int = 0
    player_statistics: Dict[str, PlayerStatistics] = field(default_factory=dict)
    
    # Game world statistics
    total_food_spawned: int = 0
    total_food_consumed: int = 0
    active_food_count: int = 0
    
    # Performance metrics
    total_updates: int = 0
    average_fps: float = 0.0
    average_update_time: float = 0.0
    
    # Network statistics
    total_messages_sent: int = 0
    total_messages_received: int = 0
    average_latency: float = 0.0
    
    def add_player(self, player_id: str, initial_mass: float = 1.0, initial_score: int = 0):
        """
        Add a new player to session tracking.
        
        Args:
            player_id: Unique player identifier
            initial_mass: Initial player mass
            initial_score: Initial player score
        """
        if player_id not in self.player_statistics:
            self.player_statistics[player_id] = PlayerStatistics(
                player_id=player_id,
                initial_mass=initial_mass,
                current_mass=initial_mass,
                initial_score=initial_score,
                current_score=initial_score
            )
            self.total_players += 1
        
        self.active_players += 1
        self.max_concurrent_players = max(self.max_concurrent_players, self.active_players)
    
    def remove_player(self, player_id: str):
        """
        Remove a player from active tracking.
        
        Args:
            player_id: Player identifier to remove
        """
        if player_id in self.player_statistics:
            self.active_players = max(0, self.active_players - 1)
    
    def update_player_statistics(self, player: GamePlayer):
        """
        Update statistics for a specific player.
        
        Args:
            player: GamePlayer instance with current data
        """
        if player.player_id not in self.player_statistics:
            self.add_player(player.player_id, player.mass, player.score)
        
        stats = self.player_statistics[player.player_id]
        stats.update_mass(player.mass)
        stats.update_score(player.score)
        
        # Update alive status
        stats.is_alive = player.is_alive()
    
    def record_food_spawn(self, count: int = 1):
        """
        Record food spawn events.
        
        Args:
            count: Number of food items spawned
        """
        self.total_food_spawned += count
        self.active_food_count += count
    
    def record_food_consumption(self, player_id: str, food_mass: float, food_value: int):
        """
        Record food consumption event.
        
        Args:
            player_id: ID of consuming player
            food_mass: Mass of consumed food
            food_value: Value of consumed food
        """
        self.total_food_consumed += 1
        self.active_food_count = max(0, self.active_food_count - 1)
        
        if player_id in self.player_statistics:
            self.player_statistics[player_id].record_food_consumption(food_mass, food_value)
    
    def record_player_consumption(self, consumer_id: str, consumed_id: str, consumed_mass: float):
        """
        Record player consumption event.
        
        Args:
            consumer_id: ID of consuming player
            consumed_id: ID of consumed player
            consumed_mass: Mass of consumed player
        """
        if consumer_id in self.player_statistics:
            self.player_statistics[consumer_id].record_player_consumption(consumed_mass)
        
        if consumed_id in self.player_statistics:
            self.player_statistics[consumed_id].times_consumed += 1
            self.player_statistics[consumed_id].record_death()
    
    def update_performance_metrics(self, fps: float, update_time: float):
        """
        Update performance tracking metrics.
        
        Args:
            fps: Current frames per second
            update_time: Time taken for last update
        """
        self.total_updates += 1
        
        # Update averages with moving average
        alpha = 0.1
        if self.total_updates > 1:
            self.average_fps = (alpha * fps) + ((1 - alpha) * self.average_fps)
            self.average_update_time = (alpha * update_time) + ((1 - alpha) * self.average_update_time)
        else:
            self.average_fps = fps
            self.average_update_time = update_time
    
    def update_network_metrics(self, messages_sent: int, messages_received: int, latency: float):
        """
        Update network performance metrics.
        
        Args:
            messages_sent: Number of messages sent
            messages_received: Number of messages received
            latency: Current network latency
        """
        self.total_messages_sent += messages_sent
        self.total_messages_received += messages_received
        
        # Update average latency
        if self.total_updates > 1:
            alpha = 0.1
            self.average_latency = (alpha * latency) + ((1 - alpha) * self.average_latency)
        else:
            self.average_latency = latency
    
    def get_session_duration(self) -> float:
        """Get total session duration."""
        end_time = self.end_time if self.end_time else time.time()
        return end_time - self.start_time
    
    def get_top_players(self, metric: str = 'max_mass_achieved', limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top players by a specific metric.
        
        Args:
            metric: Metric to sort by
            limit: Maximum number of players to return
            
        Returns:
            List of player statistics sorted by metric
        """
        if not self.player_statistics:
            return []
        
        # Get all players and their statistics
        players_data = []
        for player_id, stats in self.player_statistics.items():
            player_data = stats.to_dict()
            players_data.append(player_data)
        
        # Sort by specified metric
        if metric in players_data[0]:
            players_data.sort(key=lambda x: x.get(metric, 0), reverse=True)
        
        return players_data[:limit]
    
    def end_session(self):
        """Mark session as ended."""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session statistics to dictionary."""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'session_duration': self.get_session_duration(),
            'total_players': self.total_players,
            'active_players': self.active_players,
            'max_concurrent_players': self.max_concurrent_players,
            'total_food_spawned': self.total_food_spawned,
            'total_food_consumed': self.total_food_consumed,
            'active_food_count': self.active_food_count,
            'total_updates': self.total_updates,
            'average_fps': self.average_fps,
            'average_update_time': self.average_update_time,
            'total_messages_sent': self.total_messages_sent,
            'total_messages_received': self.total_messages_received,
            'average_latency': self.average_latency,
            'top_players_by_mass': self.get_top_players('max_mass_achieved'),
            'top_players_by_score': self.get_top_players('max_score_achieved'),
            'top_players_by_survival': self.get_top_players('survival_time')
        }


# Convenience functions for statistics management
def create_player_statistics(player_id: str, initial_mass: float = 1.0) -> PlayerStatistics:
    """Create new player statistics tracker."""
    return PlayerStatistics(
        player_id=player_id,
        initial_mass=initial_mass,
        current_mass=initial_mass
    )


def create_session_statistics(session_id: str) -> SessionStatistics:
    """Create new session statistics tracker."""
    return SessionStatistics(session_id=session_id)


# Legacy compatibility functions
def calculate_survival_time(start_time: float, end_time: Optional[float] = None) -> float:
    """
    Calculate survival time from timestamps.
    
    Provides compatibility with existing survival time calculations.
    """
    if end_time is None:
        end_time = time.time()
    return max(0.0, end_time - start_time)


def calculate_efficiency_ratio(mass_gained: float, time_survived: float) -> float:
    """
    Calculate efficiency ratio from mass gained and survival time.
    
    Provides compatibility with existing efficiency calculations.
    """
    if time_survived <= 0:
        return 0.0
    return mass_gained / time_survived