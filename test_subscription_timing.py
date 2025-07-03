#!/usr/bin/env python3
"""
Test subscription timing to understand why ML training gets empty tables.
"""

import asyncio
import logging
import time
from blackholio_client import GameClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_subscription_timing():
    """Test subscription data timing."""
    
    # Create client
    client = GameClient("localhost:3000", "blackholio")
    
    logger.info("1. Connecting to server...")
    await client.connect()
    
    # Check initial data
    logger.info("2. Checking initial data immediately after connect...")
    logger.info(f"   Players: {len(client.get_all_players())}")
    logger.info(f"   Entities: {len(client.get_all_entities())}")
    
    # Join game
    logger.info("3. Calling enter_game...")
    await client.enter_game("test_player")
    
    # Check data immediately
    logger.info("4. Checking data immediately after enter_game...")
    logger.info(f"   Players: {len(client.get_all_players())}")
    logger.info(f"   Entities: {len(client.get_all_entities())}")
    
    # Wait a bit and check again
    logger.info("5. Waiting 1 second...")
    await asyncio.sleep(1.0)
    
    logger.info("6. Checking data after 1 second...")
    logger.info(f"   Players: {len(client.get_all_players())}")
    logger.info(f"   Entities: {len(client.get_all_entities())}")
    
    # Check if we need to manually trigger a subscription refresh
    logger.info("7. Checking subscription state...")
    subscribed_tables = client.get_subscribed_tables()
    logger.info(f"   Subscribed tables: {subscribed_tables}")
    
    # Try re-subscribing
    logger.info("8. Re-subscribing to tables...")
    await client.subscribe_to_tables(["entity", "player", "circle", "food", "config"])
    
    # Wait for data
    logger.info("9. Waiting for data after re-subscribe...")
    await asyncio.sleep(1.0)
    
    logger.info("10. Final data check...")
    logger.info(f"    Players: {len(client.get_all_players())}")
    logger.info(f"    Entities: {len(client.get_all_entities())}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_subscription_timing())