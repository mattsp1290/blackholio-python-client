"""
Event system utility classes and functions.

Provides utility classes for event filtering, throttling, batching,
and other common event processing patterns.
"""

import asyncio
import time
from collections import deque, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Union
from .base import Event, EventType, EventPriority, EventFilter


class EventThrottle:
    """
    Event throttling utility to limit event processing rate.
    
    Useful for preventing event floods and reducing processing overhead.
    """
    
    def __init__(self,
                 max_events_per_second: float,
                 window_size: float = 1.0,
                 drop_policy: str = "oldest"):
        """
        Initialize event throttle.
        
        Args:
            max_events_per_second: Maximum events to allow per second
            window_size: Time window size in seconds
            drop_policy: "oldest", "newest", or "priority" (how to drop events when over limit)
        """
        self.max_events_per_second = max_events_per_second
        self.window_size = window_size
        self.drop_policy = drop_policy
        
        # Tracking
        self._event_times = deque()
        self._event_queue = deque()
        self._dropped_count = 0
        
        valid_policies = ["oldest", "newest", "priority"]
        if drop_policy not in valid_policies:
            raise ValueError(f"drop_policy must be one of {valid_policies}")
    
    def should_allow(self, event: Event) -> bool:
        """
        Check if event should be allowed through the throttle.
        
        Args:
            event: Event to check
            
        Returns:
            True if event should be processed, False if throttled
        """
        current_time = time.time()
        
        # Remove old timestamps outside the window
        cutoff_time = current_time - self.window_size
        while self._event_times and self._event_times[0] < cutoff_time:
            self._event_times.popleft()
        
        # Check if we're under the limit
        if len(self._event_times) < self.max_events_per_second * self.window_size:
            self._event_times.append(current_time)
            return True
        
        # Over limit - apply drop policy
        self._dropped_count += 1
        
        if self.drop_policy == "newest":
            # Drop the new event
            return False
        elif self.drop_policy == "oldest":
            # Drop oldest and allow new
            self._event_times.popleft()
            self._event_times.append(current_time)
            return True
        elif self.drop_policy == "priority":
            # Compare priorities and drop lower priority event
            # For simplicity, we'll drop the new event if it's not high priority
            if event.priority >= EventPriority.HIGH:
                self._event_times.popleft()
                self._event_times.append(current_time)
                return True
            return False
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get throttling statistics."""
        current_rate = len(self._event_times) / self.window_size
        
        return {
            'max_events_per_second': self.max_events_per_second,
            'current_rate': current_rate,
            'events_in_window': len(self._event_times),
            'dropped_count': self._dropped_count,
            'window_size': self.window_size,
            'drop_policy': self.drop_policy
        }
    
    def reset(self) -> None:
        """Reset throttle state."""
        self._event_times.clear()
        self._event_queue.clear()
        self._dropped_count = 0


class EventBatch:
    """
    Event batching utility for collecting and processing events in groups.
    
    Useful for reducing processing overhead and implementing batch operations.
    """
    
    def __init__(self,
                 max_size: int = 100,
                 max_wait_time: float = 1.0,
                 batch_key_func: Optional[Callable[[Event], str]] = None):
        """
        Initialize event batch.
        
        Args:
            max_size: Maximum events per batch
            max_wait_time: Maximum time to wait for batch completion
            batch_key_func: Optional function to group events by key
        """
        self.max_size = max_size
        self.max_wait_time = max_wait_time
        self.batch_key_func = batch_key_func
        
        # Batching state
        self._batches: Dict[str, List[Event]] = defaultdict(list)
        self._batch_start_times: Dict[str, float] = {}
        self._total_events = 0
        self._total_batches = 0
    
    def add_event(self, event: Event) -> Optional[List[Event]]:
        """
        Add event to batch and return completed batch if ready.
        
        Args:
            event: Event to add
            
        Returns:
            List of events if batch is complete, None otherwise
        """
        # Determine batch key
        if self.batch_key_func:
            batch_key = self.batch_key_func(event)
        else:
            batch_key = "default"
        
        # Add event to batch
        batch = self._batches[batch_key]
        batch.append(event)
        self._total_events += 1
        
        # Track batch start time
        if batch_key not in self._batch_start_times:
            self._batch_start_times[batch_key] = time.time()
        
        # Check if batch is complete
        current_time = time.time()
        batch_age = current_time - self._batch_start_times[batch_key]
        
        if len(batch) >= self.max_size or batch_age >= self.max_wait_time:
            # Return completed batch
            completed_batch = batch.copy()
            self._batches[batch_key].clear()
            del self._batch_start_times[batch_key]
            self._total_batches += 1
            return completed_batch
        
        return None
    
    def get_ready_batches(self) -> Dict[str, List[Event]]:
        """
        Get all batches that are ready for processing.
        
        Returns:
            Dictionary mapping batch keys to event lists
        """
        ready_batches = {}
        current_time = time.time()
        
        for batch_key, batch in list(self._batches.items()):
            if not batch:
                continue
            
            batch_age = current_time - self._batch_start_times[batch_key]
            
            if len(batch) >= self.max_size or batch_age >= self.max_wait_time:
                ready_batches[batch_key] = batch.copy()
                self._batches[batch_key].clear()
                del self._batch_start_times[batch_key]
                self._total_batches += 1
        
        return ready_batches
    
    def flush_all(self) -> Dict[str, List[Event]]:
        """
        Flush all pending batches regardless of size or time.
        
        Returns:
            Dictionary mapping batch keys to event lists
        """
        flushed_batches = {}
        
        for batch_key, batch in self._batches.items():
            if batch:
                flushed_batches[batch_key] = batch.copy()
                self._total_batches += 1
        
        self._batches.clear()
        self._batch_start_times.clear()
        
        return flushed_batches
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get batching statistics."""
        current_events = sum(len(batch) for batch in self._batches.values())
        avg_batch_size = self._total_events / max(1, self._total_batches)
        
        return {
            'max_size': self.max_size,
            'max_wait_time': self.max_wait_time,
            'total_events': self._total_events,
            'total_batches': self._total_batches,
            'avg_batch_size': avg_batch_size,
            'current_events': current_events,
            'active_batches': len(self._batches)
        }


class EventDeduplicator:
    """
    Event deduplication utility to prevent duplicate event processing.
    
    Useful for handling network retries and preventing duplicate actions.
    """
    
    def __init__(self,
                 window_size: float = 300.0,
                 key_func: Optional[Callable[[Event], str]] = None):
        """
        Initialize event deduplicator.
        
        Args:
            window_size: Time window for deduplication in seconds
            key_func: Function to generate deduplication key from event
        """
        self.window_size = window_size
        self.key_func = key_func or self._default_key_func
        
        # Tracking
        self._seen_events: Dict[str, float] = {}
        self._duplicate_count = 0
    
    def _default_key_func(self, event: Event) -> str:
        """Default key function using event ID."""
        return event.event_id
    
    def is_duplicate(self, event: Event) -> bool:
        """
        Check if event is a duplicate.
        
        Args:
            event: Event to check
            
        Returns:
            True if event is a duplicate, False otherwise
        """
        current_time = time.time()
        event_key = self.key_func(event)
        
        # Clean up old entries
        cutoff_time = current_time - self.window_size
        expired_keys = [k for k, t in self._seen_events.items() if t < cutoff_time]
        for key in expired_keys:
            del self._seen_events[key]
        
        # Check for duplicate
        if event_key in self._seen_events:
            self._duplicate_count += 1
            return True
        
        # Record new event
        self._seen_events[event_key] = current_time
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            'window_size': self.window_size,
            'seen_events': len(self._seen_events),
            'duplicate_count': self._duplicate_count
        }
    
    def reset(self) -> None:
        """Reset deduplicator state."""
        self._seen_events.clear()
        self._duplicate_count = 0


class EventRouter:
    """
    Event routing utility for directing events to specific handlers.
    
    Useful for implementing complex event processing workflows.
    """
    
    def __init__(self):
        """Initialize event router."""
        # Routing rules: condition -> handler list
        self._routes: List[tuple] = []
        self._default_handlers: List[Callable] = []
        self._routed_count = 0
        self._unrouted_count = 0
    
    def add_route(self,
                  condition: Union[Callable[[Event], bool], EventFilter],
                  handlers: Union[Callable, List[Callable]]) -> None:
        """
        Add a routing rule.
        
        Args:
            condition: Condition function or EventFilter
            handlers: Handler function(s) to route matching events to
        """
        if isinstance(condition, EventFilter):
            condition_func = condition.matches
        else:
            condition_func = condition
        
        if not isinstance(handlers, list):
            handlers = [handlers]
        
        self._routes.append((condition_func, handlers))
    
    def add_default_handler(self, handler: Callable) -> None:
        """Add a default handler for unmatched events."""
        self._default_handlers.append(handler)
    
    async def route_event(self, event: Event) -> bool:
        """
        Route event to appropriate handlers.
        
        Args:
            event: Event to route
            
        Returns:
            True if event was routed, False otherwise
        """
        routed = False
        
        # Check routing rules
        for condition, handlers in self._routes:
            try:
                if condition(event):
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)
                            routed = True
                        except Exception as e:
                            # Log handler error but continue with other handlers
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Error in event handler {handler}: {e}", exc_info=True)
            except Exception as e:
                # Log condition error but continue with other rules
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in routing condition {condition}: {e}", exc_info=True)
        
        # If no rules matched, try default handlers
        if not routed and self._default_handlers:
            for handler in self._default_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    routed = True
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in default handler {handler}: {e}", exc_info=True)
        
        # Update statistics
        if routed:
            self._routed_count += 1
        else:
            self._unrouted_count += 1
        
        return routed
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        total_events = self._routed_count + self._unrouted_count
        route_success_rate = (self._routed_count / max(1, total_events)) * 100
        
        return {
            'total_routes': len(self._routes),
            'default_handlers': len(self._default_handlers),
            'routed_count': self._routed_count,
            'unrouted_count': self._unrouted_count,
            'total_events': total_events,
            'route_success_rate': route_success_rate
        }
    
    def clear_routes(self) -> None:
        """Clear all routing rules."""
        self._routes.clear()
        self._default_handlers.clear()


class EventAggregator:
    """
    Event aggregation utility for combining related events.
    
    Useful for reducing event volume and implementing event summarization.
    """
    
    def __init__(self,
                 aggregation_window: float = 5.0,
                 key_func: Optional[Callable[[Event], str]] = None,
                 aggregation_func: Optional[Callable[[List[Event]], Event]] = None):
        """
        Initialize event aggregator.
        
        Args:
            aggregation_window: Time window for aggregation in seconds
            key_func: Function to group events for aggregation
            aggregation_func: Function to combine events into single aggregate event
        """
        self.aggregation_window = aggregation_window
        self.key_func = key_func or self._default_key_func
        self.aggregation_func = aggregation_func or self._default_aggregation_func
        
        # Aggregation state
        self._event_groups: Dict[str, List[Event]] = defaultdict(list)
        self._group_start_times: Dict[str, float] = {}
        self._aggregated_count = 0
    
    def _default_key_func(self, event: Event) -> str:
        """Default key function using event type and source."""
        return f"{event.event_type.value}_{event.source or 'unknown'}"
    
    def _default_aggregation_func(self, events: List[Event]) -> Event:
        """Default aggregation function that creates a summary event."""
        from .base import Event, EventType, EventPriority
        
        if not events:
            raise ValueError("Cannot aggregate empty event list")
        
        # Use the most recent event as the base
        base_event = events[-1]
        
        # Create aggregated event data
        aggregated_data = {
            'event_count': len(events),
            'time_span': events[-1].timestamp - events[0].timestamp,
            'event_types': list(set(e.event_type.value for e in events)),
            'sources': list(set(e.source for e in events if e.source)),
            'priority_range': [min(e.priority.value for e in events), max(e.priority.value for e in events)]
        }
        
        # Create new aggregated event
        aggregated_event = Event(
            event_type=base_event.event_type,
            priority=max(events, key=lambda e: e.priority.value).priority,
            source=f"Aggregated_{base_event.source}",
            data=aggregated_data
        )
        
        return aggregated_event
    
    def add_event(self, event: Event) -> Optional[Event]:
        """
        Add event to aggregation and return aggregated event if ready.
        
        Args:
            event: Event to add
            
        Returns:
            Aggregated event if window is complete, None otherwise
        """
        group_key = self.key_func(event)
        
        # Add event to group
        group = self._event_groups[group_key]
        group.append(event)
        
        # Track group start time
        if group_key not in self._group_start_times:
            self._group_start_times[group_key] = time.time()
        
        # Check if aggregation window is complete
        current_time = time.time()
        window_age = current_time - self._group_start_times[group_key]
        
        if window_age >= self.aggregation_window:
            # Create aggregated event
            aggregated_event = self.aggregation_func(group.copy())
            
            # Clear group
            self._event_groups[group_key].clear()
            del self._group_start_times[group_key]
            self._aggregated_count += 1
            
            return aggregated_event
        
        return None
    
    def get_ready_aggregations(self) -> List[Event]:
        """
        Get all aggregations that are ready for processing.
        
        Returns:
            List of aggregated events
        """
        ready_aggregations = []
        current_time = time.time()
        
        for group_key, group in list(self._event_groups.items()):
            if not group:
                continue
            
            window_age = current_time - self._group_start_times[group_key]
            
            if window_age >= self.aggregation_window:
                aggregated_event = self.aggregation_func(group.copy())
                ready_aggregations.append(aggregated_event)
                
                # Clear group
                self._event_groups[group_key].clear()
                del self._group_start_times[group_key]
                self._aggregated_count += 1
        
        return ready_aggregations
    
    def flush_all(self) -> List[Event]:
        """
        Flush all pending aggregations regardless of window completion.
        
        Returns:
            List of aggregated events
        """
        flushed_aggregations = []
        
        for group_key, group in self._event_groups.items():
            if group:
                aggregated_event = self.aggregation_func(group.copy())
                flushed_aggregations.append(aggregated_event)
                self._aggregated_count += 1
        
        self._event_groups.clear()
        self._group_start_times.clear()
        
        return flushed_aggregations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        current_events = sum(len(group) for group in self._event_groups.values())
        
        return {
            'aggregation_window': self.aggregation_window,
            'aggregated_count': self._aggregated_count,
            'current_events': current_events,
            'active_groups': len(self._event_groups)
        }