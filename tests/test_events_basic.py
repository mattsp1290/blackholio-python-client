"""
Basic tests for the event system functionality.

Tests core event system components to ensure they work correctly.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock

from blackholio_client.events.base import Event, EventType, EventPriority, EventFilter
from blackholio_client.events.manager import EventManager
from blackholio_client.events.subscriber import EventSubscriber, CallbackEventSubscriber
from blackholio_client.events.publisher import EventPublisher
from blackholio_client.events.game_events import PlayerJoinedEvent, EntityCreatedEvent
from blackholio_client.events.connection_events import ConnectionEstablishedEvent


class TestEvent(Event):
    """Test event for basic testing."""
    
    def get_event_name(self) -> str:
        return "TestEvent"
    
    def validate(self) -> None:
        pass


class TestAsyncSubscriber(EventSubscriber):
    """Test async subscriber for basic testing."""
    
    def __init__(self, name="TestSubscriber"):
        super().__init__(name)
        self.events_received = []
    
    async def handle_event(self, event: Event) -> None:
        self.events_received.append(event)
    
    def get_supported_event_types(self) -> list:
        return [EventType.GAME_STATE, EventType.CONNECTION]


@pytest.mark.asyncio
class TestEventSystem:
    """Test suite for basic event system functionality."""
    
    async def test_event_creation(self):
        """Test basic event creation and validation."""
        event = TestEvent(
            event_type=EventType.GAME_STATE,
            priority=EventPriority.HIGH,
            source="test_source"
        )
        
        assert event.event_type == EventType.GAME_STATE
        assert event.priority == EventPriority.HIGH
        assert event.source == "test_source"
        assert event.get_event_name() == "TestEvent"
        assert event.event_id is not None
        assert event.timestamp > 0
    
    async def test_event_manager_creation(self):
        """Test event manager creation and basic operations."""
        manager = EventManager(max_queue_size=100, enable_metrics=True)
        
        assert manager.max_queue_size == 100
        assert manager._enable_metrics is True
        
        status = manager.get_status()
        assert status['is_running'] is True
        assert status['queue_size'] == 0
        
        # Cleanup
        manager.shutdown()
    
    async def test_event_publishing_and_subscription(self):
        """Test basic event publishing and subscription."""
        manager = EventManager(enable_metrics=True)
        
        try:
            # Create subscriber
            subscriber = TestAsyncSubscriber()
            
            # Subscribe to events
            assert manager.subscribe(subscriber, [EventType.GAME_STATE]) is True
            
            # Create and publish event
            event = TestEvent(event_type=EventType.GAME_STATE, source="test")
            assert await manager.publish(event) is True
            
            # Wait for event processing
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Check if subscriber received the event
            assert len(subscriber.events_received) == 1
            assert subscriber.events_received[0].event_id == event.event_id
            
        finally:
            manager.shutdown()
    
    async def test_callback_subscriber(self):
        """Test callback event subscriber functionality."""
        manager = EventManager()
        
        try:
            # Create callback function
            received_events = []
            
            async def event_callback(event: Event):
                received_events.append(event)
            
            # Create callback subscriber
            subscriber = CallbackEventSubscriber(
                callback=event_callback,
                event_types=EventType.CONNECTION,
                name="CallbackTest"
            )
            
            # Subscribe
            assert manager.subscribe(subscriber) is True
            
            # Publish event
            event = TestEvent(event_type=EventType.CONNECTION, source="callback_test")
            await manager.publish(event)
            
            # Wait for processing
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Check callback was called
            assert len(received_events) == 1
            assert received_events[0].event_id == event.event_id
            
        finally:
            manager.shutdown()
    
    async def test_event_publisher(self):
        """Test event publisher functionality."""
        manager = EventManager()
        
        try:
            # Create publisher
            publisher = EventPublisher(manager, "test_publisher")
            
            # Create subscriber to verify events
            subscriber = TestAsyncSubscriber()
            manager.subscribe(subscriber, [EventType.GAME_STATE])
            
            # Publish event through publisher
            event = TestEvent(event_type=EventType.GAME_STATE)
            assert await publisher.publish(event) is True
            
            # Wait for processing
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Check event was received
            assert len(subscriber.events_received) == 1
            assert subscriber.events_received[0].source == "test_publisher"
            
            # Check publisher statistics
            stats = publisher.get_statistics()
            assert stats['events_published'] == 1
            assert stats['events_failed'] == 0
            
        finally:
            manager.shutdown()
    
    async def test_game_events(self):
        """Test game-specific event types."""
        # Test PlayerJoinedEvent
        player_data = {'id': 123, 'name': 'TestPlayer'}
        player_event = PlayerJoinedEvent(player_data=player_data)
        
        assert player_event.get_event_name() == "PlayerJoined"
        assert player_event.event_type == EventType.PLAYER
        assert player_event.priority == EventPriority.HIGH
        assert player_event.data['player_id'] == 123
        assert player_event.data['player_name'] == 'TestPlayer'
        
        # Test EntityCreatedEvent
        entity_data = {'id': 456, 'type': 'circle', 'owner_id': 123}
        entity_event = EntityCreatedEvent(entity_data=entity_data)
        
        assert entity_event.get_event_name() == "EntityCreated"
        assert entity_event.event_type == EventType.ENTITY
        assert entity_event.data['entity_id'] == 456
        assert entity_event.data['entity_type'] == 'circle'
    
    async def test_connection_events(self):
        """Test connection-specific event types."""
        connection_info = {
            'host': 'localhost',
            'port': 3000,
            'server_language': 'rust',
            'database': 'test_db'
        }
        
        conn_event = ConnectionEstablishedEvent(connection_info=connection_info)
        
        assert conn_event.get_event_name() == "ConnectionEstablished"
        assert conn_event.event_type == EventType.CONNECTION
        assert conn_event.priority == EventPriority.HIGH
        assert conn_event.data['server_host'] == 'localhost'
        assert conn_event.data['server_port'] == 3000
        assert conn_event.data['server_language'] == 'rust'
    
    async def test_event_filter(self):
        """Test event filtering functionality."""
        # Create filter for high priority events
        high_priority_filter = EventFilter(min_priority=EventPriority.HIGH)
        
        # Test with high priority event
        high_event = TestEvent(priority=EventPriority.HIGH)
        assert high_priority_filter.matches(high_event) is True
        
        # Test with low priority event
        low_event = TestEvent(priority=EventPriority.LOW)
        assert high_priority_filter.matches(low_event) is False
        
        # Test type filter
        game_filter = EventFilter(event_types=EventType.GAME_STATE)
        game_event = TestEvent(event_type=EventType.GAME_STATE)
        conn_event = TestEvent(event_type=EventType.CONNECTION)
        
        assert game_filter.matches(game_event) is True
        assert game_filter.matches(conn_event) is False
    
    async def test_event_metrics(self):
        """Test event metrics collection."""
        manager = EventManager(enable_metrics=True)
        
        try:
            # Publish some events
            for i in range(5):
                event = TestEvent(
                    event_type=EventType.GAME_STATE,
                    priority=EventPriority.NORMAL,
                    source=f"source_{i}"
                )
                await manager.publish(event)
            
            # Wait for processing
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Get metrics
            metrics = manager.get_metrics()
            
            assert metrics is not None
            assert metrics['events_published'] == 5
            assert metrics['total_subscribers'] >= 0
            assert 'uptime_seconds' in metrics
            
        finally:
            manager.shutdown()
    
    async def test_event_priority_handling(self):
        """Test priority-based event handling."""
        manager = EventManager()
        
        try:
            subscriber = TestAsyncSubscriber()
            manager.subscribe(subscriber, [EventType.GAME_STATE])
            
            # Publish events with different priorities
            normal_event = TestEvent(
                event_type=EventType.GAME_STATE,
                priority=EventPriority.NORMAL,
                source="normal"
            )
            
            high_event = TestEvent(
                event_type=EventType.GAME_STATE,
                priority=EventPriority.HIGH,
                source="high"
            )
            
            # Publish normal priority first
            await manager.publish(normal_event)
            # Publish high priority (should be processed with priority)
            await manager.publish(high_event, priority=True)
            
            # Wait for processing
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Both events should be received
            assert len(subscriber.events_received) == 2
            
        finally:
            manager.shutdown()
    
    async def test_publisher_batching(self):
        """Test event publisher batching functionality."""
        manager = EventManager()
        
        try:
            publisher = EventPublisher(
                manager, 
                "batch_test",
                enable_batching=True,
                batch_size=3,
                batch_timeout=0.1
            )
            
            subscriber = TestAsyncSubscriber()
            manager.subscribe(subscriber, [EventType.GAME_STATE])
            
            # Use batch context
            async with publisher.batch_context():
                for i in range(2):
                    event = TestEvent(event_type=EventType.GAME_STATE)
                    await publisher.publish(event)
            
            # Wait for batch processing
            await asyncio.sleep(0.2)
            await manager.wait_for_queue_empty(timeout=1.0)
            
            # Events should be received
            assert len(subscriber.events_received) == 2
            
        finally:
            manager.shutdown()


if __name__ == "__main__":
    # Run basic functionality test
    async def run_basic_test():
        test_suite = TestEventSystem()
        await test_suite.test_event_creation()
        await test_suite.test_event_publishing_and_subscription()
        print("Basic event system tests passed!")
    
    asyncio.run(run_basic_test())