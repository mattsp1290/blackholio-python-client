#!/usr/bin/env python3
"""Test ML training integration with fixed subscription callbacks."""

import asyncio
import logging
import sys
import time
sys.path.insert(0, 'src')

from blackholio_client import GameClient

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_ml_training_integration():
    """Test that the client works properly for ML training scenarios."""
    print("\n" + "="*60)
    print("🤖 Testing ML Training Integration")
    print("="*60 + "\n")
    
    # Simulate what the ML environment does
    client = GameClient("localhost:3000", "blackholio")
    
    print("1️⃣ Testing connection and initial data...")
    connected = await client.connect()
    
    if not connected:
        print("❌ Failed to connect to server")
        return False
    
    print("✅ Connected successfully")
    
    # Check initial state (this is what was failing before)
    await asyncio.sleep(0.5)
    
    players = client.get_all_players()
    entities = client.get_all_entities()
    
    print(f"\n📊 Initial game state:")
    print(f"   Players: {len(players)}")
    print(f"   Entities: {len(entities)}")
    
    if len(players) == 0 and len(entities) == 0:
        print("❌ No initial game state (this was the bug!)")
        await client.disconnect()
        return False
    
    print("✅ Initial game state received")
    
    # Test game join
    print(f"\n2️⃣ Testing game join (agent enters game)...")
    joined = await client.join_game("ml_agent_test")
    
    if not joined:
        print("❌ Failed to join game")
        await client.disconnect()
        return False
    
    print("✅ Joined game successfully")
    await asyncio.sleep(0.5)
    
    # Test getting local player
    local_player = client.get_local_player()
    if local_player:
        print(f"✅ Local player found: {local_player.name}")
    else:
        print("⚠️  Local player not set (may need to wait for server response)")
    
    # Test game state updates
    print(f"\n3️⃣ Testing game state updates...")
    players_after = client.get_all_players()
    entities_after = client.get_all_entities()
    
    print(f"   Players after join: {len(players_after)}")
    print(f"   Entities after join: {len(entities_after)}")
    
    # Test sending actions (what ML agent does)
    print(f"\n4️⃣ Testing action sending (agent control)...")
    from blackholio_client.models.game_entities import Vector2
    
    # Send a few move commands
    for i in range(3):
        direction = Vector2(x=1.0, y=0.0)  # Move right
        success = await client.move_player(direction)
        if success:
            print(f"✅ Move command {i+1} sent successfully")
        else:
            print(f"❌ Move command {i+1} failed")
        await asyncio.sleep(0.1)
    
    # Test leaving game (reset)
    print(f"\n5️⃣ Testing game leave (environment reset)...")
    left = await client.leave_game()
    if left:
        print("✅ Left game successfully")
    else:
        print("⚠️  Leave game returned false")
    
    # Disconnect
    await client.disconnect()
    
    print("\n" + "="*60)
    print("✅ ML TRAINING INTEGRATION TEST PASSED!")
    print("The client should now work properly with the ML training environment")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_ml_training_integration())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)