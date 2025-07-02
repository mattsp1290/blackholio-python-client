#!/usr/bin/env python3
"""
Simple test to check if events are flowing from connection to client.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blackholio_client.client import GameClient

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_event_flow():
    """Test that events flow from connection to client."""
    print("🧪 Testing event flow...")
    
    try:
        # Create client
        client = GameClient("localhost:3000", "blackholio")
        
        print("📡 Connecting...")
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect")
            return False
            
        print("✅ Connected successfully")
        
        # Check if active connection has event handling capability
        if client._active_connection:
            print(f"📋 Connection type: {type(client._active_connection)}")
            print(f"📋 Has 'on' method: {hasattr(client._active_connection, 'on')}")
            if hasattr(client._active_connection, '_event_callbacks'):
                print(f"📋 Event callbacks: {list(client._active_connection._event_callbacks.keys())}")
            
            # Check what methods and attributes it has
            print(f"📋 Connection attributes: {[attr for attr in dir(client._active_connection) if not attr.startswith('_')]}")
            
            # Check if it has game_entities or game_players
            if hasattr(client._active_connection, 'game_entities'):
                print(f"📋 Connection has game_entities: {len(client._active_connection.game_entities)}")
            if hasattr(client._active_connection, 'game_players'):
                print(f"📋 Connection has game_players: {len(client._active_connection.game_players)}")
        
        # Wait a bit for messages
        print("⏳ Waiting for messages...")
        await asyncio.sleep(3)
        
        # Check if we received any subscription data
        if hasattr(client._active_connection, '_messages_received'):
            print(f"📨 Messages received: {client._active_connection._messages_received}")
        
        # Manually try to enter game to trigger data
        print("🎮 Trying to enter game...")
        await client.enter_game("test_player")
        
        # Wait for game data
        await asyncio.sleep(2)
        
        # Check final state
        players = client.get_all_players()
        entities = client.get_all_entities()
        
        print(f"📊 Final state:")
        print(f"   Players: {len(players)}")
        print(f"   Entities: {len(entities)}")
        
        await client.disconnect()
        
        return len(players) > 0 or len(entities) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_event_flow())
    if success:
        print("✅ Event flow test passed")
    else:
        print("❌ Event flow test failed")