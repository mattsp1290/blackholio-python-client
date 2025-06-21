"""
Event system for the Blackholio Python Client.

Provides a unified event-driven architecture for handling game events, server messages,
and state changes across all SpacetimeDB server implementations.

Enhanced with modernized SDK event capabilities while maintaining backward compatibility.
"""

from .base import Event, EventType, EventPriority
from .manager import EventManager, GlobalEventManager
from .subscriber import EventSubscriber, CallbackEventSubscriber
from .publisher import EventPublisher, GameEventPublisher, ConnectionEventPublisher
from .handlers import AsyncEventHandler, SyncEventHandler
from .game_events import (
    GameEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
    EntityCreatedEvent,
    EntityUpdatedEvent,
    EntityDestroyedEvent,
    GameStateChangedEvent,
    PlayerMovedEvent,
    PlayerSplitEvent,
    GameStatsUpdatedEvent
)
from .connection_events import (
    ConnectionEvent,
    ConnectionEstablishedEvent,
    ConnectionLostEvent,
    ConnectionReconnectingEvent,
    ConnectionFailedEvent,
    SubscriptionStateChangedEvent,
    TableDataReceivedEvent,
    ReducerExecutedEvent,
    AuthenticationEvent
)
from .utils import EventFilter, EventThrottle, EventBatch

# Enhanced event system (SDK-powered)
from .enhanced_events import (
    EnhancedEventManager,
    get_enhanced_event_manager, 
    publish_enhanced_event,
    create_enhanced_game_event,
    create_enhanced_connection_event,
    SDKEventType,
    SDKEventPriority,
    SDKEvent,
    SDKConnectionEvent,
    SDKTableUpdateEvent,
    SDKReducerCallEvent,
    SDKErrorEvent,
    SDKPerformanceEvent,
    create_connection_event,
    create_table_update_event,
    create_reducer_call_event,
    create_error_event,
    create_performance_event
)

# Global event manager instance
_global_event_manager = None

def get_global_event_manager() -> EventManager:
    """Get the global event manager instance."""
    global _global_event_manager
    if _global_event_manager is None:
        _global_event_manager = GlobalEventManager()
    return _global_event_manager

def reset_global_event_manager() -> None:
    """Reset the global event manager (primarily for testing)."""
    global _global_event_manager
    if _global_event_manager is not None:
        _global_event_manager.shutdown()
        _global_event_manager = None

__all__ = [
    # Core classes
    'Event', 'EventType', 'EventPriority',
    'EventManager', 'GlobalEventManager',
    'EventSubscriber', 'CallbackEventSubscriber',
    'EventPublisher',
    'AsyncEventHandler', 'SyncEventHandler',
    
    # Game events
    'GameEvent',
    'PlayerJoinedEvent', 'PlayerLeftEvent',
    'EntityCreatedEvent', 'EntityUpdatedEvent', 'EntityDestroyedEvent',
    'GameStateChangedEvent', 'PlayerMovedEvent', 'PlayerSplitEvent',
    'GameStatsUpdatedEvent',
    
    # Connection events
    'ConnectionEvent',
    'ConnectionEstablishedEvent', 'ConnectionLostEvent',
    'ConnectionReconnectingEvent', 'ConnectionFailedEvent',
    'SubscriptionStateChangedEvent', 'TableDataReceivedEvent',
    'ReducerExecutedEvent', 'AuthenticationEvent',
    
    # Utilities
    'EventFilter', 'EventThrottle', 'EventBatch',
    
    # Global functions
    'get_global_event_manager', 'reset_global_event_manager',
    
    # Enhanced event system (SDK-powered)
    'EnhancedEventManager',
    'get_enhanced_event_manager', 
    'publish_enhanced_event',
    'create_enhanced_game_event',
    'create_enhanced_connection_event',
    
    # SDK event types for direct use
    'SDKEventType',
    'SDKEventPriority', 
    'SDKEvent',
    'SDKConnectionEvent',
    'SDKTableUpdateEvent',
    'SDKReducerCallEvent',
    'SDKErrorEvent',
    'SDKPerformanceEvent',
    'create_connection_event',
    'create_table_update_event',
    'create_reducer_call_event',
    'create_error_event',
    'create_performance_event'
]