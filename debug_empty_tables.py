#!/usr/bin/env python3
"""Debug why DatabaseUpdate has empty tables."""

import asyncio
import logging
from src.blackholio_client.client import GameClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_empty_tables():
    """Connect to the server and debug why tables are empty."""
    
    # Create client
    client = GameClient(
        host="localhost:3000",
        database="blackholio-dev"
    )
    
    try:
        logger.info("🔄 Connecting to server...")
        success = await client.connect()
        
        if not success:
            logger.error("❌ Failed to connect")
            return
            
        logger.info("✅ Connected successfully")
        
        # Wait a bit to ensure all initial messages are processed
        await asyncio.sleep(2)
        
        # Check what data we have
        players = client.get_all_players()
        entities = client.get_all_entities()
        
        logger.info(f"📊 After connection: {len(players)} players, {len(entities)} entities")
        
        # Try to join a game
        logger.info("🎮 Attempting to join game...")
        joined = await client.join_game("DebugPlayer")
        
        if joined:
            logger.info("✅ Joined game successfully")
            
            # Wait for data to populate
            await asyncio.sleep(1)
            
            # Check again
            players = client.get_all_players()
            entities = client.get_all_entities()
            
            logger.info(f"📊 After joining: {len(players)} players, {len(entities)} entities")
        else:
            logger.error("❌ Failed to join game")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        logger.info("🔌 Disconnected")

if __name__ == "__main__":
    asyncio.run(debug_empty_tables())