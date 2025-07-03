#!/usr/bin/env python3
"""
Debug different connection paths to understand the protocol mismatch.
"""

import asyncio
import logging
from blackholio_client import GameClient

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Focus on connection and protocol logs
logging.getLogger('blackholio_client.config').setLevel(logging.WARNING)


async def test_direct_client():
    """Test direct GameClient connection (what test_ml_training_integration.py does)."""
    logger.info("\n" + "="*60)
    logger.info("Testing Direct GameClient Connection")
    logger.info("="*60)
    
    client = GameClient("localhost:3000", "blackholio")
    
    # Check what connection manager is being used
    logger.info(f"Connection manager type: {type(client._connection_manager)}")
    logger.info(f"Has active connection: {client._active_connection is not None}")
    
    # Connect
    logger.info("Connecting...")
    success = await client.connect()
    logger.info(f"Connect result: {success}")
    
    if client._active_connection:
        logger.info(f"Active connection type: {type(client._active_connection)}")
        logger.info(f"Protocol version: {getattr(client._active_connection, '_protocol_version', 'unknown')}")
        if hasattr(client._active_connection, 'protocol_helper'):
            logger.info(f"Protocol helper use_binary: {client._active_connection.protocol_helper.use_binary}")
    
    await asyncio.sleep(0.5)
    await client.disconnect()


async def test_with_env_override():
    """Test with environment override."""
    logger.info("\n" + "="*60)
    logger.info("Testing with Protocol Override")
    logger.info("="*60)
    
    import os
    os.environ['SPACETIME_PROTOCOL'] = 'v1.bsatn.spacetimedb'  # Force binary
    
    client = GameClient("localhost:3000", "blackholio")
    logger.info("Connecting with binary protocol...")
    success = await client.connect()
    logger.info(f"Connect result: {success}")
    
    await asyncio.sleep(0.5)
    await client.disconnect()
    
    # Reset
    os.environ['SPACETIME_PROTOCOL'] = 'v1.json.spacetimedb'


async def main():
    """Run tests."""
    await test_direct_client()
    # Don't test binary - we know it will fail
    # await test_with_env_override()


if __name__ == "__main__":
    asyncio.run(main())