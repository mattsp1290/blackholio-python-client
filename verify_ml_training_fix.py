#!/usr/bin/env python3
"""
Verify that ML training now receives full game state after protocol fix.
This script simulates the ML training connection pattern using the connection pool.
"""

import asyncio
import logging
from blackholio_client import GameClient
from blackholio_client.connection.connection_manager import get_connection_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ml_training_connection():
    """Test ML training connection pattern with connection pool."""
    
    logger.info("=" * 60)
    logger.info("Testing ML Training Connection Pattern")
    logger.info("=" * 60)
    
    # Create GameClient (which uses connection pool internally)
    client = GameClient("localhost:3000", "blackholio")
    
    logger.info("1. Connecting to server...")
    success = await client.connect()
    logger.info(f"   Connect result: {success}")
    
    if not success:
        logger.error("Failed to connect!")
        return
    
    # Check if we're using the connection pool
    logger.info(f"2. Connection type: {type(client._active_connection)}")
    logger.info(f"   Using connection manager: {client._connection_manager is not None}")
    
    # Join game
    logger.info("3. Calling enter_game...")
    await client.enter_game("ml_test_player")
    
    # Wait for initial data
    logger.info("4. Waiting for initial game state...")
    await asyncio.sleep(2.0)
    
    # Check received data
    logger.info("5. Checking received data:")
    players = client.get_all_players()
    entities = client.get_all_entities()
    
    logger.info(f"   Players: {len(players)}")
    logger.info(f"   Entities: {len(entities)}")
    
    if len(entities) > 0:
        logger.info("   ✅ SUCCESS: Received game entities!")
        logger.info(f"   Entity types: {set(e.get('entity_type', 'unknown') for e in entities[:10])}")
    else:
        logger.error("   ❌ FAILURE: No entities received!")
    
    # Test reducer calls
    logger.info("6. Testing reducer calls...")
    
    # Test update_player_input
    success = await client.update_player_input({"x": 1.0, "y": 0.0})
    logger.info(f"   update_player_input: {'✅ Success' if success else '❌ Failed'}")
    
    # Test player_split
    success = await client.player_split()
    logger.info(f"   player_split: {'✅ Success' if success else '❌ Failed'}")
    
    # Wait a bit to see any updates
    await asyncio.sleep(1.0)
    
    # Final check
    logger.info("7. Final state:")
    logger.info(f"   Players: {len(client.get_all_players())}")
    logger.info(f"   Entities: {len(client.get_all_entities())}")
    
    # Leave game
    logger.info("8. Leaving game...")
    await client.leave_game()
    
    await client.disconnect()
    
    # Get connection pool metrics
    logger.info("\n9. Connection Pool Metrics:")
    manager = get_connection_manager()
    metrics = manager.get_global_metrics()
    for pool_key, pool_metrics in metrics['pools'].items():
        logger.info(f"   Pool {pool_key}:")
        logger.info(f"     Total connections: {pool_metrics['total_connections']}")
        logger.info(f"     Active connections: {pool_metrics['active_connections']}")
        logger.info(f"     Health status: {pool_metrics['health_status']}")

async def test_direct_pool_connection():
    """Test direct connection pool usage (what ML training does internally)."""
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Direct Connection Pool Usage")
    logger.info("=" * 60)
    
    manager = get_connection_manager()
    
    # Get connection from pool
    logger.info("1. Getting connection from pool...")
    async with manager.get_connection() as conn:
        logger.info(f"   Connection type: {type(conn)}")
        logger.info(f"   Is connected: {conn.is_connected}")
        logger.info(f"   Protocol: {getattr(conn, '_protocol_version', 'unknown')}")
        
        if hasattr(conn, 'websocket') and conn.websocket:
            logger.info(f"   WebSocket state: {conn.websocket.state}")
        
        # The connection should already be connected by the pool
        if conn.is_connected:
            logger.info("   ✅ Connection is ready")
        else:
            logger.error("   ❌ Connection not ready!")

async def main():
    """Run all tests."""
    try:
        # Test ML training pattern
        await test_ml_training_connection()
        
        # Test direct pool usage
        await test_direct_pool_connection()
        
        # Cleanup
        manager = get_connection_manager()
        await manager.shutdown_all()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())