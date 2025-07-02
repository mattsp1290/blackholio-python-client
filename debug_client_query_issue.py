#!/usr/bin/env python3
"""
Debug script to identify client query logic issues.

This script tests the blackholio-python-client to understand why 
get_all_players() and get_all_entities() return empty arrays despite 
data existing in the database.
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

async def debug_client_issues():
    """Debug client query issues."""
    print("🔍 Starting client query debugging...")
    
    try:
        # Create client
        client = GameClient("localhost:3000", "blackholio")
        client.enable_debug_logging("DEBUG")
        
        print("📡 Attempting to connect...")
        
        # Connect to server
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to server")
            return False
            
        print("✅ Connected to server")
        
        # Wait a moment for any initial data
        print("⏳ Waiting for initial data...")
        await asyncio.sleep(2)
        
        # Run comprehensive debugging
        await client.debug_full_client_state()
        
        # Try to join game to trigger data creation
        print("🎮 Attempting to join game...")
        joined = await client.join_game("debug_player_test")
        print(f"Join game result: {joined}")
        
        # Wait for game data
        print("⏳ Waiting for game data...")
        await asyncio.sleep(3)
        
        # Check data again after joining
        print("\n🔍 Checking data after joining game...")
        await client.debug_full_client_state()
        
        # Manual check of get_all methods
        print("\n📊 Manual method testing:")
        players = client.get_all_players()
        entities = client.get_all_entities()
        print(f"get_all_players() returned: {len(players)} players")
        print(f"get_all_entities() returned: {len(entities)} entities")
        
        if players:
            print(f"Sample player: {list(players.values())[0]}")
        if entities:
            print(f"Sample entity: {list(entities.values())[0]}")
        
        # Check connection stats
        if hasattr(client, '_active_connection') and client._active_connection:
            if hasattr(client._active_connection, 'connection_stats'):
                stats = client._active_connection.connection_stats
                print(f"\n📈 Connection stats: {stats}")
        
        await client.disconnect()
        return len(players) > 0 or len(entities) > 0
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main debug function."""
    print("🚀 Blackholio Client Query Debugging")
    print("=" * 50)
    
    # Test the client
    success = await debug_client_issues()
    
    print("=" * 50)
    if success:
        print("✅ Client query debugging completed - found data")
    else:
        print("❌ Client query debugging completed - no data found")
        print("   This confirms the issue: client cannot find existing data")

if __name__ == "__main__":
    asyncio.run(main())