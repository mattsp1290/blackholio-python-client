#!/usr/bin/env python3
"""
Test ML training data timing issue.

The problem: When ML training connects, it gets empty tables because
the server sends current state (empty) before enter_game creates data.
"""

import asyncio
import logging
import time
from blackholio_client import GameClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce noise from connection logs
logging.getLogger('blackholio_client.connection').setLevel(logging.WARNING)
logging.getLogger('blackholio_client.config').setLevel(logging.WARNING)


async def wait_for_game_data(client: GameClient, timeout: float = 5.0) -> bool:
    """Wait for game data to appear after calling enter_game."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        entities = len(client.get_all_entities())
        players = len(client.get_all_players())
        
        if entities > 0 or players > 1:  # More than just our player
            logger.info(f"✅ Game data appeared: {players} players, {entities} entities")
            return True
        
        await asyncio.sleep(0.1)
    
    logger.error(f"❌ Timeout waiting for game data after {timeout}s")
    return False


async def test_scenario(scenario_name: str, delay_before_connect: float = 0):
    """Test a specific connection scenario."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {scenario_name}")
    logger.info(f"{'='*60}")
    
    if delay_before_connect > 0:
        logger.info(f"Waiting {delay_before_connect}s before connecting...")
        await asyncio.sleep(delay_before_connect)
    
    client = GameClient("localhost:3000", "blackholio")
    
    try:
        # Connect
        logger.info("1. Connecting...")
        await client.connect()
        
        # Check initial data
        logger.info(f"2. Initial data: {len(client.get_all_players())} players, {len(client.get_all_entities())} entities")
        
        # Enter game
        logger.info("3. Calling enter_game...")
        success = await client.enter_game(f"TestPlayer_{scenario_name}")
        logger.info(f"   enter_game returned: {success}")
        
        # Check data immediately
        logger.info(f"4. Data immediately after: {len(client.get_all_players())} players, {len(client.get_all_entities())} entities")
        
        # Wait for data
        logger.info("5. Waiting for game data...")
        data_received = await wait_for_game_data(client)
        
        if data_received:
            logger.info(f"6. Final data: {len(client.get_all_players())} players, {len(client.get_all_entities())} entities")
        else:
            logger.error("6. No game data received!")
            
    finally:
        await client.disconnect()
        await asyncio.sleep(0.5)  # Let connection close cleanly


async def main():
    """Run multiple test scenarios."""
    
    # Scenario 1: Fresh connection (like ML training)
    await test_scenario("Fresh Connection", delay_before_connect=0)
    
    # Scenario 2: Connection after server has data
    await test_scenario("After Existing Game", delay_before_connect=2.0)
    
    # Scenario 3: Rapid reconnection
    await test_scenario("Rapid Reconnect", delay_before_connect=0.1)


if __name__ == "__main__":
    asyncio.run(main())