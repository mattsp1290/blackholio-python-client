#!/usr/bin/env python3
"""
Test script to verify the SpacetimeDB binary protocol fix.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
from blackholio_client.connection.server_config import ServerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_binary_protocol_connection():
    """Test the SpacetimeDB connection with binary protocol."""
    config = ServerConfig(
        host="localhost",
        port=3000,
        db_identity="blackholio",
        protocol="v1.bsatn.spacetimedb",
        language="rust"  # or whatever server language you're using
    )
    
    connection = SpacetimeDBConnection(config)
    
    try:
        logger.info("Testing SpacetimeDB connection with binary protocol...")
        
        # Test connection
        success = await connection.connect()
        
        if success:
            logger.info("✅ Connection successful with binary protocol!")
            logger.info(f"Connected with identity: {connection.identity}")
            
            # Keep connection alive for a few seconds to test stability
            logger.info("Testing connection stability...")
            await asyncio.sleep(5)
            
            # Check connection stats
            stats = connection.connection_stats
            logger.info(f"Connection stats: {stats}")
            
            if connection.is_connected:
                logger.info("✅ Connection remained stable!")
            else:
                logger.error("❌ Connection became unstable")
                
        else:
            logger.error("❌ Connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
        
    finally:
        # Clean up
        await connection.disconnect()
        logger.info("Disconnected from SpacetimeDB")
    
    return success

async def main():
    """Run the test."""
    logger.info("Starting SpacetimeDB binary protocol test...")
    
    success = await test_binary_protocol_connection()
    
    if success:
        logger.info("🎉 All tests passed! Binary protocol fix is working.")
        sys.exit(0)
    else:
        logger.error("💥 Tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())