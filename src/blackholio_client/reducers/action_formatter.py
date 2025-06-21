"""
Action Formatter - SpacetimeDB Action Message Formatting

Handles the formatting and validation of action messages for SpacetimeDB reducers
with proper serialization and type safety.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..models.game_entities import Vector2
from ..exceptions.connection_errors import DataValidationError


logger = logging.getLogger(__name__)


class ActionType(Enum):
    """SpacetimeDB action types."""
    CALL_REDUCER = "call_reducer"
    SUBSCRIPTION = "subscription"
    HEARTBEAT = "heartbeat"
    TRANSACTION = "transaction"


@dataclass
class Action:
    """
    SpacetimeDB action representation.
    
    Contains action data, metadata, and validation for SpacetimeDB operations.
    """
    action_type: ActionType
    reducer_name: str
    args: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.timestamp is None:
            self.timestamp = time.time()
        
        if not self.reducer_name:
            raise ValueError("Reducer name is required")
        
        # Validate action type
        if isinstance(self.action_type, str):
            try:
                self.action_type = ActionType(self.action_type)
            except ValueError:
                raise ValueError(f"Invalid action type: {self.action_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for serialization."""
        data = {
            'type': self.action_type.value,
            'reducer': self.reducer_name,
            'args': self._serialize_args(self.args),
            'timestamp': self.timestamp
        }
        
        if self.request_id:
            data['request_id'] = self.request_id
        
        if self.metadata:
            data['metadata'] = self.metadata
        
        return data
    
    def _serialize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize arguments for SpacetimeDB."""
        serialized = {}
        
        for key, value in args.items():
            if isinstance(value, Vector2):
                serialized[key] = value.to_dict()
            elif hasattr(value, 'to_dict'):
                serialized[key] = value.to_dict()
            elif isinstance(value, (list, tuple)):
                serialized[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return serialized
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create Action from dictionary."""
        return cls(
            action_type=ActionType(data['type']),
            reducer_name=data['reducer'],
            args=data.get('args', {}),
            timestamp=data.get('timestamp'),
            request_id=data.get('request_id'),
            metadata=data.get('metadata', {})
        )


class ActionFormatter:
    """
    Formats and validates SpacetimeDB actions.
    
    Provides utilities for creating properly formatted action messages
    with validation and type safety for SpacetimeDB operations.
    """
    
    def __init__(self, protocol_version: str = "v1.json.spacetimedb"):
        """
        Initialize action formatter.
        
        Args:
            protocol_version: SpacetimeDB protocol version
        """
        self.protocol_version = protocol_version
        self._request_counter = 0
        
        logger.debug(f"Action formatter initialized with protocol: {protocol_version}")
    
    def format_reducer_call(self, reducer_name: str, args: Dict[str, Any], 
                          request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a reducer call action.
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            request_id: Optional request ID for tracking
            
        Returns:
            Formatted action message
        """
        if request_id is None:
            request_id = self._generate_request_id()
        
        action = Action(
            action_type=ActionType.CALL_REDUCER,
            reducer_name=reducer_name,
            args=args,
            request_id=request_id
        )
        
        return self._wrap_action(action)
    
    def format_subscription(self, table_names: List[str], 
                          request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a subscription action.
        
        Args:
            table_names: List of table names to subscribe to
            request_id: Optional request ID for tracking
            
        Returns:
            Formatted subscription message
        """
        if request_id is None:
            request_id = self._generate_request_id()
        
        action = Action(
            action_type=ActionType.SUBSCRIPTION,
            reducer_name="subscribe",
            args={"tables": table_names},
            request_id=request_id
        )
        
        return self._wrap_action(action)
    
    def format_heartbeat(self) -> Dict[str, Any]:
        """
        Format a heartbeat action.
        
        Returns:
            Formatted heartbeat message
        """
        action = Action(
            action_type=ActionType.HEARTBEAT,
            reducer_name="heartbeat",
            args={}
        )
        
        return self._wrap_action(action)
    
    def format_game_action(self, action_name: str, **kwargs) -> Dict[str, Any]:
        """
        Format a game-specific action.
        
        Args:
            action_name: Name of the game action
            **kwargs: Action parameters
            
        Returns:
            Formatted action message
        """
        return self.format_reducer_call(f"game_{action_name}", kwargs)
    
    def _wrap_action(self, action: Action) -> Dict[str, Any]:
        """Wrap action in protocol envelope."""
        message = {
            "protocol": self.protocol_version,
            "timestamp": action.timestamp or time.time(),
            "action": action.to_dict()
        }
        
        if action.request_id:
            message["request_id"] = action.request_id
        
        return message
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_counter += 1
        return f"action_{self._request_counter}_{int(time.time() * 1000)}"
    
    def validate_action(self, action: Union[Action, Dict[str, Any]]) -> bool:
        """
        Validate action format and data.
        
        Args:
            action: Action to validate
            
        Returns:
            True if valid
            
        Raises:
            DataValidationError: If action is invalid
        """
        try:
            if isinstance(action, dict):
                action = Action.from_dict(action.get('action', action))
            
            # Validate required fields
            if not action.reducer_name:
                raise DataValidationError("Reducer name is required")
            
            if not isinstance(action.args, dict):
                raise DataValidationError("Action args must be a dictionary")
            
            # Validate action type
            if not isinstance(action.action_type, ActionType):
                raise DataValidationError("Invalid action type")
            
            # Validate timestamp
            if action.timestamp and not isinstance(action.timestamp, (int, float)):
                raise DataValidationError("Timestamp must be a number")
            
            return True
            
        except Exception as e:
            logger.error(f"Action validation failed: {e}")
            raise DataValidationError(f"Action validation failed: {e}")


# Game-specific action formatters
class GameActionFormatter(ActionFormatter):
    """
    Game-specific action formatter for Blackholio operations.
    
    Provides convenient methods for common game actions with proper
    validation and formatting for the Blackholio game.
    """
    
    def format_enter_game(self, player_name: str, identity_id: Optional[str] = None) -> Dict[str, Any]:
        """Format enter game action."""
        args = {"player_name": player_name}
        if identity_id:
            args["identity_id"] = identity_id
        
        return self.format_reducer_call("enter_game", args)
    
    def format_update_player_input(self, direction: Vector2) -> Dict[str, Any]:
        """Format player input update action."""
        return self.format_reducer_call("update_player_input", {
            "direction": direction.to_dict()
        })
    
    def format_player_move(self, position: Vector2, velocity: Vector2) -> Dict[str, Any]:
        """Format player movement action."""
        return self.format_reducer_call("player_move", {
            "position": position.to_dict(),
            "velocity": velocity.to_dict()
        })
    
    def format_consume_circle(self, circle_id: str) -> Dict[str, Any]:
        """Format circle consumption action."""
        return self.format_reducer_call("consume_circle", {
            "circle_id": circle_id
        })
    
    def format_player_split(self, direction: Vector2) -> Dict[str, Any]:
        """Format player split action."""
        return self.format_reducer_call("player_split", {
            "direction": direction.to_dict()
        })
    
    def format_leave_game(self) -> Dict[str, Any]:
        """Format leave game action."""
        return self.format_reducer_call("leave_game", {})
    
    def format_get_leaderboard(self, limit: int = 10) -> Dict[str, Any]:
        """Format get leaderboard action."""
        return self.format_reducer_call("get_leaderboard", {
            "limit": limit
        })
    
    def format_get_game_state(self) -> Dict[str, Any]:
        """Format get game state action."""
        return self.format_reducer_call("get_game_state", {})


# Utility functions for common action patterns
def create_enter_game_action(player_name: str, identity_id: Optional[str] = None) -> Dict[str, Any]:
    """Create enter game action with validation."""
    formatter = GameActionFormatter()
    return formatter.format_enter_game(player_name, identity_id)


def create_movement_action(direction: Vector2) -> Dict[str, Any]:
    """Create player movement action with validation."""
    formatter = GameActionFormatter()
    return formatter.format_update_player_input(direction)


def create_subscription_action(tables: List[str]) -> Dict[str, Any]:
    """Create table subscription action."""
    formatter = ActionFormatter()
    return formatter.format_subscription(tables)


def validate_game_action(action: Union[Action, Dict[str, Any]]) -> bool:
    """Validate game action with game-specific rules."""
    formatter = GameActionFormatter()
    return formatter.validate_action(action)