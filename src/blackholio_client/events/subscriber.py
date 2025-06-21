"""
Event subscriber implementations.

Provides event subscriber interfaces and implementations for handling events
in the Blackholio event system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Coroutine

from .base import Event, EventType


logger = logging.getLogger(__name__)


class EventSubscriber(ABC):
    """
    Abstract base class for event subscribers.
    
    Event subscribers can register with the event manager to receive
    notifications about specific events.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize event subscriber.
        
        Args:
            name: Optional name for the subscriber
        """
        self.name = name or f"{self.__class__.__name__}_{id(self)}"
        self._active = True
    
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """
        Handle an event.
        
        Args:
            event: Event to handle
        """
        pass
    
    @abstractmethod
    def get_supported_event_types(self) -> List[EventType]:
        """
        Get list of event types this subscriber handles.
        
        Returns:
            List of supported event types
        """
        pass
    
    def is_active(self) -> bool:
        """Check if subscriber is active."""
        return self._active
    
    def activate(self) -> None:
        """Activate the subscriber."""
        self._active = True
        logger.debug(f"Activated subscriber {self.name}")
    
    def deactivate(self) -> None:
        """Deactivate the subscriber."""
        self._active = False
        logger.debug(f"Deactivated subscriber {self.name}")
    
    def __str__(self) -> str:
        """String representation of subscriber."""
        return f"{self.name}(active={self._active})"
    
    def __repr__(self) -> str:
        """Detailed string representation of subscriber."""
        return (f"{self.__class__.__name__}("
                f"name='{self.name}', "
                f"active={self._active}, "
                f"supported_types={[t.value for t in self.get_supported_event_types()]})")


class CallbackEventSubscriber(EventSubscriber):
    """
    Event subscriber that delegates to callback functions.
    
    Allows easy subscription using callback functions or coroutines.
    """
    
    def __init__(self,
                 callback: Union[Callable[[Event], None], Callable[[Event], Coroutine]],
                 event_types: Union[EventType, List[EventType]],
                 name: Optional[str] = None):
        """
        Initialize callback event subscriber.
        
        Args:
            callback: Function or coroutine to call for events
            event_types: Event type(s) to handle
            name: Optional name for the subscriber
        """
        super().__init__(name)
        self.callback = callback
        
        # Normalize event types to list
        if isinstance(event_types, EventType):
            self.event_types = [event_types]
        else:
            self.event_types = list(event_types)
        
        # Check if callback is async
        self._is_async_callback = asyncio.iscoroutinefunction(callback)
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by calling the callback."""
        if not self._active:
            return
        
        try:
            if self._is_async_callback:
                await self.callback(event)
            else:
                # Run sync callback in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.callback, event)
                
        except Exception as e:
            logger.error(f"Error in callback subscriber {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types."""
        return self.event_types.copy()


class FilteredEventSubscriber(EventSubscriber):
    """
    Event subscriber with built-in filtering capabilities.
    
    Applies filters before delegating to a wrapped subscriber.
    """
    
    def __init__(self,
                 wrapped_subscriber: EventSubscriber,
                 event_filter: Optional[Callable[[Event], bool]] = None,
                 max_events_per_second: Optional[float] = None,
                 name: Optional[str] = None):
        """
        Initialize filtered event subscriber.
        
        Args:
            wrapped_subscriber: Subscriber to wrap
            event_filter: Optional filter function
            max_events_per_second: Optional rate limiting
            name: Optional name for the subscriber
        """
        super().__init__(name or f"Filtered_{wrapped_subscriber.name}")
        self.wrapped_subscriber = wrapped_subscriber
        self.event_filter = event_filter
        self.max_events_per_second = max_events_per_second
        
        # Rate limiting
        self._last_event_times = []
        self._rate_limit_window = 1.0  # 1 second window
    
    async def handle_event(self, event: Event) -> None:
        """Handle event with filtering."""
        if not self._active:
            return
        
        # Apply custom filter
        if self.event_filter and not self.event_filter(event):
            return
        
        # Apply rate limiting
        if self.max_events_per_second and not self._check_rate_limit():
            logger.debug(f"Rate limit exceeded for subscriber {self.name}")
            return
        
        # Delegate to wrapped subscriber
        await self.wrapped_subscriber.handle_event(event)
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows processing this event."""
        import time
        
        current_time = time.time()
        
        # Remove old timestamps outside the window
        cutoff_time = current_time - self._rate_limit_window
        self._last_event_times = [t for t in self._last_event_times if t > cutoff_time]
        
        # Check if we're under the limit
        if len(self._last_event_times) >= self.max_events_per_second:
            return False
        
        # Add current timestamp
        self._last_event_times.append(current_time)
        return True
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types from wrapped subscriber."""
        return self.wrapped_subscriber.get_supported_event_types()
    
    def activate(self) -> None:
        """Activate both this subscriber and the wrapped one."""
        super().activate()
        self.wrapped_subscriber.activate()
    
    def deactivate(self) -> None:
        """Deactivate both this subscriber and the wrapped one."""
        super().deactivate()
        self.wrapped_subscriber.deactivate()


class CompositeEventSubscriber(EventSubscriber):
    """
    Event subscriber that manages multiple child subscribers.
    
    Distributes events to all child subscribers that support the event type.
    """
    
    def __init__(self, subscribers: List[EventSubscriber], name: Optional[str] = None):
        """
        Initialize composite event subscriber.
        
        Args:
            subscribers: List of child subscribers
            name: Optional name for the subscriber
        """
        super().__init__(name or "CompositeSubscriber")
        self.subscribers = subscribers.copy()
        
        # Cache supported event types
        self._supported_types = set()
        for subscriber in self.subscribers:
            self._supported_types.update(subscriber.get_supported_event_types())
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by distributing to all relevant subscribers."""
        if not self._active:
            return
        
        # Find subscribers that support this event type
        relevant_subscribers = [
            s for s in self.subscribers
            if s.is_active() and event.event_type in s.get_supported_event_types()
        ]
        
        # Handle event with all relevant subscribers concurrently
        if relevant_subscribers:
            tasks = [subscriber.handle_event(event) for subscriber in relevant_subscribers]
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error in composite subscriber {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get all supported event types from child subscribers."""
        return list(self._supported_types)
    
    def add_subscriber(self, subscriber: EventSubscriber) -> None:
        """Add a child subscriber."""
        self.subscribers.append(subscriber)
        self._supported_types.update(subscriber.get_supported_event_types())
        logger.debug(f"Added subscriber {subscriber.name} to composite {self.name}")
    
    def remove_subscriber(self, subscriber: EventSubscriber) -> bool:
        """Remove a child subscriber."""
        try:
            self.subscribers.remove(subscriber)
            # Recalculate supported types
            self._supported_types.clear()
            for s in self.subscribers:
                self._supported_types.update(s.get_supported_event_types())
            logger.debug(f"Removed subscriber {subscriber.name} from composite {self.name}")
            return True
        except ValueError:
            return False
    
    def activate(self) -> None:
        """Activate this subscriber and all children."""
        super().activate()
        for subscriber in self.subscribers:
            subscriber.activate()
    
    def deactivate(self) -> None:
        """Deactivate this subscriber and all children."""
        super().deactivate()
        for subscriber in self.subscribers:
            subscriber.deactivate()


class BufferedEventSubscriber(EventSubscriber):
    """
    Event subscriber that buffers events before processing.
    
    Useful for batch processing or handling bursts of events.
    """
    
    def __init__(self,
                 wrapped_subscriber: EventSubscriber,
                 buffer_size: int = 100,
                 flush_interval: float = 1.0,
                 name: Optional[str] = None):
        """
        Initialize buffered event subscriber.
        
        Args:
            wrapped_subscriber: Subscriber to wrap
            buffer_size: Maximum events to buffer before flushing
            flush_interval: Maximum time to wait before flushing (seconds)
            name: Optional name for the subscriber
        """
        super().__init__(name or f"Buffered_{wrapped_subscriber.name}")
        self.wrapped_subscriber = wrapped_subscriber
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Buffer management
        self._buffer: List[Event] = []
        self._last_flush_time = 0
        self._flush_task: Optional[asyncio.Task] = None
        self._buffer_lock = asyncio.Lock()
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by adding to buffer."""
        if not self._active:
            return
        
        async with self._buffer_lock:
            self._buffer.append(event)
            
            # Check if we need to flush
            should_flush = (
                len(self._buffer) >= self.buffer_size or
                (self._last_flush_time > 0 and 
                 event.timestamp - self._last_flush_time >= self.flush_interval)
            )
            
            if should_flush:
                await self._flush_buffer()
    
    async def _flush_buffer(self) -> None:
        """Flush the event buffer."""
        if not self._buffer:
            return
        
        events_to_process = self._buffer.copy()
        self._buffer.clear()
        self._last_flush_time = events_to_process[-1].timestamp if events_to_process else 0
        
        # Process all buffered events
        for event in events_to_process:
            try:
                await self.wrapped_subscriber.handle_event(event)
            except Exception as e:
                logger.error(f"Error processing buffered event in {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types from wrapped subscriber."""
        return self.wrapped_subscriber.get_supported_event_types()
    
    async def flush(self) -> None:
        """Manually flush the buffer."""
        async with self._buffer_lock:
            await self._flush_buffer()
    
    def activate(self) -> None:
        """Activate both this subscriber and the wrapped one."""
        super().activate()
        self.wrapped_subscriber.activate()
    
    def deactivate(self) -> None:
        """Deactivate both this subscriber and the wrapped one."""
        super().deactivate()
        self.wrapped_subscriber.deactivate()
        
        # Flush remaining events before deactivating
        if self._buffer:
            asyncio.create_task(self.flush())