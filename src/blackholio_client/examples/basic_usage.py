"""
Basic usage examples for the Blackholio SpacetimeDB client.

This module demonstrates the most common usage patterns for connecting to
SpacetimeDB servers and interacting with the Blackholio game.
"""

import asyncio
import logging
from typing import Dict, Any

from ..client import create_game_client, GameClient
from ..interfaces.connection_interface import ConnectionState
from ..models.game_entities import GamePlayer, GameEntity


# Configure logging for examples
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_connection_example():
    """
    Demonstrate basic connection to a SpacetimeDB server.
    
    This example shows how to create a client, connect to the server,
    and handle connection state changes.
    """
    print("\n=== Basic Connection Example ===")
    
    # Create client for Rust server (default)
    client = create_game_client(
        host="localhost:3000",
        database="blackholio",
        server_language="rust"
    )
    
    # Set up connection state monitoring
    def on_connection_changed(state: ConnectionState):
        print(f"Connection state changed to: {state.value}")
    
    client.on_connection_state_changed(on_connection_changed)
    
    # Set up error handling
    def on_error(error_message: str):
        print(f"Connection error: {error_message}")
    
    client.on_error(on_error)
    
    try:
        # Connect to server
        print("Connecting to SpacetimeDB server...")
        success = await client.connect()
        
        if success:
            print("✅ Connected successfully!")
            print(f"Connection info: {client.get_connection_info()}")
            
            # Keep connection alive for a moment
            await asyncio.sleep(2)
            
            # Gracefully disconnect
            print("Disconnecting...")
            await client.disconnect()
            print("✅ Disconnected successfully!")
        else:
            print("❌ Failed to connect")
            
    except Exception as e:
        print(f"❌ Connection example failed: {e}")
    
    finally:
        await client.shutdown()


async def basic_game_interaction_example():
    """
    Demonstrate basic game interactions including joining, moving, and leaving.
    
    This example shows the most common game operations that both
    blackholio-agent and client-pygame would need.
    """
    print("\n=== Basic Game Interaction Example ===")
    
    # Create client
    client = create_game_client(
        host="localhost:3000",
        database="blackholio",
        server_language="rust",
        auto_reconnect=True
    )
    
    # Set up game event handlers
    def on_player_joined(player: GamePlayer):
        print(f"🎮 Player joined: {player.name}")
    
    def on_entity_created(entity: GameEntity):
        print(f"🔵 Entity created: ID {entity.entity_id} at {entity.position}")
    
    client.on_player_joined(on_player_joined)
    client.on_entity_created(on_entity_created)
    
    try:
        # Join the game (this handles connection + subscription + enter game)
        print("Joining game as 'ExamplePlayer'...")
        success = await client.join_game("ExamplePlayer")
        
        if success:
            print("✅ Joined game successfully!")
            
            # Check game state
            if client.is_in_game():
                print(f"Current player: {client.get_local_player()}")
                print(f"Player entities: {len(client.get_local_player_entities())}")
                print(f"Total entities: {len(client.get_all_entities())}")
                print(f"Total players: {len(client.get_all_players())}")
            
            # Simulate some game actions
            print("\nPerforming game actions...")
            
            # Move player
            from ..models.game_entities import Vector2
            await client.move_player(Vector2(1.0, 0.0))  # Move right
            print("Moved player right")
            
            await asyncio.sleep(1)
            
            await client.move_player(Vector2(0.0, 1.0))  # Move up
            print("Moved player up")
            
            await asyncio.sleep(1)
            
            # Try to split
            await client.player_split()
            print("Attempted player split")
            
            await asyncio.sleep(2)
            
            # Leave game
            print("\nLeaving game...")
            await client.leave_game()
            print("✅ Left game successfully!")
            
        else:
            print("❌ Failed to join game")
            
    except Exception as e:
        print(f"❌ Game interaction example failed: {e}")
    
    finally:
        await client.shutdown()


async def authentication_example():
    """
    Demonstrate authentication patterns including token management.
    
    This example shows how to handle authentication tokens,
    which is important for persistent player identity.
    """
    print("\n=== Authentication Example ===")
    
    client = create_game_client(
        host="localhost:3000",
        database="blackholio"
    )
    
    # Set up authentication monitoring
    def on_auth_changed(is_authenticated: bool):
        print(f"Authentication state: {'✅ Authenticated' if is_authenticated else '❌ Not authenticated'}")
    
    client.on_authentication_changed(on_auth_changed)
    
    try:
        # Connect without authentication
        await client.connect()
        
        print(f"Auth info: {client.get_auth_info()}")
        
        # Try to load saved token
        if client.load_token():
            print("✅ Loaded saved authentication token")
        else:
            print("ℹ️ No saved token found, authenticating...")
            
            # In a real scenario, you would get credentials from user input
            # or from an external authentication system
            fake_credentials = {"token": "example_auth_token_12345"}
            
            if await client.authenticate(fake_credentials):
                print("✅ Authentication successful!")
                print(f"Identity: {client.identity}")
                print(f"Token length: {len(client.token or '')}")
                
                # Save token for future use
                client.save_token()
                print("💾 Token saved for future sessions")
            else:
                print("❌ Authentication failed")
        
        # Demonstrate token validation
        if client.validate_token():
            print("✅ Current token is valid")
        else:
            print("❌ Current token is invalid")
        
    except Exception as e:
        print(f"❌ Authentication example failed: {e}")
    
    finally:
        await client.shutdown()


async def multi_server_language_example():
    """
    Demonstrate connecting to different server language implementations.
    
    This example shows how the unified API works consistently across
    Rust, Python, C#, and Go server implementations.
    """
    print("\n=== Multi-Server Language Example ===")
    
    server_configs = [
        {"language": "rust", "port": 3000},
        {"language": "python", "port": 3001},
        {"language": "csharp", "port": 3002},
        {"language": "go", "port": 3003}
    ]
    
    for config in server_configs:
        print(f"\n--- Testing {config['language'].upper()} server ---")
        
        client = create_game_client(
            host=f"localhost:{config['port']}",
            database="blackholio",
            server_language=config['language']
        )
        
        try:
            # The API is identical regardless of server language
            success = await client.connect()
            
            if success:
                print(f"✅ Connected to {config['language']} server")
                
                # Same game operations work across all server types
                if await client.join_game(f"TestPlayer_{config['language']}"):
                    print(f"✅ Joined game on {config['language']} server")
                    
                    # Game operations are identical
                    await client.move_player(Vector2(0.5, 0.5))
                    print(f"✅ Moved player on {config['language']} server")
                    
                    await client.leave_game()
                    print(f"✅ Left game on {config['language']} server")
                
            else:
                print(f"❌ Could not connect to {config['language']} server (may not be running)")
                
        except Exception as e:
            print(f"❌ Error with {config['language']} server: {e}")
        
        finally:
            await client.shutdown()


async def error_handling_and_reconnection_example():
    """
    Demonstrate error handling and automatic reconnection features.
    
    This example shows how to handle connection failures and
    implement robust error recovery.
    """
    print("\n=== Error Handling and Reconnection Example ===")
    
    client = create_game_client(
        host="localhost:3000",
        database="blackholio",
        auto_reconnect=True
    )
    
    # Track connection attempts
    connection_attempts = 0
    
    def on_connection_changed(state: ConnectionState):
        nonlocal connection_attempts
        print(f"Connection state: {state.value}")
        
        if state == ConnectionState.CONNECTING:
            connection_attempts += 1
            print(f"Connection attempt #{connection_attempts}")
    
    def on_error(error_message: str):
        print(f"🚨 Error occurred: {error_message}")
    
    client.on_connection_state_changed(on_connection_changed)
    client.on_error(on_error)
    
    try:
        # Configure reconnection behavior
        client.enable_auto_reconnect(
            max_attempts=5,
            delay=2.0,
            exponential_backoff=True
        )
        
        # Try to connect
        print("Attempting initial connection...")
        success = await client.connect()
        
        if success:
            print("✅ Initial connection successful")
            
            # Simulate working with the connection
            await client.join_game("ErrorTestPlayer")
            
            # In a real scenario, you might detect connection issues
            # and trigger reconnection manually
            if not client.is_connected():
                print("Connection lost, attempting reconnect...")
                await client.reconnect()
            
        else:
            print("❌ Initial connection failed")
            print("Auto-reconnect would handle retries in the background")
        
        # Demonstrate graceful error recovery
        try:
            # This might fail if server is not available
            await client.move_player(Vector2(1.0, 0.0))
        except Exception as game_error:
            print(f"Game action failed: {game_error}")
            print("Client would handle this gracefully")
        
    except Exception as e:
        print(f"❌ Error handling example failed: {e}")
    
    finally:
        await client.shutdown()


async def statistics_and_monitoring_example():
    """
    Demonstrate client statistics and monitoring capabilities.
    
    This example shows how to monitor client performance and
    gather metrics useful for debugging and optimization.
    """
    print("\n=== Statistics and Monitoring Example ===")
    
    client = create_game_client(
        host="localhost:3000",
        database="blackholio"
    )
    
    try:
        await client.connect()
        await client.join_game("StatsTestPlayer")
        
        # Perform some operations to generate statistics
        for i in range(5):
            await client.move_player(Vector2(0.1 * i, 0.1 * i))
            await asyncio.sleep(0.5)
        
        await client.player_split()
        
        # Get comprehensive statistics
        stats = client.get_client_statistics()
        print("\n📊 Client Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Get current client state
        state = client.get_client_state()
        print("\n📋 Client State Summary:")
        print(f"  Connection: {state['connection']['state']}")
        print(f"  In game: {state['game_state']['is_in_game']}")
        print(f"  Entities: {state['game_state']['entities_count']}")
        print(f"  Subscriptions: {len(state['subscriptions']['tables'])}")
        
        # Get debug information
        debug_info = client.get_debug_info()
        print("\n🔍 Debug Information:")
        print(f"  Memory usage - Entities: {debug_info['memory_usage']['entities']}")
        print(f"  Callbacks registered: {debug_info['callbacks']}")
        
        # Export state for detailed analysis
        if client.export_state("client_state_export.json"):
            print("✅ State exported to client_state_export.json")
        
    except Exception as e:
        print(f"❌ Statistics example failed: {e}")
    
    finally:
        await client.shutdown()


async def run_all_examples():
    """Run all basic usage examples in sequence."""
    print("🚀 Running all basic usage examples...")
    
    examples = [
        basic_connection_example,
        basic_game_interaction_example,
        authentication_example,
        multi_server_language_example,
        error_handling_and_reconnection_example,
        statistics_and_monitoring_example
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            print(f"❌ Example {example.__name__} failed: {e}")
            continue
    
    print("\n✅ All basic usage examples completed!")


if __name__ == "__main__":
    # Run examples when script is executed directly
    asyncio.run(run_all_examples())