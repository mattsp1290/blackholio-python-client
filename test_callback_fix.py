#!/usr/bin/env python3
"""Test script to verify subscription callback fix."""

import asyncio
import logging
import sys
sys.path.insert(0, 'src')

from blackholio_client import GameClient

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_callback_fix():
    """Test that callbacks are registered before events fire."""
    print("\n" + "="*60)
    print("🧪 Testing Subscription Callback Fix")
    print("="*60 + "\n")
    
    client = GameClient("localhost:3000", "blackholio")
    
    print("📡 Connecting to server...")
    # Connect and verify callbacks catch initial events
    connected = await client.connect()
    
    if not connected:
        print("❌ Failed to connect to server")
        return False
    
    print("✅ Connected successfully")
    
    # Give a moment for any async processing
    await asyncio.sleep(0.5)
    
    # Check if identity was set
    identity_set = client._identity is not None
    print(f"\n🔐 Identity set: {identity_set}")
    if identity_set:
        print(f"   Identity: {client._identity}")
    
    # Check initial data
    players = client.get_all_players()
    entities = client.get_all_entities()
    
    print(f"\n📊 Initial data received:")
    print(f"   Players: {len(players)}")
    print(f"   Entities: {len(entities)}")
    
    if len(players) > 0:
        print(f"   Sample player: {list(players.values())[0]}")
    if len(entities) > 0:
        print(f"   Sample entity: {list(entities.values())[0]}")
    
    # Join game and verify data flows
    print(f"\n🎮 Joining game as 'test_player'...")
    joined = await client.join_game("test_player")
    
    if not joined:
        print("❌ Failed to join game")
        await client.disconnect()
        return False
    
    print("✅ Joined game successfully")
    
    # Wait for data to update
    await asyncio.sleep(1)
    
    # Check data after joining
    players_after = client.get_all_players()
    entities_after = client.get_all_entities()
    
    print(f"\n📊 After joining game:")
    print(f"   Players: {len(players_after)}")
    print(f"   Entities: {len(entities_after)}")
    
    # Verify we have data
    success = True
    if len(players_after) == 0:
        print("\n❌ FAIL: Still no players after joining!")
        success = False
    else:
        print("\n✅ SUCCESS: Players found!")
        
    if len(entities_after) == 0:
        print("❌ FAIL: Still no entities after joining!")
        success = False
    else:
        print("✅ SUCCESS: Entities found!")
    
    # Disconnect
    print("\n🔌 Disconnecting...")
    await client.disconnect()
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED: Subscription callbacks working!")
    else:
        print("❌ TEST FAILED: Subscription callbacks not working properly")
    print("="*60 + "\n")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(test_callback_fix())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)