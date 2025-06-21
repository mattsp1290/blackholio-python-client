"""
Migration examples for transitioning from existing blackholio implementations.

This module demonstrates how to migrate from the existing blackholio-agent
and client-pygame implementations to the unified client library.
"""

import asyncio
import logging
from typing import Dict, Any, List

from ..client import create_game_client
from ..models.game_entities import Vector2, GameEntity, GamePlayer


logger = logging.getLogger(__name__)


class LegacyBlackholioAgentMigration:
    """
    Demonstrates migrating from blackholio-agent to the unified client.
    
    This class shows the before/after patterns for common operations
    that the ML agent would perform.
    """
    
    def __init__(self):
        self.client = None
    
    async def migrate_connection_pattern(self):
        """
        Show how to migrate connection code from blackholio-agent.
        """
        print("\n=== Migrating blackholio-agent Connection Pattern ===")
        
        # BEFORE (blackholio-agent pattern):
        print("\n❌ OLD blackholio-agent pattern:")
        print("""
        # Old blackholio-agent code
        from blackholio_connection_v112 import BlackholioConnectionV112
        
        connection = BlackholioConnectionV112(
            host="localhost:3000", 
            db_identity="blackholio"
        )
        await connection.connect()
        await connection._subscribe_to_tables()
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        from blackholio_client import create_game_client
        
        client = create_game_client(
            host="localhost:3000",
            database="blackholio",
            server_language="rust"  # Now configurable!
        )
        await client.join_game("MLAgent")  # Handles connection + subscription + game entry
        """)
        
        # Demonstrate the new pattern
        self.client = create_game_client(
            host="localhost:3000",
            database="blackholio",
            server_language="rust"
        )
        
        try:
            success = await self.client.join_game("MLAgentMigrationTest")
            if success:
                print("✅ Migration successful - client connected and in game!")
            else:
                print("❌ Migration test failed - server may not be running")
        except Exception as e:
            print(f"❌ Migration error: {e}")
    
    async def migrate_game_state_access(self):
        """
        Show how to migrate game state access patterns.
        """
        print("\n=== Migrating Game State Access ===")
        
        if not self.client or not self.client.is_in_game():
            print("⚠️ Skipping - not connected to game")
            return
        
        # BEFORE (blackholio-agent pattern):
        print("\n❌ OLD blackholio-agent pattern:")
        print("""
        # Old way - direct access to connection internals
        local_player_entities = []
        for entity_id, entity in connection._entities.items():
            if entity.get('player_id') == connection._local_player_id:
                local_player_entities.append(entity)
        
        center_of_mass = calculate_center_of_mass(local_player_entities)
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        # New way - clean API methods
        local_player = client.get_local_player()
        local_entities = client.get_local_player_entities()
        all_entities = client.get_all_entities()
        
        # Built-in utilities available
        from blackholio_client.models.physics import calculate_center_of_mass
        center_of_mass = calculate_center_of_mass(local_entities)
        """)
        
        # Demonstrate the new pattern
        local_player = self.client.get_local_player()
        local_entities = self.client.get_local_player_entities()
        all_entities = self.client.get_all_entities()
        
        print(f"✅ Local player: {local_player}")
        print(f"✅ Local entities count: {len(local_entities)}")
        print(f"✅ Total entities count: {len(all_entities)}")
    
    async def migrate_ml_training_loop(self):
        """
        Show how to migrate the ML training loop pattern.
        """
        print("\n=== Migrating ML Training Loop ===")
        
        if not self.client or not self.client.is_in_game():
            print("⚠️ Skipping - not connected to game")
            return
        
        # BEFORE (blackholio-agent pattern):
        print("\n❌ OLD blackholio-agent pattern:")
        print("""
        # Old training loop - complex state management
        while training:
            # Manual state extraction
            game_state = {
                'entities': connection._entities,
                'local_player': connection._local_player_id,
                'circles': connection._circles
            }
            
            # Manual action calculation
            action = ml_model.predict(extract_features(game_state))
            
            # Manual action execution
            await connection.call_reducer("update_player_input", action)
            
            await asyncio.sleep(0.1)
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        # New training loop - clean and simple
        while training:
            # Easy state access with built-in utilities
            game_state = client.get_client_state()
            local_entities = client.get_local_player_entities()
            nearby_entities = client.get_entities_near(player_position, search_radius)
            
            # ML model prediction (unchanged)
            action = ml_model.predict(extract_features(local_entities, nearby_entities))
            
            # Clean action execution
            await client.move_player(Vector2(action['x'], action['y']))
            if action.get('split', False):
                await client.player_split()
            
            await asyncio.sleep(0.1)
        """)
        
        # Demonstrate simplified training loop (simulation)
        print("🤖 Simulating ML training loop...")
        for step in range(3):
            # Get game state (much simpler now)
            local_entities = self.client.get_local_player_entities()
            all_entities = self.client.get_all_entities()
            
            # Simulate ML model decision
            import random
            action = {
                'x': random.uniform(-1.0, 1.0),
                'y': random.uniform(-1.0, 1.0),
                'split': random.random() < 0.1
            }
            
            # Execute action (much cleaner)
            await self.client.move_player(Vector2(action['x'], action['y']))
            if action['split']:
                await self.client.player_split()
            
            print(f"  Step {step + 1}: moved to ({action['x']:.2f}, {action['y']:.2f})")
            await asyncio.sleep(0.5)
        
        print("✅ ML training loop simulation completed!")
    
    async def migrate_error_handling(self):
        """
        Show how to migrate error handling patterns.
        """
        print("\n=== Migrating Error Handling ===")
        
        # BEFORE (blackholio-agent pattern):
        print("\n❌ OLD blackholio-agent pattern:")
        print("""
        # Old way - manual error handling
        try:
            await connection.connect()
        except websockets.exceptions.ConnectionClosed:
            # Manual reconnection logic
            await asyncio.sleep(1)
            await connection.connect()
        except Exception as e:
            # Manual error categorization
            if "404" in str(e):
                print("Server not found")
            elif "timeout" in str(e):
                print("Connection timeout")
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        # New way - automatic error handling with callbacks
        def on_error(error_msg):
            print(f"Handled error: {error_msg}")
        
        def on_connection_changed(state):
            if state == ConnectionState.FAILED:
                # Auto-reconnect handles retries
                pass
        
        client.on_error(on_error)
        client.on_connection_state_changed(on_connection_changed)
        client.enable_auto_reconnect(max_attempts=10)
        """)
        
        # Demonstrate new error handling
        def error_handler(error_msg: str):
            print(f"✅ Error handled gracefully: {error_msg}")
        
        self.client.on_error(error_handler)
        
        # Test error handling
        try:
            # This might fail, but error handler will catch it
            await self.client.move_player(Vector2(999.0, 999.0))
            print("✅ Action succeeded or error handled gracefully")
        except Exception as e:
            print(f"✅ Exception caught and handled: {e}")
    
    async def cleanup(self):
        """Clean up the migration test."""
        if self.client:
            await self.client.shutdown()


class LegacyPygameClientMigration:
    """
    Demonstrates migrating from client-pygame to the unified client.
    
    This class shows the before/after patterns for common operations
    that the pygame client would perform.
    """
    
    def __init__(self):
        self.client = None
    
    async def migrate_pygame_integration(self):
        """
        Show how to integrate the unified client with pygame.
        """
        print("\n=== Migrating pygame Client Integration ===")
        
        # BEFORE (client-pygame pattern):
        print("\n❌ OLD client-pygame pattern:")
        print("""
        # Old pygame client - tight coupling
        class GameClient:
            def __init__(self):
                self.connection = SpacetimeConnection("ws://localhost:3000")
                self.renderer = GameRenderer()
                self.input_handler = InputHandler()
            
            def update(self):
                # Manual state synchronization
                self.renderer.entities = self.connection._entities
                self.renderer.players = self.connection._players
                
                # Manual input processing
                input_data = self.input_handler.get_input()
                if input_data:
                    self.connection.send_input(input_data)
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        # New pygame client - clean separation
        class GameClient:
            def __init__(self):
                self.client = create_game_client(
                    host="localhost:3000",
                    database="blackholio",
                    server_language="rust"
                )
                self.renderer = GameRenderer()
                self.input_handler = InputHandler()
                
                # Set up event handlers
                self.client.on_entity_created(self.renderer.add_entity)
                self.client.on_entity_updated(self.renderer.update_entity)
                self.client.on_entity_destroyed(self.renderer.remove_entity)
            
            async def update(self):
                # Clean state access
                entities = self.client.get_all_entities()
                players = self.client.get_all_players()
                self.renderer.render(entities, players)
                
                # Clean input handling
                input_vector = self.input_handler.get_movement_vector()
                if input_vector:
                    await self.client.move_player(input_vector)
        """)
        
        # Demonstrate the integration
        self.client = create_game_client(
            host="localhost:3000",
            database="blackholio",
            server_language="rust"
        )
        
        # Set up pygame-style event handlers
        def on_entity_created(entity: GameEntity):
            print(f"🎮 Pygame would render new entity: {entity.entity_id}")
        
        def on_entity_updated(old_entity: GameEntity, new_entity: GameEntity):
            print(f"🎮 Pygame would update entity: {new_entity.entity_id}")
        
        self.client.on_entity_created(on_entity_created)
        self.client.on_entity_updated(on_entity_updated)
        
        try:
            success = await self.client.join_game("PygamePlayer")
            if success:
                print("✅ Pygame integration successful!")
                
                # Simulate pygame game loop
                await self.simulate_pygame_loop()
            else:
                print("❌ Pygame integration test failed - server may not be running")
        except Exception as e:
            print(f"❌ Pygame migration error: {e}")
    
    async def simulate_pygame_loop(self):
        """
        Simulate a pygame game loop with the unified client.
        """
        print("\n🎮 Simulating pygame game loop...")
        
        # Simulate 5 game loop iterations
        for frame in range(5):
            print(f"  Frame {frame + 1}:")
            
            # Simulate pygame input (mouse movement, keyboard)
            import random
            mouse_x = random.uniform(-1.0, 1.0)
            mouse_y = random.uniform(-1.0, 1.0)
            spacebar_pressed = random.random() < 0.2
            
            # Convert pygame input to game actions
            movement = Vector2(mouse_x, mouse_y).normalized()
            await self.client.move_player(movement)
            print(f"    Moved player: {movement}")
            
            if spacebar_pressed:
                await self.client.player_split()
                print(f"    Player split!")
            
            # Get game state for rendering (pygame would use this)
            entities = self.client.get_all_entities()
            players = self.client.get_all_players()
            local_player = self.client.get_local_player()
            
            print(f"    Rendering {len(entities)} entities, {len(players)} players")
            
            # Simulate frame delay
            await asyncio.sleep(0.1)
        
        print("✅ Pygame game loop simulation completed!")
    
    async def migrate_rendering_pattern(self):
        """
        Show how to migrate rendering patterns.
        """
        print("\n=== Migrating Rendering Patterns ===")
        
        if not self.client or not self.client.is_in_game():
            print("⚠️ Skipping - not connected to game")
            return
        
        # BEFORE (client-pygame pattern):
        print("\n❌ OLD client-pygame pattern:")
        print("""
        # Old rendering - direct access to connection data
        def render_game(screen, connection):
            # Manual data extraction and conversion
            for entity_id, entity_data in connection._entities.items():
                pos = entity_data['position']
                radius = calculate_radius(entity_data['mass'])
                pygame.draw.circle(screen, color, (pos['x'], pos['y']), radius)
            
            # Manual player identification
            if connection._local_player_id:
                player_entities = [e for e in connection._entities.values() 
                                 if e.get('player_id') == connection._local_player_id]
                # Render player entities differently
        """)
        
        # AFTER (unified client pattern):
        print("\n✅ NEW unified client pattern:")
        print("""
        # New rendering - clean data access with proper types
        def render_game(screen, client):
            # Clean entity access
            entities = client.get_all_entities()
            for entity in entities.values():
                pos = entity.position  # Proper Vector2 object
                radius = entity.calculated_radius()  # Built-in method
                pygame.draw.circle(screen, entity.color, (pos.x, pos.y), radius)
            
            # Easy local player highlighting
            local_entities = client.get_local_player_entities()
            for entity in local_entities:
                # Render with highlight
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, 
                                 (entity.position.x, entity.position.y), 
                                 entity.calculated_radius() + 2)
        """)
        
        # Demonstrate clean data access
        entities = self.client.get_all_entities()
        local_entities = self.client.get_local_player_entities()
        
        print(f"✅ Clean entity access: {len(entities)} total entities")
        print(f"✅ Local entities: {len(local_entities)} entities")
        
        for entity in list(entities.values())[:3]:  # Show first 3
            print(f"  Entity {entity.entity_id}: pos={entity.position}, mass={entity.mass}")
    
    async def cleanup(self):
        """Clean up the migration test."""
        if self.client:
            await self.client.shutdown()


async def environment_variable_migration():
    """
    Demonstrate migrating to environment variable configuration.
    """
    print("\n=== Migrating to Environment Variable Configuration ===")
    
    # BEFORE (hardcoded configuration):
    print("\n❌ OLD pattern - hardcoded configuration:")
    print("""
    # Old way - hardcoded server details
    connection = BlackholioConnectionV112(
        host="localhost:3000",  # Hardcoded
        db_identity="blackholio"  # Hardcoded
    )
    """)
    
    # AFTER (environment variable configuration):
    print("\n✅ NEW pattern - environment variable configuration:")
    print("""
    # New way - environment variable driven
    import os
    
    # Set environment variables (or use Docker environment)
    os.environ['SERVER_LANGUAGE'] = 'rust'  # rust, python, csharp, go
    os.environ['SERVER_IP'] = 'localhost'
    os.environ['SERVER_PORT'] = '3000'
    
    # Client automatically uses environment configuration
    client = create_game_client(
        host=f"{os.getenv('SERVER_IP')}:{os.getenv('SERVER_PORT')}",
        database="blackholio",
        server_language=os.getenv('SERVER_LANGUAGE', 'rust')
    )
    """)
    
    # Demonstrate environment-based configuration
    import os
    
    # Set up environment variables
    os.environ['SERVER_LANGUAGE'] = 'rust'
    os.environ['SERVER_IP'] = 'localhost'
    os.environ['SERVER_PORT'] = '3000'
    
    # Create client using environment configuration
    client = create_game_client(
        host=f"{os.getenv('SERVER_IP')}:{os.getenv('SERVER_PORT')}",
        database="blackholio",
        server_language=os.getenv('SERVER_LANGUAGE', 'rust')
    )
    
    print("✅ Environment-based configuration:")
    print(f"  Server Language: {os.getenv('SERVER_LANGUAGE')}")
    print(f"  Server IP: {os.getenv('SERVER_IP')}")
    print(f"  Server Port: {os.getenv('SERVER_PORT')}")
    print(f"  Connection Info: {client.get_connection_info()}")
    
    await client.shutdown()


async def performance_comparison():
    """
    Demonstrate performance improvements with the unified client.
    """
    print("\n=== Performance Comparison ===")
    
    print("\n📊 Performance improvements with unified client:")
    print("""
    BEFORE (separate implementations):
    ❌ Code duplication: ~2,300 lines duplicated between projects
    ❌ Inconsistent fixes: Bugs fixed in one project but not the other
    ❌ Manual connection management: Complex reconnection logic in each project
    ❌ No connection pooling: New connection for each client instance
    ❌ Inconsistent error handling: Different approaches in each project
    
    AFTER (unified client):
    ✅ Zero code duplication: Single implementation shared across projects
    ✅ Consistent behavior: Bug fixes benefit all users immediately
    ✅ Automatic connection management: Built-in reconnection and error handling
    ✅ Connection pooling: Efficient resource usage with connection reuse
    ✅ Standardized error handling: Consistent, robust error recovery
    ✅ Performance monitoring: Built-in statistics and debugging capabilities
    ✅ Multi-server support: Same code works with Rust, Python, C#, Go servers
    """)
    
    # Demonstrate performance monitoring
    client = create_game_client(
        host="localhost:3000",
        database="blackholio"
    )
    
    import time
    start_time = time.time()
    
    try:
        # Perform operations and measure
        await client.connect()
        await client.join_game("PerformanceTest")
        
        # Simulate some game operations
        for i in range(10):
            await client.move_player(Vector2(0.1 * i, 0.1 * i))
        
        await client.player_split()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get performance statistics
        stats = client.get_client_statistics()
        
        print(f"\n📈 Performance Results:")
        print(f"  Operations completed in: {duration:.3f} seconds")
        print(f"  Total reducer calls: {stats['reducer_calls']}")
        print(f"  Successful calls: {stats['successful_reducers']}")
        print(f"  Connection attempts: {stats['connection_attempts']}")
        print(f"  Messages sent: {stats['messages_sent']}")
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
    
    finally:
        await client.shutdown()


async def run_migration_examples():
    """Run all migration examples."""
    print("🔄 Running migration examples...")
    
    # Blackholio-agent migration
    agent_migration = LegacyBlackholioAgentMigration()
    try:
        await agent_migration.migrate_connection_pattern()
        await agent_migration.migrate_game_state_access()
        await agent_migration.migrate_ml_training_loop()
        await agent_migration.migrate_error_handling()
    finally:
        await agent_migration.cleanup()
    
    print("\n" + "="*50)
    
    # Pygame client migration
    pygame_migration = LegacyPygameClientMigration()
    try:
        await pygame_migration.migrate_pygame_integration()
        await pygame_migration.migrate_rendering_pattern()
    finally:
        await pygame_migration.cleanup()
    
    print("\n" + "="*50)
    
    # Environment variable migration
    await environment_variable_migration()
    
    print("\n" + "="*50)
    
    # Performance comparison
    await performance_comparison()
    
    print("\n✅ All migration examples completed!")


if __name__ == "__main__":
    # Run migration examples when script is executed directly
    asyncio.run(run_migration_examples())