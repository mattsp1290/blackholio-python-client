"""
Event manager implementation.

Provides centralized event management with subscription handling, event routing,
and async processing capabilities.
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Set, Union, Coroutine
from concurrent.futures import ThreadPoolExecutor

from .base import Event, EventType, EventPriority, EventFilter, EventMetrics
from .subscriber import EventSubscriber
from .handlers import AsyncEventHandler, SyncEventHandler


logger = logging.getLogger(__name__)


class EventManager:
    """
    Centralized event management system.
    
    Handles event publishing, subscription management, and event routing
    with support for both async and sync event handlers.
    """
    
    def __init__(self,
                 max_queue_size: int = 10000,
                 max_worker_threads: int = 4,
                 enable_metrics: bool = True,
                 default_event_ttl: float = 300.0):
        """
        Initialize event manager.
        
        Args:
            max_queue_size: Maximum number of events in queue
            max_worker_threads: Maximum worker threads for sync handlers
            enable_metrics: Whether to collect event metrics
            default_event_ttl: Default event time-to-live in seconds
        """
        self.max_queue_size = max_queue_size
        self.max_worker_threads = max_worker_threads
        self.default_event_ttl = default_event_ttl
        
        # Event queue and processing
        self._event_queue = asyncio.Queue(maxsize=max_queue_size)
        self._priority_queue = deque()
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Subscriber management
        self._subscribers: Dict[EventType, Set[EventSubscriber]] = defaultdict(set)
        self._global_subscribers: Set[EventSubscriber] = set()
        self._subscriber_lock = threading.RLock()
        
        # Handler management
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._sync_handlers: Dict[EventType, List[SyncEventHandler]] = defaultdict(list)
        self._handler_lock = threading.RLock()
        
        # Thread pool for sync handlers
        self._thread_pool = ThreadPoolExecutor(max_workers=max_worker_threads)
        
        # Metrics and monitoring
        self._metrics = EventMetrics() if enable_metrics else None
        self._enable_metrics = enable_metrics
        
        # Configuration
        self._filters: List[EventFilter] = []
        self._middleware: List[Callable[[Event], Optional[Event]]] = []
        
        # Start processing
        self._start_processing()
    
    def _start_processing(self):
        """Start the event processing task."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_events())
    
    async def _process_events(self):
        """Main event processing loop."""
        logger.info("Event manager started processing events")
        
        while not self._shutdown_event.is_set():
            try:
                # Process priority events first
                if self._priority_queue:
                    event = self._priority_queue.popleft()
                    await self._handle_event(event)
                    continue
                
                # Wait for regular events with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                    await self._handle_event(event)
                    self._event_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # Brief pause on error
        
        logger.info("Event manager stopped processing events")
    
    async def _handle_event(self, event: Event):
        """Handle a single event."""
        start_time = time.time()
        
        try:
            # Apply middleware transformations
            processed_event = event
            for middleware in self._middleware:
                processed_event = middleware(processed_event)
                if processed_event is None:
                    logger.debug(f"Event {event.event_id} filtered out by middleware")
                    return
            
            # Apply filters
            for event_filter in self._filters:
                if not event_filter.matches(processed_event):
                    logger.debug(f"Event {event.event_id} filtered out by filter")
                    return
            
            # Check if event has expired
            if processed_event.is_expired(self.default_event_ttl):
                logger.warning(f"Event {event.event_id} expired, discarding")
                return
            
            # Notify subscribers and handlers
            await self._notify_subscribers(processed_event)
            await self._execute_handlers(processed_event)
            
            # Record metrics
            if self._enable_metrics and self._metrics:
                processing_time = time.time() - start_time
                self._metrics.record_processed_event(processed_event, processing_time)
                
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}", exc_info=True)
            if self._enable_metrics and self._metrics:
                self._metrics.record_failed_event(event, e)
    
    async def _notify_subscribers(self, event: Event):
        """Notify all relevant subscribers about the event."""
        # Get type-specific subscribers
        type_subscribers = set()
        with self._subscriber_lock:
            type_subscribers.update(self._subscribers.get(event.event_type, set()))
            type_subscribers.update(self._global_subscribers)
        
        # Notify each subscriber
        for subscriber in type_subscribers:
            try:
                await subscriber.handle_event(event)
            except Exception as e:
                logger.error(f"Error in subscriber {subscriber}: {e}", exc_info=True)
    
    async def _execute_handlers(self, event: Event):
        """Execute all relevant handlers for the event."""
        # Execute async handlers
        async_handlers = []
        with self._handler_lock:
            async_handlers = self._async_handlers.get(event.event_type, []).copy()
        
        for handler in async_handlers:
            try:
                await handler.handle_event(event)
            except Exception as e:
                logger.error(f"Error in async handler {handler}: {e}", exc_info=True)
        
        # Execute sync handlers in thread pool
        sync_handlers = []
        with self._handler_lock:
            sync_handlers = self._sync_handlers.get(event.event_type, []).copy()
        
        for handler in sync_handlers:
            try:
                # Submit to thread pool
                future = self._thread_pool.submit(handler.handle_event, event)
                # Don't wait for completion to avoid blocking
            except Exception as e:
                logger.error(f"Error submitting sync handler {handler}: {e}", exc_info=True)
    
    async def publish(self, event: Event, priority: bool = False) -> bool:
        """
        Publish an event to the system.
        
        Args:
            event: Event to publish
            priority: Whether to process with high priority
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        try:
            # Record metrics
            if self._enable_metrics and self._metrics:
                self._metrics.record_published_event(event)
            
            # Add to appropriate queue
            if priority or event.priority >= EventPriority.HIGH:
                self._priority_queue.append(event)
                logger.debug(f"Added priority event {event} to queue")
            else:
                # Use non-blocking put to avoid hanging if queue is full
                try:
                    self._event_queue.put_nowait(event)
                    logger.debug(f"Added event {event} to queue")
                except asyncio.QueueFull:
                    logger.warning(f"Event queue full, dropping event {event}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event}: {e}", exc_info=True)
            return False
    
    def subscribe(self,
                  subscriber: EventSubscriber,
                  event_types: Optional[Union[EventType, List[EventType]]] = None) -> bool:
        """
        Subscribe to events.
        
        Args:
            subscriber: Subscriber to register
            event_types: Specific event types to subscribe to (all if None)
            
        Returns:
            True if subscription successful, False otherwise
        """
        try:
            with self._subscriber_lock:
                if event_types is None:
                    # Subscribe to all events
                    self._global_subscribers.add(subscriber)
                    logger.debug(f"Added global subscriber {subscriber}")
                else:
                    # Subscribe to specific event types
                    if isinstance(event_types, EventType):
                        event_types = [event_types]
                    
                    for event_type in event_types:
                        self._subscribers[event_type].add(subscriber)
                        logger.debug(f"Added subscriber {subscriber} for {event_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing {subscriber}: {e}", exc_info=True)
            return False
    
    def unsubscribe(self,
                    subscriber: EventSubscriber,
                    event_types: Optional[Union[EventType, List[EventType]]] = None) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscriber: Subscriber to unregister
            event_types: Specific event types to unsubscribe from (all if None)
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        try:
            with self._subscriber_lock:
                if event_types is None:
                    # Unsubscribe from all events
                    self._global_subscribers.discard(subscriber)
                    for subscribers in self._subscribers.values():
                        subscribers.discard(subscriber)
                    logger.debug(f"Removed subscriber {subscriber} from all events")
                else:
                    # Unsubscribe from specific event types
                    if isinstance(event_types, EventType):
                        event_types = [event_types]
                    
                    for event_type in event_types:
                        self._subscribers[event_type].discard(subscriber)
                        logger.debug(f"Removed subscriber {subscriber} from {event_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing {subscriber}: {e}", exc_info=True)
            return False
    
    def add_handler(self, handler: Union[AsyncEventHandler, SyncEventHandler]) -> bool:
        """
        Add an event handler.
        
        Args:
            handler: Handler to add
            
        Returns:
            True if handler added successfully, False otherwise
        """
        try:
            with self._handler_lock:
                if isinstance(handler, AsyncEventHandler):
                    for event_type in handler.get_supported_event_types():
                        self._async_handlers[event_type].append(handler)
                        logger.debug(f"Added async handler {handler} for {event_type}")
                elif isinstance(handler, SyncEventHandler):
                    for event_type in handler.get_supported_event_types():
                        self._sync_handlers[event_type].append(handler)
                        logger.debug(f"Added sync handler {handler} for {event_type}")
                else:
                    logger.error(f"Unknown handler type: {type(handler)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding handler {handler}: {e}", exc_info=True)
            return False
    
    def remove_handler(self, handler: Union[AsyncEventHandler, SyncEventHandler]) -> bool:
        """
        Remove an event handler.
        
        Args:
            handler: Handler to remove
            
        Returns:
            True if handler removed successfully, False otherwise
        """
        try:
            with self._handler_lock:
                if isinstance(handler, AsyncEventHandler):
                    for handlers in self._async_handlers.values():
                        if handler in handlers:
                            handlers.remove(handler)
                elif isinstance(handler, SyncEventHandler):
                    for handlers in self._sync_handlers.values():
                        if handler in handlers:
                            handlers.remove(handler)
            
            logger.debug(f"Removed handler {handler}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing handler {handler}: {e}", exc_info=True)
            return False
    
    def add_filter(self, event_filter: EventFilter) -> None:
        """Add an event filter."""
        self._filters.append(event_filter)
        logger.debug(f"Added event filter {event_filter}")
    
    def remove_filter(self, event_filter: EventFilter) -> bool:
        """Remove an event filter."""
        try:
            self._filters.remove(event_filter)
            logger.debug(f"Removed event filter {event_filter}")
            return True
        except ValueError:
            return False
    
    def add_middleware(self, middleware: Callable[[Event], Optional[Event]]) -> None:
        """Add event middleware."""
        self._middleware.append(middleware)
        logger.debug(f"Added event middleware {middleware}")
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get event system metrics."""
        if not self._enable_metrics or not self._metrics:
            return None
        
        base_metrics = self._metrics.get_metrics()
        
        # Add manager-specific metrics
        with self._subscriber_lock:
            total_subscribers = len(self._global_subscribers)
            for subscribers in self._subscribers.values():
                total_subscribers += len(subscribers)
        
        with self._handler_lock:
            total_async_handlers = sum(len(handlers) for handlers in self._async_handlers.values())
            total_sync_handlers = sum(len(handlers) for handlers in self._sync_handlers.values())
        
        base_metrics.update({
            'queue_size': self._event_queue.qsize(),
            'priority_queue_size': len(self._priority_queue),
            'total_subscribers': total_subscribers,
            'total_async_handlers': total_async_handlers,
            'total_sync_handlers': total_sync_handlers,
            'active_filters': len(self._filters),
            'active_middleware': len(self._middleware),
            'is_processing': not (self._processing_task is None or self._processing_task.done())
        })
        
        return base_metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get current manager status."""
        return {
            'is_running': not self._shutdown_event.is_set(),
            'is_processing': not (self._processing_task is None or self._processing_task.done()),
            'queue_size': self._event_queue.qsize(),
            'priority_queue_size': len(self._priority_queue),
            'metrics_enabled': self._enable_metrics
        }
    
    async def wait_for_queue_empty(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for event queue to be empty.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if queue became empty, False if timeout
        """
        try:
            if timeout:
                await asyncio.wait_for(self._event_queue.join(), timeout=timeout)
            else:
                await self._event_queue.join()
            
            # Also wait for priority queue
            while self._priority_queue:
                await asyncio.sleep(0.01)
            
            return True
            
        except asyncio.TimeoutError:
            return False
    
    def shutdown(self):
        """Shutdown the event manager."""
        logger.info("Shutting down event manager")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel processing task
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        # Clear all subscribers and handlers
        with self._subscriber_lock:
            self._subscribers.clear()
            self._global_subscribers.clear()
        
        with self._handler_lock:
            self._async_handlers.clear()
            self._sync_handlers.clear()
        
        logger.info("Event manager shutdown complete")


class GlobalEventManager(EventManager):
    """
    Global singleton event manager.
    
    Provides a shared event manager instance for the entire application.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, *args, **kwargs):
        """Initialize only once."""
        if not hasattr(self, '_initialized'):
            super().__init__(*args, **kwargs)
            self._initialized = True
            logger.info("Global event manager initialized")