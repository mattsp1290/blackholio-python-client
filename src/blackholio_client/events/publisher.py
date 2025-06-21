"""
Event publisher implementations.

Provides event publishing capabilities for components to emit events
into the Blackholio event system.
"""

import asyncio
import logging
from typing import Optional, Union, List, Dict, Any
from contextlib import asynccontextmanager

from .base import Event, EventType, EventPriority
from .manager import EventManager


logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event publisher for emitting events to the event system.
    
    Provides a high-level interface for publishing events with proper
    error handling, batching, and context management.
    """
    
    def __init__(self,
                 event_manager: EventManager,
                 source_name: str,
                 default_priority: EventPriority = EventPriority.NORMAL,
                 enable_batching: bool = False,
                 batch_size: int = 10,
                 batch_timeout: float = 1.0):
        """
        Initialize event publisher.
        
        Args:
            event_manager: Event manager to publish to
            source_name: Name of the event source
            default_priority: Default priority for events
            enable_batching: Whether to enable event batching
            batch_size: Maximum events per batch
            batch_timeout: Maximum time to wait for batch completion
        """
        self.event_manager = event_manager
        self.source_name = source_name
        self.default_priority = default_priority
        self.enable_batching = enable_batching
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Batching support
        self._current_batch: List[Event] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._batch_lock = asyncio.Lock()
        
        # Statistics
        self._events_published = 0
        self._events_failed = 0
        self._batches_sent = 0
        
        logger.debug(f"Created event publisher for source '{source_name}'")
    
    async def publish(self,
                      event: Event,
                      priority: Optional[EventPriority] = None,
                      correlation_id: Optional[str] = None,
                      force_immediate: bool = False) -> bool:
        """
        Publish an event.
        
        Args:
            event: Event to publish
            priority: Override priority for this event
            correlation_id: Optional correlation ID for tracing
            force_immediate: Skip batching and publish immediately
            
        Returns:
            True if event was published successfully, False otherwise
        """
        try:
            # Set event metadata
            event.source = self.source_name
            if priority is not None:
                event.priority = priority
            elif event.priority == EventPriority.NORMAL:
                event.priority = self.default_priority
            
            if correlation_id:
                event.correlation_id = correlation_id
            
            # Decide whether to batch or publish immediately
            if (self.enable_batching and 
                not force_immediate and 
                event.priority < EventPriority.HIGH):
                return await self._add_to_batch(event)
            else:
                return await self._publish_immediately(event)
                
        except Exception as e:
            logger.error(f"Error publishing event {event}: {e}", exc_info=True)
            self._events_failed += 1
            return False
    
    async def _publish_immediately(self, event: Event) -> bool:
        """Publish event immediately."""
        success = await self.event_manager.publish(event)
        if success:
            self._events_published += 1
        else:
            self._events_failed += 1
        return success
    
    async def _add_to_batch(self, event: Event) -> bool:
        """Add event to batch for later publishing."""
        async with self._batch_lock:
            self._current_batch.append(event)
            
            # Check if batch is full
            if len(self._current_batch) >= self.batch_size:
                await self._flush_batch()
            elif self._batch_task is None:
                # Start batch timeout task
                self._batch_task = asyncio.create_task(self._batch_timeout_handler())
        
        return True
    
    async def _batch_timeout_handler(self):
        """Handle batch timeout."""
        try:
            await asyncio.sleep(self.batch_timeout)
            async with self._batch_lock:
                if self._current_batch:
                    await self._flush_batch()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in batch timeout handler: {e}", exc_info=True)
    
    async def _flush_batch(self):
        """Flush current batch of events."""
        if not self._current_batch:
            return
        
        batch_to_send = self._current_batch.copy()
        self._current_batch.clear()
        
        # Cancel timeout task
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
        self._batch_task = None
        
        # Publish all events in batch
        successful = 0
        for event in batch_to_send:
            if await self.event_manager.publish(event):
                successful += 1
        
        self._events_published += successful
        self._events_failed += len(batch_to_send) - successful
        self._batches_sent += 1
        
        logger.debug(f"Flushed batch of {len(batch_to_send)} events "
                    f"({successful} successful, {len(batch_to_send) - successful} failed)")
    
    async def flush(self) -> None:
        """Flush any pending batched events."""
        if self.enable_batching:
            async with self._batch_lock:
                await self._flush_batch()
    
    async def publish_multiple(self,
                               events: List[Event],
                               priority: Optional[EventPriority] = None,
                               correlation_id: Optional[str] = None) -> int:
        """
        Publish multiple events.
        
        Args:
            events: List of events to publish
            priority: Override priority for all events
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Number of events published successfully
        """
        successful = 0
        
        for event in events:
            if await self.publish(event, priority, correlation_id):
                successful += 1
        
        return successful
    
    @asynccontextmanager
    async def batch_context(self):
        """
        Context manager for batching events.
        
        All events published within this context will be batched
        and sent when the context exits.
        """
        old_batching = self.enable_batching
        self.enable_batching = True
        
        try:
            yield self
        finally:
            await self.flush()
            self.enable_batching = old_batching
    
    def create_event(self,
                     event_class: type,
                     event_type: EventType,
                     priority: Optional[EventPriority] = None,
                     correlation_id: Optional[str] = None,
                     **kwargs) -> Event:
        """
        Create an event with publisher metadata.
        
        Args:
            event_class: Event class to instantiate
            event_type: Event type
            priority: Event priority
            correlation_id: Optional correlation ID
            **kwargs: Additional event data
            
        Returns:
            Created event instance
        """
        event = event_class(
            event_type=event_type,
            priority=priority or self.default_priority,
            source=self.source_name,
            correlation_id=correlation_id,
            **kwargs
        )
        
        return event
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get publisher statistics."""
        total_events = self._events_published + self._events_failed
        success_rate = (self._events_published / max(1, total_events)) * 100
        
        return {
            'source_name': self.source_name,
            'events_published': self._events_published,
            'events_failed': self._events_failed,
            'total_events': total_events,
            'success_rate': success_rate,
            'batches_sent': self._batches_sent,
            'batching_enabled': self.enable_batching,
            'current_batch_size': len(self._current_batch) if self.enable_batching else 0
        }
    
    def reset_statistics(self) -> None:
        """Reset publisher statistics."""
        self._events_published = 0
        self._events_failed = 0
        self._batches_sent = 0
    
    async def shutdown(self) -> None:
        """Shutdown the publisher."""
        logger.debug(f"Shutting down event publisher for source '{self.source_name}'")
        
        # Flush any remaining batched events
        await self.flush()
        
        # Cancel batch timeout task
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
        
        logger.debug(f"Event publisher shutdown complete for source '{self.source_name}'")


class GameEventPublisher(EventPublisher):
    """
    Specialized event publisher for game events.
    
    Provides convenience methods for publishing common game events.
    """
    
    def __init__(self, event_manager: EventManager, source_name: str, **kwargs):
        """Initialize game event publisher."""
        super().__init__(event_manager, source_name, **kwargs)
    
    async def publish_player_joined(self, player_data: Dict[str, Any], **kwargs) -> bool:
        """Publish player joined event."""
        from .game_events import PlayerJoinedEvent
        
        event = PlayerJoinedEvent(
            source=self.source_name,
            player_data=player_data,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.HIGH)
    
    async def publish_player_left(self, player_data: Dict[str, Any], **kwargs) -> bool:
        """Publish player left event."""
        from .game_events import PlayerLeftEvent
        
        event = PlayerLeftEvent(
            source=self.source_name,
            player_data=player_data,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.HIGH)
    
    async def publish_entity_created(self, entity_data: Dict[str, Any], **kwargs) -> bool:
        """Publish entity created event."""
        from .game_events import EntityCreatedEvent
        
        event = EntityCreatedEvent(
            source=self.source_name,
            entity_data=entity_data,
            **kwargs
        )
        
        return await self.publish(event)
    
    async def publish_entity_updated(self, 
                                    old_entity_data: Dict[str, Any],
                                    new_entity_data: Dict[str, Any], 
                                    **kwargs) -> bool:
        """Publish entity updated event."""
        from .game_events import EntityUpdatedEvent
        
        event = EntityUpdatedEvent(
            source=self.source_name,
            old_entity_data=old_entity_data,
            new_entity_data=new_entity_data,
            **kwargs
        )
        
        return await self.publish(event)
    
    async def publish_entity_destroyed(self, entity_data: Dict[str, Any], **kwargs) -> bool:
        """Publish entity destroyed event."""
        from .game_events import EntityDestroyedEvent
        
        event = EntityDestroyedEvent(
            source=self.source_name,
            entity_data=entity_data,
            **kwargs
        )
        
        return await self.publish(event)
    
    async def publish_game_state_changed(self, 
                                        old_state: Dict[str, Any],
                                        new_state: Dict[str, Any], 
                                        **kwargs) -> bool:
        """Publish game state changed event."""
        from .game_events import GameStateChangedEvent
        
        event = GameStateChangedEvent(
            source=self.source_name,
            old_state=old_state,
            new_state=new_state,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.HIGH)


class ConnectionEventPublisher(EventPublisher):
    """
    Specialized event publisher for connection events.
    
    Provides convenience methods for publishing connection-related events.
    """
    
    def __init__(self, event_manager: EventManager, source_name: str, **kwargs):
        """Initialize connection event publisher."""
        super().__init__(event_manager, source_name, **kwargs)
    
    async def publish_connection_established(self, connection_info: Dict[str, Any], **kwargs) -> bool:
        """Publish connection established event."""
        from .connection_events import ConnectionEstablishedEvent
        
        event = ConnectionEstablishedEvent(
            source=self.source_name,
            connection_info=connection_info,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.HIGH)
    
    async def publish_connection_lost(self, error_info: Dict[str, Any], **kwargs) -> bool:
        """Publish connection lost event."""
        from .connection_events import ConnectionLostEvent
        
        event = ConnectionLostEvent(
            source=self.source_name,
            error_info=error_info,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.CRITICAL)
    
    async def publish_connection_reconnecting(self, attempt_info: Dict[str, Any], **kwargs) -> bool:
        """Publish connection reconnecting event."""
        from .connection_events import ConnectionReconnectingEvent
        
        event = ConnectionReconnectingEvent(
            source=self.source_name,
            attempt_info=attempt_info,
            **kwargs
        )
        
        return await self.publish(event, priority=EventPriority.HIGH)
    
    async def publish_subscription_state_changed(self,
                                                table_name: str,
                                                old_state: str,
                                                new_state: str,
                                                **kwargs) -> bool:
        """Publish subscription state changed event."""
        from .connection_events import SubscriptionStateChangedEvent
        
        event = SubscriptionStateChangedEvent(
            source=self.source_name,
            table_name=table_name,
            old_state=old_state,
            new_state=new_state,
            **kwargs
        )
        
        return await self.publish(event)