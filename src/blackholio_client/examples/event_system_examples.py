"""
Event System Usage Examples for Blackholio Python Client.

Demonstrates how to use the event system for game events, connection monitoring,
and custom event handling patterns.
"""

import asyncio
import logging
from typing import Dict, Any

# Import event system components
from ..events import (
    EventManager, EventSubscriber, CallbackEventSubscriber,
    EventPublisher, GameEventPublisher, ConnectionEventPublisher,
    EventType, EventPriority,
    PlayerJoinedEvent, PlayerLeftEvent, EntityCreatedEvent,
    ConnectionEstablishedEvent, ConnectionLostEvent,
    get_global_event_manager
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameEventHandler(EventSubscriber):
    """Example game event handler that processes player and entity events."""
    
    def __init__(self):
        super().__init__("GameEventHandler")
        self.player_count = 0
        self.entity_count = 0
    
    async def handle_event(self, event) -> None:
        """Handle game events and update game state."""
        if event.get_event_name() == "PlayerJoined":
            self.player_count += 1
            player_name = event.data.get('player_name', 'Unknown')
            logger.info(f"Player joined: {player_name} (Total players: {self.player_count})")
            
        elif event.get_event_name() == "PlayerLeft":
            self.player_count = max(0, self.player_count - 1)
            player_name = event.data.get('player_name', 'Unknown')
            logger.info(f"Player left: {player_name} (Total players: {self.player_count})")
            
        elif event.get_event_name() == "EntityCreated":
            self.entity_count += 1
            entity_type = event.data.get('entity_type', 'Unknown')
            logger.info(f"Entity created: {entity_type} (Total entities: {self.entity_count})")
    
    def get_supported_event_types(self):
        return [EventType.PLAYER, EventType.ENTITY]
    
    def get_stats(self) -> Dict[str, int]:
        """Get current game statistics."""
        return {
            'player_count': self.player_count,
            'entity_count': self.entity_count
        }


class ConnectionMonitor(EventSubscriber):
    """Example connection monitor that tracks connection health."""
    
    def __init__(self):
        super().__init__("ConnectionMonitor")
        self.connection_status = "disconnected"
        self.reconnect_attempts = 0
        self.last_error = None
    
    async def handle_event(self, event) -> None:
        """Handle connection events and update status."""
        event_name = event.get_event_name()
        
        if event_name == "ConnectionEstablished":
            self.connection_status = "connected"
            self.reconnect_attempts = 0
            server_host = event.data.get('server_host', 'unknown')
            logger.info(f"✅ Connected to {server_host}")
            
        elif event_name == "ConnectionLost":
            self.connection_status = "disconnected"
            self.last_error = event.data.get('error_message')
            logger.warning(f"❌ Connection lost: {self.last_error}")
            
        elif event_name == "ConnectionReconnecting":
            self.connection_status = "reconnecting"
            self.reconnect_attempts = event.data.get('attempt_number', 0)
            delay = event.data.get('delay_seconds', 0)
            logger.info(f"🔄 Reconnecting (attempt {self.reconnect_attempts}) in {delay}s")
    
    def get_supported_event_types(self):
        return [EventType.CONNECTION]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            'status': self.connection_status,
            'reconnect_attempts': self.reconnect_attempts,
            'last_error': self.last_error
        }


async def example_basic_event_usage():
    """Demonstrate basic event system usage."""
    print("\n=== Basic Event System Usage ===")
    
    # Create event manager
    manager = EventManager(enable_metrics=True)
    
    try:
        # Create event handlers
        game_handler = GameEventHandler()
        connection_monitor = ConnectionMonitor()
        
        # Subscribe handlers to events
        manager.subscribe(game_handler, [EventType.PLAYER, EventType.ENTITY])
        manager.subscribe(connection_monitor, EventType.CONNECTION)
        
        # Create event publisher
        publisher = EventPublisher(manager, "ExampleGame")
        
        # Simulate some game events
        print("Publishing game events...")
        
        # Player joins
        player_event = PlayerJoinedEvent(
            player_data={'id': 1, 'name': 'Alice'},
            source="ExampleGame"
        )
        await publisher.publish(player_event)
        
        # Another player joins
        player_event2 = PlayerJoinedEvent(
            player_data={'id': 2, 'name': 'Bob'},
            source="ExampleGame"
        )
        await publisher.publish(player_event2)
        
        # Entity created
        entity_event = EntityCreatedEvent(
            entity_data={'id': 101, 'type': 'circle', 'owner_id': 1},
            source="ExampleGame"
        )
        await publisher.publish(entity_event)
        
        # Connection events
        conn_event = ConnectionEstablishedEvent(
            connection_info={
                'host': 'localhost',
                'port': 3000,
                'server_language': 'rust',
                'database': 'blackholio'
            },
            source="ConnectionManager"
        )
        await publisher.publish(conn_event)
        
        # Wait for all events to be processed
        await manager.wait_for_queue_empty(timeout=2.0)
        
        # Show results
        print(f"Game stats: {game_handler.get_stats()}")
        print(f"Connection status: {connection_monitor.get_status()}")
        
        # Show metrics
        metrics = manager.get_metrics()
        if metrics:
            print(f"Events published: {metrics['events_published']}")
            print(f"Events processed: {metrics['events_processed']}")
        
    finally:
        manager.shutdown()


async def example_callback_subscribers():
    """Demonstrate callback-based event subscribers."""
    print("\n=== Callback Subscriber Example ===")
    
    manager = EventManager()
    
    try:
        # Create callback functions for different event types
        async def on_player_joined(event):
            player_name = event.data.get('player_name', 'Unknown')
            print(f"🎮 Welcome {player_name} to the game!")
        
        def on_entity_created(event):  # Sync callback
            entity_type = event.data.get('entity_type', 'Unknown')
            entity_id = event.data.get('entity_id')
            print(f"⚪ New {entity_type} entity created (ID: {entity_id})")
        
        async def on_high_priority_events(event):
            print(f"🚨 High priority event: {event.get_event_name()}")
        
        # Create callback subscribers
        player_subscriber = CallbackEventSubscriber(
            callback=on_player_joined,
            event_types=EventType.PLAYER,
            name="PlayerWelcomer"
        )
        
        entity_subscriber = CallbackEventSubscriber(
            callback=on_entity_created,  # Sync callback
            event_types=EventType.ENTITY,
            name="EntityTracker"
        )
        
        # Subscribe to all high priority events
        high_priority_subscriber = CallbackEventSubscriber(
            callback=on_high_priority_events,
            event_types=[EventType.PLAYER, EventType.CONNECTION, EventType.ENTITY],
            name="HighPriorityMonitor"
        )
        
        # Register subscribers
        manager.subscribe(player_subscriber)
        manager.subscribe(entity_subscriber)
        manager.subscribe(high_priority_subscriber)
        
        # Create publisher
        publisher = EventPublisher(manager, "CallbackExample")
        
        # Publish events
        print("Publishing events with callback handlers...")
        
        await publisher.publish(PlayerJoinedEvent(
            player_data={'id': 3, 'name': 'Charlie'},
            priority=EventPriority.HIGH
        ))
        
        await publisher.publish(EntityCreatedEvent(
            entity_data={'id': 102, 'type': 'food', 'owner_id': None}
        ))
        
        # Wait for processing
        await manager.wait_for_queue_empty(timeout=1.0)
        
    finally:
        manager.shutdown()


async def example_specialized_publishers():
    """Demonstrate specialized event publishers."""
    print("\n=== Specialized Publishers Example ===")
    
    manager = EventManager()
    
    try:
        # Create callback to handle all events
        all_events = []
        
        async def event_collector(event):
            all_events.append(event)
            print(f"📨 Received: {event.get_event_name()} from {event.source}")
        
        # Subscribe to all event types
        collector = CallbackEventSubscriber(
            callback=event_collector,
            event_types=[EventType.PLAYER, EventType.ENTITY, EventType.CONNECTION],
            name="EventCollector"
        )
        manager.subscribe(collector)
        
        # Create specialized publishers
        game_publisher = GameEventPublisher(manager, "GameLogic")
        connection_publisher = ConnectionEventPublisher(manager, "NetworkLayer")
        
        print("Using specialized publishers...")
        
        # Use convenience methods from GameEventPublisher
        await game_publisher.publish_player_joined(
            player_data={'id': 4, 'name': 'Diana', 'level': 5}
        )
        
        await game_publisher.publish_entity_created(
            entity_data={'id': 103, 'type': 'obstacle', 'position': {'x': 100, 'y': 200}}
        )
        
        await game_publisher.publish_player_left(
            player_data={'id': 4, 'name': 'Diana'},
            reason="disconnect"
        )
        
        # Use convenience methods from ConnectionEventPublisher
        await connection_publisher.publish_connection_established(
            connection_info={
                'host': 'game-server.example.com',
                'port': 8080,
                'server_language': 'python'
            }
        )
        
        await connection_publisher.publish_connection_lost(
            error_info={'error_type': 'timeout', 'message': 'Server timeout'}
        )
        
        # Wait for processing
        await manager.wait_for_queue_empty(timeout=1.0)
        
        print(f"Total events processed: {len(all_events)}")
        
    finally:
        manager.shutdown()


async def example_event_filtering():
    """Demonstrate event filtering and priorities."""
    print("\n=== Event Filtering Example ===")
    
    manager = EventManager()
    
    try:
        # Create filtered event handlers
        high_priority_events = []
        player_events = []
        
        async def high_priority_handler(event):
            high_priority_events.append(event)
            print(f"🔥 High priority: {event.get_event_name()}")
        
        async def player_event_handler(event):
            player_events.append(event)
            print(f"👤 Player event: {event.get_event_name()}")
        
        # Create subscribers with different filters
        from ..events.base import EventFilter
        
        high_priority_filter = EventFilter(min_priority=EventPriority.HIGH)
        high_priority_subscriber = CallbackEventSubscriber(
            callback=high_priority_handler,
            event_types=[EventType.PLAYER, EventType.CONNECTION, EventType.ENTITY],
            name="HighPriorityFilter"
        )
        
        player_subscriber = CallbackEventSubscriber(
            callback=player_event_handler,
            event_types=EventType.PLAYER,
            name="PlayerEventFilter"
        )
        
        # Subscribe
        manager.subscribe(high_priority_subscriber)
        manager.subscribe(player_subscriber)
        
        # Add global filter to manager
        manager.add_filter(high_priority_filter)
        
        # Create publisher
        publisher = EventPublisher(manager, "FilterExample")
        
        print("Publishing events with different priorities...")
        
        # Publish events with different priorities
        await publisher.publish(PlayerJoinedEvent(
            player_data={'id': 5, 'name': 'Eve'},
            priority=EventPriority.LOW  # Will be filtered out by global filter
        ))
        
        await publisher.publish(PlayerJoinedEvent(
            player_data={'id': 6, 'name': 'Frank'},
            priority=EventPriority.HIGH  # Will pass through
        ))
        
        await publisher.publish(EntityCreatedEvent(
            entity_data={'id': 104, 'type': 'circle'},
            priority=EventPriority.CRITICAL  # Will pass through
        ))
        
        # Wait for processing
        await manager.wait_for_queue_empty(timeout=1.0)
        
        print(f"High priority events received: {len(high_priority_events)}")
        print(f"Player events received: {len(player_events)}")
        
    finally:
        manager.shutdown()


async def example_global_event_manager():
    """Demonstrate using the global event manager."""
    print("\n=== Global Event Manager Example ===")
    
    # Get global event manager (singleton)
    manager = get_global_event_manager()
    
    # Create a simple event logger
    async def event_logger(event):
        timestamp = event.timestamp
        print(f"[{timestamp:.2f}] {event.source}: {event.get_event_name()}")
    
    logger_subscriber = CallbackEventSubscriber(
        callback=event_logger,
        event_types=[EventType.PLAYER, EventType.ENTITY, EventType.CONNECTION],
        name="GlobalEventLogger"
    )
    
    # Subscribe to global manager
    manager.subscribe(logger_subscriber)
    
    # Multiple components can use the same global manager
    game_publisher = GameEventPublisher(manager, "GameComponent")
    network_publisher = ConnectionEventPublisher(manager, "NetworkComponent")
    
    print("Using global event manager...")
    
    # Publish from different components
    await game_publisher.publish_player_joined({'id': 7, 'name': 'Grace'})
    await network_publisher.publish_connection_established({
        'host': 'localhost', 'port': 3000, 'server_language': 'rust'
    })
    await game_publisher.publish_entity_created({'id': 105, 'type': 'food'})
    
    # Wait for processing
    await manager.wait_for_queue_empty(timeout=1.0)
    
    # Show manager metrics
    metrics = manager.get_metrics()
    if metrics:
        print(f"Global manager processed {metrics['events_processed']} events")


async def main():
    """Run all event system examples."""
    print("🎯 Blackholio Event System Examples")
    print("==================================")
    
    try:
        await example_basic_event_usage()
        await example_callback_subscribers()
        await example_specialized_publishers()
        await example_event_filtering()
        await example_global_event_manager()
        
        print("\n✅ All event system examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())