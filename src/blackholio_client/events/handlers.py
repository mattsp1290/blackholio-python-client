"""
Event handler implementations.

Provides event handler interfaces and implementations for processing events
in the Blackholio event system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Coroutine

from .base import Event, EventType


logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Abstract base class for event handlers.
    
    Event handlers process events and can perform actions based on event data.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize event handler.
        
        Args:
            name: Optional name for the handler
        """
        self.name = name or f"{self.__class__.__name__}_{id(self)}"
        self._active = True
    
    @abstractmethod
    def get_supported_event_types(self) -> List[EventType]:
        """
        Get list of event types this handler processes.
        
        Returns:
            List of supported event types
        """
        pass
    
    def is_active(self) -> bool:
        """Check if handler is active."""
        return self._active
    
    def activate(self) -> None:
        """Activate the handler."""
        self._active = True
        logger.debug(f"Activated handler {self.name}")
    
    def deactivate(self) -> None:
        """Deactivate the handler."""
        self._active = False
        logger.debug(f"Deactivated handler {self.name}")
    
    def __str__(self) -> str:
        """String representation of handler."""
        return f"{self.name}(active={self._active})"
    
    def __repr__(self) -> str:
        """Detailed string representation of handler."""
        return (f"{self.__class__.__name__}("
                f"name='{self.name}', "
                f"active={self._active}, "
                f"supported_types={[t.value for t in self.get_supported_event_types()]})")


class AsyncEventHandler(EventHandler):
    """
    Abstract base class for asynchronous event handlers.
    
    Async handlers can perform non-blocking operations when processing events.
    """
    
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """
        Handle an event asynchronously.
        
        Args:
            event: Event to handle
        """
        pass


class SyncEventHandler(EventHandler):
    """
    Abstract base class for synchronous event handlers.
    
    Sync handlers perform blocking operations and are executed in a thread pool.
    """
    
    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        Handle an event synchronously.
        
        Args:
            event: Event to handle
        """
        pass


class CallbackAsyncEventHandler(AsyncEventHandler):
    """
    Async event handler that delegates to callback functions.
    
    Allows easy handler registration using async callback functions.
    """
    
    def __init__(self,
                 callback: Callable[[Event], Coroutine],
                 event_types: Union[EventType, List[EventType]],
                 name: Optional[str] = None):
        """
        Initialize callback async event handler.
        
        Args:
            callback: Async function to call for events
            event_types: Event type(s) to handle
            name: Optional name for the handler
        """
        super().__init__(name)
        self.callback = callback
        
        # Normalize event types to list
        if isinstance(event_types, EventType):
            self.event_types = [event_types]
        else:
            self.event_types = list(event_types)
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by calling the callback."""
        if not self._active:
            return
        
        try:
            await self.callback(event)
        except Exception as e:
            logger.error(f"Error in callback handler {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types."""
        return self.event_types.copy()


class CallbackSyncEventHandler(SyncEventHandler):
    """
    Sync event handler that delegates to callback functions.
    
    Allows easy handler registration using sync callback functions.
    """
    
    def __init__(self,
                 callback: Callable[[Event], None],
                 event_types: Union[EventType, List[EventType]],
                 name: Optional[str] = None):
        """
        Initialize callback sync event handler.
        
        Args:
            callback: Sync function to call for events
            event_types: Event type(s) to handle
            name: Optional name for the handler
        """
        super().__init__(name)
        self.callback = callback
        
        # Normalize event types to list
        if isinstance(event_types, EventType):
            self.event_types = [event_types]
        else:
            self.event_types = list(event_types)
    
    def handle_event(self, event: Event) -> None:
        """Handle event by calling the callback."""
        if not self._active:
            return
        
        try:
            self.callback(event)
        except Exception as e:
            logger.error(f"Error in callback handler {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types."""
        return self.event_types.copy()


class LoggingEventHandler(AsyncEventHandler):
    """
    Event handler that logs events for debugging and monitoring.
    
    Useful for development and troubleshooting event flows.
    """
    
    def __init__(self,
                 event_types: Optional[Union[EventType, List[EventType]]] = None,
                 log_level: str = "INFO",
                 include_data: bool = True,
                 name: Optional[str] = None):
        """
        Initialize logging event handler.
        
        Args:
            event_types: Event types to log (all if None)
            log_level: Logging level to use
            include_data: Whether to include event data in logs
            name: Optional name for the handler
        """
        super().__init__(name or "LoggingHandler")
        
        # Normalize event types
        if event_types is None:
            self.event_types = list(EventType)
        elif isinstance(event_types, EventType):
            self.event_types = [event_types]
        else:
            self.event_types = list(event_types)
        
        self.log_level = getattr(logging, log_level.upper())
        self.include_data = include_data
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by logging it."""
        if not self._active:
            return
        
        # Format log message
        message = f"Event: {event.get_event_name()} (ID: {event.event_id[:8]})"
        
        if self.include_data and event.data:
            message += f" | Data: {event.data}"
        
        # Log at appropriate level
        self._logger.log(self.log_level, message)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types."""
        return self.event_types.copy()


class MetricsEventHandler(AsyncEventHandler):
    """
    Event handler that collects metrics about events.
    
    Useful for monitoring and performance analysis.
    """
    
    def __init__(self,
                 event_types: Optional[Union[EventType, List[EventType]]] = None,
                 name: Optional[str] = None):
        """
        Initialize metrics event handler.
        
        Args:
            event_types: Event types to track (all if None)
            name: Optional name for the handler
        """
        super().__init__(name or "MetricsHandler")
        
        # Normalize event types
        if event_types is None:
            self.event_types = list(EventType)
        elif isinstance(event_types, EventType):
            self.event_types = [event_types]
        else:
            self.event_types = list(event_types)
        
        # Metrics storage
        self._event_counts: Dict[str, int] = {}
        self._event_types_seen: Dict[EventType, int] = {}
        self._sources_seen: Dict[str, int] = {}
        self._priority_counts: Dict[int, int] = {}
        self._total_events = 0
        self._start_time = None
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by collecting metrics."""
        if not self._active:
            return
        
        import time
        
        if self._start_time is None:
            self._start_time = time.time()
        
        # Count events
        self._total_events += 1
        
        # Count by event name
        event_name = event.get_event_name()
        self._event_counts[event_name] = self._event_counts.get(event_name, 0) + 1
        
        # Count by event type
        self._event_types_seen[event.event_type] = self._event_types_seen.get(event.event_type, 0) + 1
        
        # Count by source
        if event.source:
            self._sources_seen[event.source] = self._sources_seen.get(event.source, 0) + 1
        
        # Count by priority
        priority_value = event.priority.value
        self._priority_counts[priority_value] = self._priority_counts.get(priority_value, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        import time
        
        uptime = time.time() - self._start_time if self._start_time else 0
        
        return {
            'total_events': self._total_events,
            'events_per_second': self._total_events / max(1, uptime),
            'uptime_seconds': uptime,
            'event_counts': self._event_counts.copy(),
            'event_types_seen': {t.value: count for t, count in self._event_types_seen.items()},
            'sources_seen': self._sources_seen.copy(),
            'priority_counts': self._priority_counts.copy()
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        import time
        
        self._event_counts.clear()
        self._event_types_seen.clear()
        self._sources_seen.clear()
        self._priority_counts.clear()
        self._total_events = 0
        self._start_time = time.time()
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types."""
        return self.event_types.copy()


class FilteredEventHandler(AsyncEventHandler):
    """
    Event handler wrapper that applies filtering before processing.
    
    Allows conditional event processing based on event properties.
    """
    
    def __init__(self,
                 wrapped_handler: Union[AsyncEventHandler, SyncEventHandler],
                 event_filter: Callable[[Event], bool],
                 name: Optional[str] = None):
        """
        Initialize filtered event handler.
        
        Args:
            wrapped_handler: Handler to wrap
            event_filter: Filter function to apply
            name: Optional name for the handler
        """
        super().__init__(name or f"Filtered_{wrapped_handler.name}")
        self.wrapped_handler = wrapped_handler
        self.event_filter = event_filter
        self._is_async_handler = isinstance(wrapped_handler, AsyncEventHandler)
    
    async def handle_event(self, event: Event) -> None:
        """Handle event with filtering."""
        if not self._active:
            return
        
        # Apply filter
        if not self.event_filter(event):
            return
        
        # Delegate to wrapped handler
        try:
            if self._is_async_handler:
                await self.wrapped_handler.handle_event(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.wrapped_handler.handle_event, event)
        except Exception as e:
            logger.error(f"Error in filtered handler {self.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get supported event types from wrapped handler."""
        return self.wrapped_handler.get_supported_event_types()
    
    def activate(self) -> None:
        """Activate both this handler and the wrapped one."""
        super().activate()
        self.wrapped_handler.activate()
    
    def deactivate(self) -> None:
        """Deactivate both this handler and the wrapped one."""
        super().deactivate()
        self.wrapped_handler.deactivate()


class CompositeEventHandler(AsyncEventHandler):
    """
    Event handler that manages multiple child handlers.
    
    Distributes events to all child handlers that support the event type.
    """
    
    def __init__(self, handlers: List[Union[AsyncEventHandler, SyncEventHandler]], name: Optional[str] = None):
        """
        Initialize composite event handler.
        
        Args:
            handlers: List of child handlers
            name: Optional name for the handler
        """
        super().__init__(name or "CompositeHandler")
        self.handlers = handlers.copy()
        
        # Cache supported event types
        self._supported_types = set()
        for handler in self.handlers:
            self._supported_types.update(handler.get_supported_event_types())
    
    async def handle_event(self, event: Event) -> None:
        """Handle event by distributing to all relevant handlers."""
        if not self._active:
            return
        
        # Find handlers that support this event type
        relevant_handlers = [
            h for h in self.handlers
            if h.is_active() and event.event_type in h.get_supported_event_types()
        ]
        
        # Handle event with all relevant handlers
        for handler in relevant_handlers:
            try:
                if isinstance(handler, AsyncEventHandler):
                    await handler.handle_event(event)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler.handle_event, event)
            except Exception as e:
                logger.error(f"Error in composite handler {self.name}, child {handler.name}: {e}", exc_info=True)
    
    def get_supported_event_types(self) -> List[EventType]:
        """Get all supported event types from child handlers."""
        return list(self._supported_types)
    
    def add_handler(self, handler: Union[AsyncEventHandler, SyncEventHandler]) -> None:
        """Add a child handler."""
        self.handlers.append(handler)
        self._supported_types.update(handler.get_supported_event_types())
        logger.debug(f"Added handler {handler.name} to composite {self.name}")
    
    def remove_handler(self, handler: Union[AsyncEventHandler, SyncEventHandler]) -> bool:
        """Remove a child handler."""
        try:
            self.handlers.remove(handler)
            # Recalculate supported types
            self._supported_types.clear()
            for h in self.handlers:
                self._supported_types.update(h.get_supported_event_types())
            logger.debug(f"Removed handler {handler.name} from composite {self.name}")
            return True
        except ValueError:
            return False
    
    def activate(self) -> None:
        """Activate this handler and all children."""
        super().activate()
        for handler in self.handlers:
            handler.activate()
    
    def deactivate(self) -> None:
        """Deactivate this handler and all children."""
        super().deactivate()
        for handler in self.handlers:
            handler.deactivate()