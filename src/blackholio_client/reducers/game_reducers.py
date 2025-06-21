"""
Game Reducers - Blackholio-specific Reducer Operations

Provides high-level interfaces for Blackholio game-specific reducers
with proper validation, error handling, and type safety.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union

from .reducer_client import ReducerClient, ReducerResult, TypedReducerClient
from .action_formatter import GameActionFormatter
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..models.game_entities import GamePlayer, GameCircle, Vector2, GameEntity
from ..exceptions.connection_errors import (
    SpacetimeDBError,
    DataValidationError,
    GameStateError
)


logger = logging.getLogger(__name__)


class GameReducers:
    """
    High-level interface for Blackholio game reducers.
    
    Provides type-safe, validated methods for all game operations
    with proper error handling and response processing.
    """
    
    def __init__(self, connection: SpacetimeDBConnection):
        """
        Initialize game reducers client.
        
        Args:
            connection: SpacetimeDB connection instance
        """
        self.connection = connection
        self.reducer_client = TypedReducerClient(connection)
        self.formatter = GameActionFormatter()
        
        # Game state cache
        self._player_cache: Dict[str, GamePlayer] = {}
        self._circle_cache: Dict[str, GameCircle] = {}
        self._last_state_update = 0
        
        logger.info("Game reducers client initialized")
    
    async def enter_game(self, player_name: str, identity_id: Optional[str] = None) -> GamePlayer:
        """
        Enter the game with a player.
        
        Args:
            player_name: Name for the player
            identity_id: Optional identity ID for authentication
            
        Returns:
            GamePlayer object for the created player
            
        Raises:
            GameStateError: If game entry failed
            DataValidationError: If invalid parameters
        """
        if not player_name or not player_name.strip():
            raise DataValidationError("Player name cannot be empty")
        
        args = {"player_name": player_name.strip()}
        if identity_id:
            args["identity_id"] = identity_id
        
        try:
            result = await self.reducer_client.call_with_validation(
                "enter_game",
                args,
                response_type=GamePlayer
            )
            
            if isinstance(result, dict):
                player = GamePlayer.from_dict(result)
            else:
                player = result
            
            # Cache the player
            self._player_cache[player.player_id] = player
            
            logger.info(f"Player {player_name} entered game (ID: {player.player_id})")
            return player
            
        except Exception as e:
            logger.error(f"Failed to enter game: {e}")
            raise GameStateError(f"Failed to enter game: {e}")
    
    async def leave_game(self, player_id: Optional[str] = None) -> bool:
        """
        Leave the game.
        
        Args:
            player_id: Optional player ID (uses current player if None)
            
        Returns:
            True if successfully left game
        """
        try:
            args = {}
            if player_id:
                args["player_id"] = player_id
            
            result = await self.reducer_client.call_reducer("leave_game", args)
            
            if result.is_success:
                # Remove from cache
                if player_id and player_id in self._player_cache:
                    del self._player_cache[player_id]
                
                logger.info("Successfully left game")
                return True
            else:
                logger.warning(f"Failed to leave game: {result.get_error_message()}")
                return False
                
        except Exception as e:
            logger.error(f"Error leaving game: {e}")
            return False
    
    async def update_player_input(self, direction: Vector2, player_id: Optional[str] = None) -> bool:
        """
        Update player movement input.
        
        Args:
            direction: Movement direction vector
            player_id: Optional player ID (uses current player if None)
            
        Returns:
            True if input updated successfully
        """
        try:
            # Normalize direction if needed
            if direction.magnitude > 1.0:
                direction = direction.normalize()
            
            args = {"direction": direction.to_dict()}
            if player_id:
                args["player_id"] = player_id
            
            result = await self.reducer_client.call_reducer("update_player_input", args)
            
            if result.is_success:
                logger.debug(f"Updated player input: {direction}")
                return True
            else:
                logger.warning(f"Failed to update input: {result.get_error_message()}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating player input: {e}")
            return False
    
    async def consume_circle(self, circle_id: str, player_id: Optional[str] = None) -> Optional[GameCircle]:
        """
        Consume a circle (food/powerup).
        
        Args:
            circle_id: ID of the circle to consume
            player_id: Optional player ID (uses current player if None)
            
        Returns:
            GameCircle object if consumed successfully
        """
        try:
            args = {"circle_id": circle_id}
            if player_id:
                args["player_id"] = player_id
            
            result = await self.reducer_client.call_with_validation(
                "consume_circle",
                args,
                response_type=GameCircle
            )
            
            if result:
                # Remove from cache if it was there
                if circle_id in self._circle_cache:
                    del self._circle_cache[circle_id]
                
                if isinstance(result, dict):
                    circle = GameCircle.from_dict(result)
                else:
                    circle = result
                
                logger.debug(f"Consumed circle: {circle_id}")
                return circle
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to consume circle {circle_id}: {e}")
            return None
    
    async def player_split(self, direction: Vector2, player_id: Optional[str] = None) -> List[GamePlayer]:
        """
        Split player into multiple pieces.
        
        Args:
            direction: Direction to split towards
            player_id: Optional player ID (uses current player if None)
            
        Returns:
            List of resulting GamePlayer objects
        """
        try:
            args = {"direction": direction.to_dict()}
            if player_id:
                args["player_id"] = player_id
            
            result = await self.reducer_client.call_with_validation(
                "player_split",
                args,
                response_type=GamePlayer
            )
            
            if result:
                # Handle single player or list of players
                if isinstance(result, list):
                    players = [GamePlayer.from_dict(p) if isinstance(p, dict) else p for p in result]
                else:
                    players = [GamePlayer.from_dict(result) if isinstance(result, dict) else result]
                
                # Update cache
                for player in players:
                    self._player_cache[player.player_id] = player
                
                logger.info(f"Player split into {len(players)} pieces")
                return players
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to split player: {e}")
            return []
    
    async def get_game_state(self) -> Dict[str, Any]:
        """
        Get current game state.
        
        Returns:
            Dictionary containing current game state
        """
        try:
            result = await self.reducer_client.call_reducer("get_game_state", {})
            
            if result.is_success and result.data:
                # Update caches
                if 'players' in result.data:
                    for player_data in result.data['players']:
                        player = GamePlayer.from_dict(player_data)
                        self._player_cache[player.player_id] = player
                
                if 'circles' in result.data:
                    for circle_data in result.data['circles']:
                        circle = GameCircle.from_dict(circle_data)
                        self._circle_cache[circle.circle_id] = circle
                
                self._last_state_update = asyncio.get_event_loop().time()
                return result.data
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get game state: {e}")
            return {}
    
    async def get_leaderboard(self, limit: int = 10) -> List[GamePlayer]:
        """
        Get game leaderboard.
        
        Args:
            limit: Maximum number of players to return
            
        Returns:
            List of GamePlayer objects sorted by score
        """
        try:
            result = await self.reducer_client.call_with_validation(
                "get_leaderboard",
                {"limit": limit},
                response_type=GamePlayer
            )
            
            if result:
                if isinstance(result, list):
                    players = [GamePlayer.from_dict(p) if isinstance(p, dict) else p for p in result]
                else:
                    # Single player response
                    players = [GamePlayer.from_dict(result) if isinstance(result, dict) else result]
                
                # Sort by score descending
                players.sort(key=lambda p: p.score, reverse=True)
                
                logger.debug(f"Retrieved leaderboard with {len(players)} players")
                return players
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []
    
    async def get_player_by_id(self, player_id: str, use_cache: bool = True) -> Optional[GamePlayer]:
        """
        Get player by ID.
        
        Args:
            player_id: Player ID to look up
            use_cache: Whether to use cached data
            
        Returns:
            GamePlayer object or None if not found
        """
        # Check cache first
        if use_cache and player_id in self._player_cache:
            return self._player_cache[player_id]
        
        try:
            result = await self.reducer_client.call_with_validation(
                "get_player",
                {"player_id": player_id},
                response_type=GamePlayer
            )
            
            if result:
                player = GamePlayer.from_dict(result) if isinstance(result, dict) else result
                self._player_cache[player_id] = player
                return player
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get player {player_id}: {e}")
            return None
    
    async def get_circles_in_area(self, center: Vector2, radius: float) -> List[GameCircle]:
        """
        Get circles within a specific area.
        
        Args:
            center: Center point of the area
            radius: Radius of the area
            
        Returns:
            List of GameCircle objects in the area
        """
        try:
            result = await self.reducer_client.call_with_validation(
                "get_circles_in_area",
                {
                    "center": center.to_dict(),
                    "radius": radius
                },
                response_type=GameCircle
            )
            
            if result:
                if isinstance(result, list):
                    circles = [GameCircle.from_dict(c) if isinstance(c, dict) else c for c in result]
                else:
                    circles = [GameCircle.from_dict(result) if isinstance(result, dict) else result]
                
                # Update cache
                for circle in circles:
                    self._circle_cache[circle.circle_id] = circle
                
                return circles
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get circles in area: {e}")
            return []
    
    # Cache management
    def clear_cache(self):
        """Clear all cached game data."""
        self._player_cache.clear()
        self._circle_cache.clear()
        self._last_state_update = 0
        logger.debug("Game data cache cleared")
    
    def get_cached_players(self) -> Dict[str, GamePlayer]:
        """Get all cached players."""
        return self._player_cache.copy()
    
    def get_cached_circles(self) -> Dict[str, GameCircle]:
        """Get all cached circles."""
        return self._circle_cache.copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_players': len(self._player_cache),
            'cached_circles': len(self._circle_cache),
            'last_update': self._last_state_update,
            'cache_age': asyncio.get_event_loop().time() - self._last_state_update if self._last_state_update > 0 else None
        }


# Convenience functions for game operations
async def quick_enter_game(connection: SpacetimeDBConnection, 
                          player_name: str) -> Optional[GamePlayer]:
    """Quick game entry with minimal setup."""
    game = GameReducers(connection)
    try:
        return await game.enter_game(player_name)
    except Exception as e:
        logger.error(f"Quick game entry failed: {e}")
        return None


async def quick_update_movement(connection: SpacetimeDBConnection, 
                               x: float, y: float) -> bool:
    """Quick movement update with coordinates."""
    game = GameReducers(connection)
    try:
        direction = Vector2(x, y)
        return await game.update_player_input(direction)
    except Exception as e:
        logger.error(f"Quick movement update failed: {e}")
        return False


async def get_game_leaderboard(connection: SpacetimeDBConnection, 
                              limit: int = 10) -> List[GamePlayer]:
    """Get game leaderboard with error handling."""
    game = GameReducers(connection)
    try:
        return await game.get_leaderboard(limit)
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        return []