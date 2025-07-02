#!/usr/bin/env python3
"""
Test script to verify our specific fixes:
1. Protocol fix - TEXT frames instead of BINARY
2. Data flow fix - subscription data populates client caches
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blackholio_client.client import GameClient


async def test_fixes():
    """Test that our fixes work correctly."""
    print("🧪 Testing Blackholio Client Fixes")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    try:
        # Test 1: Connection without protocol errors
        print("\n✨ Test 1: Protocol Fix - Connection Stability")
        client = GameClient("localhost:3000", "blackholio")
        
        connected = await client.connect()
        if connected:
            print("  ✅ Connected successfully without protocol errors")
            success_count += 1
        else:
            print("  ❌ Failed to connect")
            
        # Wait for initial data
        await asyncio.sleep(1)
        
        # Test 2: Data is populated from subscription
        print("\n✨ Test 2: Data Flow Fix - Initial Data Population")
        players = client.get_all_players()
        entities = client.get_all_entities()
        
        if len(players) > 0 or len(entities) > 0:
            print(f"  ✅ Data populated: {len(players)} players, {len(entities)} entities")
            success_count += 1
        else:
            print("  ❌ No data populated from subscription")
            
        # Test 3: Join game and check data
        print("\n✨ Test 3: Game Operations - Join Game")
        joined = await client.join_game("test_player")
        if joined:
            print("  ✅ Successfully joined game")
            success_count += 1
        else:
            print("  ❌ Failed to join game")
            
        # Wait for game data
        await asyncio.sleep(2)
        
        # Test 4: Check connection stability
        print("\n✨ Test 4: Connection Stability Check")
        if client.is_connected():
            stats = client.get_connection_info()
            print(f"  ✅ Connection stable: {stats['state']}")
            print(f"     Protocol: {stats['protocol']}")
            print(f"     Authenticated: {stats['is_authenticated']}")
            success_count += 1
        else:
            print("  ❌ Connection lost")
            
        print("\n✨ Disconnecting gracefully...")
        await client.disconnect()
        
        # Give server time to process the close frame
        await asyncio.sleep(0.1)
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 50)
    print(f"📊 Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL FIXES VERIFIED! The client is working perfectly!")
        return True
    else:
        print(f"⚠️  {total_tests - success_count} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_fixes())
    sys.exit(0 if success else 1)