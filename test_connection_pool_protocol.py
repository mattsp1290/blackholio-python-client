#!/usr/bin/env python3
"""
Test connection pool protocol to verify it's using JSON correctly.
"""

import asyncio
import logging
from blackholio_client.connection.connection_manager import ConnectionManager
from blackholio_client.config.environment import EnvironmentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection_pool():
    """Test connection pool protocol."""
    
    # Create connection manager
    env_config = EnvironmentConfig()
    logger.info(f"Environment config protocol: {env_config.spacetime_protocol}")
    
    conn_manager = ConnectionManager(env_config)
    
    # Get a connection from the pool
    logger.info("Getting connection from pool...")
    try:
        async with conn_manager.get_connection() as conn:
            logger.info(f"Connection type: {type(conn)}")
            logger.info(f"Connection protocol: {getattr(conn, '_protocol_version', 'unknown')}")
            
            # Check the protocol helper
            if hasattr(conn, 'protocol_helper'):
                logger.info(f"Protocol helper use_binary: {conn.protocol_helper.use_binary}")
            
            # Check if it's actually connected
            logger.info(f"Is connected: {conn.is_connected}")
            
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection_pool())