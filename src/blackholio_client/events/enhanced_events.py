"""
Enhanced Event System Integration

This module provides enhanced event management by using the modernized
spacetimedb-python-sdk's advanced event system while maintaining
backward compatibility with the existing blackholio-client event API.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Union

# Import from the modernized SDK
from spacetimedb_sdk.events import (
    EnhancedEventManager as SDKEventManager,
    EventType as SDKEventType,
    EventPriority as SDKEventPriority,
    Event as SDKEvent,
    EventFilter as SDKEventFilter,
    EventMetrics as SDKEventMetrics,
    AsyncEventHandler as SDKAsyncEventHandler,
    SyncEventHandler as SDKSyncEventHandler,
    EventSubscriber as SDKEventSubscriber,
    CallbackEventSubscriber as SDKCallbackEventSubscriber,
    get_event_manager as get_sdk_event_manager,
    publish_event as sdk_publish_event,
    subscribe_to_events as sdk_subscribe_to_events,
    
    # SpacetimeDB-specific events
    ConnectionEvent as SDKConnectionEvent,
    TableUpdateEvent as SDKTableUpdateEvent,
    ReducerCallEvent as SDKReducerCallEvent,
    ErrorEvent as SDKErrorEvent,
    PerformanceEvent as SDKPerformanceEvent,
    create_connection_event,
    create_table_update_event,
    create_reducer_call_event,
    create_error_event,
    create_performance_event
)

# Import existing blackholio event types for compatibility
from .base import Event, EventType, EventPriority
from .game_events import (
    GameEvent, PlayerJoinedEvent, PlayerLeftEvent,
    EntityCreatedEvent, EntityUpdatedEvent, EntityDestroyedEvent,
    GameStateChangedEvent, PlayerMovedEvent, PlayerSplitEvent
)
from .connection_events import (
    ConnectionEvent, ConnectionEstablishedEvent, ConnectionLostEvent,
    SubscriptionStateChangedEvent, TableDataReceivedEvent, ReducerExecutedEvent
)


logger = logging.getLogger(__name__)


class EnhancedEventManager:
    """
    Enhanced event manager that integrates the modernized SDK's event system
    while maintaining backward compatibility with existing blackholio-client APIs.
    """
    
    def __init__(self):
        """Initialize enhanced event manager."""
        self._sdk_manager = None
        self._compatibility_mappings = self._setup_compatibility_mappings()
        self._initialized = False
        
        logger.info("Enhanced event manager ready (SDK initialization deferred)")
    
    def _ensure_initialized(self):
        """Ensure SDK manager is initialized (lazy initialization)."""
        if not self._initialized:
            self._sdk_manager = get_sdk_event_manager()
            self._initialized = True
            logger.info("SDK event manager initialized")
    
    def _setup_compatibility_mappings(self) -> Dict[str, Any]:
        """Setup mappings between blackholio and SDK event types."""
        return {
            # Event type mappings
            'event_type_mapping': {
                EventType.CONNECTION: SDKEventType.CONNECTION,
                EventType.AUTHENTICATION: SDKEventType.AUTHENTICATION,
                EventType.SUBSCRIPTION: SDKEventType.SUBSCRIPTION,
                EventType.GAME_STATE: SDKEventType.TABLE_UPDATE,  # Map game state to table updates
                EventType.PLAYER: SDKEventType.TABLE_UPDATE,
                EventType.ENTITY: SDKEventType.TABLE_UPDATE,
                EventType.REDUCER: SDKEventType.REDUCER_CALL,
                EventType.SYSTEM: SDKEventType.SYSTEM,
                EventType.ERROR: SDKEventType.ERROR,
                EventType.DEBUG: SDKEventType.DEBUG,
            },
            
            # Priority mappings
            'priority_mapping': {
                EventPriority.LOW: SDKEventPriority.LOW,
                EventPriority.NORMAL: SDKEventPriority.NORMAL,
                EventPriority.HIGH: SDKEventPriority.HIGH,
                EventPriority.CRITICAL: SDKEventPriority.CRITICAL,
                EventPriority.EMERGENCY: SDKEventPriority.EMERGENCY,
            }
        }
    
    def _convert_event_to_sdk(self, event: Event) -> SDKEvent:
        """Convert blackholio event to SDK event."""
        if isinstance(event, ConnectionEvent):
            return create_connection_event(
                connection_id=getattr(event, 'connection_id', 'unknown'),
                state=getattr(event, 'connection_state', 'unknown'),
                host=getattr(event, 'host', None),
                error=getattr(event, 'error_message', None)
            )
        elif isinstance(event, GameEvent):
            # Convert game events to table update events
            return create_table_update_event(
                table_name=getattr(event, 'entity_type', 'game_entity'),
                operation=getattr(event, 'action', 'update'),
                row_data=getattr(event, 'data', {}),
                primary_key=getattr(event, 'entity_id', None)
            )
        else:
            # Generic conversion
            sdk_event_type = self._compatibility_mappings['event_type_mapping'].get(
                event.event_type, SDKEventType.SYSTEM
            )
            sdk_priority = self._compatibility_mappings['priority_mapping'].get(
                event.priority, SDKEventPriority.NORMAL
            )
            
            # Create a generic SDK event
            class GenericSDKEvent(SDKEvent):
                def validate(self):
                    pass
                
                def get_event_name(self):
                    return f"Legacy.{event.__class__.__name__}"
            
            return GenericSDKEvent(
                event_type=sdk_event_type,
                priority=sdk_priority,
                source=getattr(event, 'source', 'blackholio_client'),
                correlation_id=getattr(event, 'event_id', None),
                data=getattr(event, 'data', {})
            )
    
    async def publish(self, event: Event, priority: bool = False) -> bool:
        """
        Publish an event using the enhanced SDK manager.
        
        Args:
            event: Event to publish (blackholio format)
            priority: Whether to process with high priority
            
        Returns:
            True if event was published successfully
        """
        try:
            self._ensure_initialized()
            
            # Convert to SDK event
            sdk_event = self._convert_event_to_sdk(event)
            
            # Publish using SDK
            return await sdk_publish_event(sdk_event, priority)
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def subscribe(self, subscriber: Any, event_types: Optional[List[EventType]] = None) -> None:
        """
        Subscribe to events with backward compatibility.
        
        Args:
            subscriber: Event subscriber (blackholio format)
            event_types: Event types to subscribe to
        """
        self._ensure_initialized()
        
        # Convert event types to SDK format
        sdk_event_types = None
        if event_types:
            sdk_event_types = [
                self._compatibility_mappings['event_type_mapping'].get(et, SDKEventType.SYSTEM)
                for et in event_types
            ]
        
        # Create wrapper function for compatibility
        def wrapper_callback(sdk_event):
            """Wrapper to convert SDK events back to blackholio format."""
            try:
                # Convert SDK event back to blackholio format for backward compatibility
                if hasattr(subscriber, 'handle_event'):
                    # Create a compatible event object
                    compat_event = self._create_compatible_event(sdk_event)
                    return subscriber.handle_event(compat_event)
                elif callable(subscriber):
                    # Direct callback
                    compat_event = self._create_compatible_event(sdk_event)
                    return subscriber(compat_event)
            except Exception as e:
                logger.error(f"Error in event subscriber wrapper: {e}")
        
        # Subscribe using SDK
        sdk_subscribe_to_events(wrapper_callback, sdk_event_types, "blackholio_compat")
    
    def _create_compatible_event(self, sdk_event: SDKEvent) -> Event:
        """Create a blackholio-compatible event from SDK event."""
        # Create a basic compatible event
        class CompatibleEvent(Event):
            def __init__(self, sdk_event):
                super().__init__(
                    event_id=sdk_event.event_id,
                    timestamp=sdk_event.timestamp,
                    event_type=self._map_sdk_to_blackholio_type(sdk_event.event_type),
                    priority=self._map_sdk_to_blackholio_priority(sdk_event.priority),
                    source=sdk_event.source,
                    data=sdk_event.data.copy()
                )
            
            def validate(self):
                pass
            
            def get_event_name(self):
                return f"SDK.{sdk_event.get_event_name()}"
        
        return CompatibleEvent(sdk_event)
    
    def _map_sdk_to_blackholio_type(self, sdk_type: SDKEventType) -> EventType:
        """Map SDK event type to blackholio event type."""
        reverse_mapping = {v: k for k, v in self._compatibility_mappings['event_type_mapping'].items()}
        return reverse_mapping.get(sdk_type, EventType.SYSTEM)
    
    def _map_sdk_to_blackholio_priority(self, sdk_priority: SDKEventPriority) -> EventPriority:
        """Map SDK priority to blackholio priority."""
        reverse_mapping = {v: k for k, v in self._compatibility_mappings['priority_mapping'].items()}
        return reverse_mapping.get(sdk_priority, EventPriority.NORMAL)
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get event system metrics."""
        if not self._initialized:
            return None
            
        sdk_metrics = self._sdk_manager.get_metrics()
        if sdk_metrics:
            # Add compatibility info
            sdk_metrics['enhanced_sdk_powered'] = True
            sdk_metrics['blackholio_compatibility'] = True
        return sdk_metrics
    
    async def shutdown(self) -> None:
        """Shutdown the enhanced event manager."""
        if self._initialized and self._sdk_manager:
            await self._sdk_manager.shutdown()
        logger.info("Enhanced event manager shutdown complete")


# Compatibility functions
def create_enhanced_game_event(event_type: str, entity_id: str, data: Dict[str, Any]) -> SDKEvent:
    """Create an enhanced game event using SDK patterns."""
    return create_table_update_event(
        table_name="game_entities",
        operation="update",
        row_data=data,
        primary_key=entity_id
    )


def create_enhanced_connection_event(state: str, **kwargs) -> SDKEvent:
    """Create an enhanced connection event using SDK patterns."""
    return create_connection_event(
        connection_id=kwargs.get('connection_id', 'default'),
        state=state,
        **kwargs
    )


# Global enhanced event manager
_enhanced_event_manager: Optional[EnhancedEventManager] = None


def get_enhanced_event_manager() -> EnhancedEventManager:
    """Get the global enhanced event manager."""
    global _enhanced_event_manager
    
    if _enhanced_event_manager is None:
        _enhanced_event_manager = EnhancedEventManager()
    
    return _enhanced_event_manager


async def publish_enhanced_event(event: Union[Event, SDKEvent], priority: bool = False) -> bool:
    """Publish an event using the enhanced system."""
    manager = get_enhanced_event_manager()
    
    if isinstance(event, SDKEvent):
        # Direct SDK event
        return await sdk_publish_event(event, priority)
    else:
        # Blackholio event - convert and publish
        return await manager.publish(event, priority)


__all__ = [
    'EnhancedEventManager',
    'get_enhanced_event_manager',
    'publish_enhanced_event',
    'create_enhanced_game_event',
    'create_enhanced_connection_event',
    
    # Re-export SDK types for direct use
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