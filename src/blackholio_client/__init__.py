"""
Blackholio Client - Shared SpacetimeDB Python Package

A unified Python client for SpacetimeDB integration across multiple server languages.
Eliminates code duplication between blackholio-agent and client-pygame projects.

Author: Elite Engineering Team
Version: 0.1.0
License: MIT
"""

__version__ = "0.1.0"
__author__ = "Elite Engineering Team"
__email__ = "engineering@blackholio.com"
__license__ = "MIT"

# Core imports for easy access - using modernized SDK implementation
from .connection.modernized_spacetimedb_client import BlackholioClient
from .config.environment import EnvironmentConfig, get_environment_config

# Create alias for backward compatibility
get_global_config = get_environment_config
from .models.game_entities import GameEntity, GamePlayer, GameCircle, Vector2
from .auth.auth_client import AuthenticatedClient
from .auth.identity_manager import IdentityManager, Identity
from .auth.token_manager import TokenManager, AuthToken
from .reducers.reducer_client import ReducerClient, ReducerResult
from .reducers.action_formatter import ActionFormatter, Action
from .reducers.game_reducers import GameReducers
from .integration.client_generator import SpacetimeDBClientGenerator
from .integration.client_loader import ClientLoader
from .integration.server_manager import ServerManager
from .factory.client_factory import create_client, get_client_factory
from .factory.base import ClientFactory
from .exceptions.connection_errors import (
    BlackholioConnectionError,
    BlackholioConfigurationError,
    ServerConfigurationError,
    SpacetimeDBError
)

# NEW: Unified API imports
from .client import GameClient, create_game_client
from .interfaces.connection_interface import ConnectionInterface, ConnectionState
from .interfaces.auth_interface import AuthInterface
from .interfaces.subscription_interface import SubscriptionInterface, SubscriptionState
from .interfaces.reducer_interface import ReducerInterface, ReducerStatus
from .interfaces.game_client_interface import GameClientInterface

# Event System imports
from .events import (
    Event, EventType, EventPriority,
    EventManager, GlobalEventManager,
    EventSubscriber, CallbackEventSubscriber,
    EventPublisher, GameEventPublisher, ConnectionEventPublisher,
    AsyncEventHandler, SyncEventHandler,
    # Game events
    GameEvent, PlayerJoinedEvent, PlayerLeftEvent,
    EntityCreatedEvent, EntityUpdatedEvent, EntityDestroyedEvent,
    GameStateChangedEvent, PlayerMovedEvent, PlayerSplitEvent,
    # Connection events
    ConnectionEvent, ConnectionEstablishedEvent, ConnectionLostEvent,
    ConnectionReconnectingEvent, SubscriptionStateChangedEvent,
    TableDataReceivedEvent, ReducerExecutedEvent, AuthenticationEvent,
    # Utilities
    EventFilter, EventThrottle, EventBatch,
    get_global_event_manager, reset_global_event_manager
)

# Package metadata
__all__ = [
    # Legacy components (for backward compatibility)
    "BlackholioClient",
    "AuthenticatedClient",
    "EnvironmentConfig",
    "get_environment_config",
    "get_global_config", 
    "IdentityManager",
    "Identity",
    "TokenManager",
    "AuthToken",
    "ReducerClient",
    "ReducerResult",
    "ActionFormatter",
    "Action",
    "GameReducers",
    "SpacetimeDBClientGenerator",
    "ClientLoader",
    "ServerManager",
    "create_client",
    "get_client_factory",
    "ClientFactory",
    "GameEntity",
    "GamePlayer",
    "GameCircle",
    "Vector2",
    "BlackholioConnectionError",
    "BlackholioConfigurationError",
    "ServerConfigurationError",
    "SpacetimeDBError",
    
    # NEW: Unified API (recommended for new projects)
    "GameClient",
    "create_game_client",
    "ConnectionInterface",
    "ConnectionState",
    "AuthInterface",
    "SubscriptionInterface",
    "SubscriptionState",
    "ReducerInterface",
    "ReducerStatus",
    "GameClientInterface",
    
    # Event System
    "Event", "EventType", "EventPriority",
    "EventManager", "GlobalEventManager",
    "EventSubscriber", "CallbackEventSubscriber",
    "EventPublisher", "GameEventPublisher", "ConnectionEventPublisher",
    "AsyncEventHandler", "SyncEventHandler",
    # Game events
    "GameEvent", "PlayerJoinedEvent", "PlayerLeftEvent",
    "EntityCreatedEvent", "EntityUpdatedEvent", "EntityDestroyedEvent",
    "GameStateChangedEvent", "PlayerMovedEvent", "PlayerSplitEvent",
    # Connection events
    "ConnectionEvent", "ConnectionEstablishedEvent", "ConnectionLostEvent",
    "ConnectionReconnectingEvent", "SubscriptionStateChangedEvent",
    "TableDataReceivedEvent", "ReducerExecutedEvent", "AuthenticationEvent",
    # Utilities
    "EventFilter", "EventThrottle", "EventBatch",
    "get_global_event_manager", "reset_global_event_manager",
]

# Version info tuple for programmatic access
VERSION_INFO = tuple(map(int, __version__.split('.')))
