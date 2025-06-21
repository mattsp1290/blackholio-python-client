"""
Base event system components.

Defines core event types, priorities, and base classes for the event system.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, Optional, TypeVar, Generic, Union
import uuid


class EventType(Enum):
    """Event type enumeration for categorizing events."""
    # Connection events
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    SUBSCRIPTION = "subscription"
    
    # Game events
    GAME_STATE = "game_state"
    PLAYER = "player"
    ENTITY = "entity"
    REDUCER = "reducer"
    
    # System events
    SYSTEM = "system"
    ERROR = "error"
    DEBUG = "debug"


class EventPriority(IntEnum):
    """Event priority levels (higher numbers = higher priority)."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20
    EMERGENCY = 100


@dataclass
class Event(ABC):
    """
    Base event class for all events in the system.
    
    All events must inherit from this class and provide type information
    and relevant data for the event.
    """
    
    # Event metadata
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    event_type: EventType = field(default=EventType.SYSTEM)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    # Event context
    source: Optional[str] = field(default=None)
    correlation_id: Optional[str] = field(default=None)
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization hook for validation."""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Validate event data and configuration."""
        pass
    
    @abstractmethod
    def get_event_name(self) -> str:
        """Get the human-readable event name."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp,
            'event_type': self.event_type.value,
            'priority': self.priority.value,
            'source': self.source,
            'correlation_id': self.correlation_id,
            'event_name': self.get_event_name(),
            'data': self.data.copy()
        }
    
    def get_age_seconds(self) -> float:
        """Get the age of the event in seconds."""
        return time.time() - self.timestamp
    
    def is_expired(self, max_age_seconds: float) -> bool:
        """Check if the event has expired based on max age."""
        return self.get_age_seconds() > max_age_seconds
    
    def add_context(self, key: str, value: Any) -> None:
        """Add contextual data to the event."""
        self.data[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get contextual data from the event."""
        return self.data.get(key, default)
    
    def __str__(self) -> str:
        """String representation of the event."""
        return f"{self.get_event_name()}({self.event_id[:8]})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the event."""
        return (f"{self.__class__.__name__}("
                f"event_id='{self.event_id}', "
                f"timestamp={self.timestamp}, "
                f"event_type={self.event_type.value}, "
                f"priority={self.priority.value}, "
                f"source='{self.source}', "
                f"data_keys={list(self.data.keys())})")


# Type variable for generic event handling
EventT = TypeVar('EventT', bound=Event)


class EventFilter(Generic[EventT]):
    """
    Generic event filter for selecting specific events.
    
    Can filter by event type, priority, age, source, or custom predicates.
    """
    
    def __init__(self,
                 event_types: Optional[Union[EventType, list[EventType]]] = None,
                 min_priority: Optional[EventPriority] = None,
                 max_age_seconds: Optional[float] = None,
                 sources: Optional[Union[str, list[str]]] = None,
                 custom_filter: Optional[callable] = None):
        """
        Initialize event filter.
        
        Args:
            event_types: Event type(s) to match
            min_priority: Minimum priority level to match
            max_age_seconds: Maximum age of events to match
            sources: Source(s) to match
            custom_filter: Custom filter function taking an Event and returning bool
        """
        self.event_types = self._normalize_to_set(event_types)
        self.min_priority = min_priority
        self.max_age_seconds = max_age_seconds
        self.sources = self._normalize_to_set(sources)
        self.custom_filter = custom_filter
    
    def _normalize_to_set(self, value):
        """Convert single value or list to set."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return set(value)
        return {value}
    
    def matches(self, event: EventT) -> bool:
        """Check if event matches the filter criteria."""
        # Check event type
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check priority
        if self.min_priority and event.priority < self.min_priority:
            return False
        
        # Check age
        if self.max_age_seconds and event.is_expired(self.max_age_seconds):
            return False
        
        # Check source
        if self.sources and event.source not in self.sources:
            return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True
    
    def __call__(self, event: EventT) -> bool:
        """Allow filter to be used as a callable."""
        return self.matches(event)


class EventMetrics:
    """Event system metrics collector."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.events_published = 0
        self.events_processed = 0
        self.events_failed = 0
        self.events_by_type = {}
        self.events_by_priority = {}
        self.processing_times = []
        self.start_time = time.time()
    
    def record_published_event(self, event: Event):
        """Record an event being published."""
        self.events_published += 1
        event_type = event.event_type.value
        priority = event.priority.value
        
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        self.events_by_priority[priority] = self.events_by_priority.get(priority, 0) + 1
    
    def record_processed_event(self, event: Event, processing_time: float):
        """Record an event being processed."""
        self.events_processed += 1
        self.processing_times.append(processing_time)
        
        # Keep only last 1000 processing times
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]
    
    def record_failed_event(self, event: Event, error: Exception):
        """Record an event processing failure."""
        self.events_failed += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        uptime = time.time() - self.start_time
        
        # Calculate processing time statistics
        avg_processing_time = 0
        max_processing_time = 0
        if self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            max_processing_time = max(self.processing_times)
        
        return {
            'uptime_seconds': uptime,
            'events_published': self.events_published,
            'events_processed': self.events_processed,
            'events_failed': self.events_failed,
            'success_rate': (self.events_processed / max(1, self.events_published)) * 100,
            'events_per_second': self.events_published / max(1, uptime),
            'events_by_type': self.events_by_type.copy(),
            'events_by_priority': self.events_by_priority.copy(),
            'avg_processing_time_ms': avg_processing_time * 1000,
            'max_processing_time_ms': max_processing_time * 1000,
            'queue_length': len(self.processing_times)
        }