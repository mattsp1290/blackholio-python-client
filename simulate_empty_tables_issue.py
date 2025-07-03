#!/usr/bin/env python3
"""Simulate the empty tables issue based on the logs from the ML training."""

import asyncio
import logging
import json
from src.blackholio_client.client import GameClient
from src.blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def simulate_database_update_with_empty_tables():
    """Simulate a DatabaseUpdate event with empty tables to debug the processing."""
    
    # Create client
    client = GameClient(
        host="localhost:3000",
        database="blackholio-dev"
    )
    
    # Simulate the exact DatabaseUpdate message that was causing empty tables
    # Based on the logs, the issue was that 'tables' was an empty dict {}
    database_update_message = {
        "type": "DatabaseUpdate",
        "tables": {},  # This is the problem - empty tables dict
        "request_id": "test-request-123",
        "total_host_execution_duration": None
    }
    
    logger.info("🧪 Simulating DatabaseUpdate with empty tables...")
    logger.info(f"📊 Message structure: {json.dumps(database_update_message, indent=2)}")
    
    # Trigger the handlers directly
    try:
        await client._handle_database_update(database_update_message)
        
        # Check results
        players = client.get_all_players()
        entities = client.get_all_entities()
        
        logger.info(f"📊 Result: {len(players)} players, {len(entities)} entities")
        
        if len(players) == 0 and len(entities) == 0:
            logger.error("❌ CONFIRMED: Empty tables dict leads to 0 players, 0 entities")
        else:
            logger.info("✅ Data was processed successfully")
            
    except Exception as e:
        logger.error(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()

async def simulate_database_update_with_actual_data():
    """Simulate a DatabaseUpdate with actual game data."""
    
    # Create client
    client = GameClient(
        host="localhost:3000",
        database="blackholio-dev"
    )
    
    # Simulate a DatabaseUpdate with actual game data
    database_update_with_data = {
        "type": "DatabaseUpdate",
        "tables": {
            "Player": [
                {
                    "player_id": 1,
                    "name": "TestPlayer",
                    "position": {"x": 100.0, "y": 200.0},
                    "direction": {"x": 1.0, "y": 0.0},
                    "mass": 10.0,
                    "radius": 5.0,
                    "score": 0,
                    "is_active": True
                }
            ],
            "Entity": [
                {
                    "entity_id": 1,
                    "position": {"x": 150.0, "y": 250.0},
                    "mass": 5.0,
                    "radius": 3.0,
                    "velocity": {"x": 0.0, "y": 0.0},
                    "entity_type": "food"
                }
            ]
        },
        "request_id": "test-request-456",
        "total_host_execution_duration": None
    }
    
    logger.info("🧪 Simulating DatabaseUpdate with actual data...")
    logger.info(f"📊 Message structure: {json.dumps(database_update_with_data, indent=2)}")
    
    # Trigger the handlers directly
    try:
        await client._handle_database_update(database_update_with_data)
        
        # Check results
        players = client.get_all_players()
        entities = client.get_all_entities()
        
        logger.info(f"📊 Result: {len(players)} players, {len(entities)} entities")
        
        if len(players) > 0 and len(entities) > 0:
            logger.info("✅ CONFIRMED: Non-empty tables lead to populated data")
            logger.info(f"📊 Player: {list(players.values())[0]}")
            logger.info(f"📊 Entity: {list(entities.values())[0]}")
        else:
            logger.error("❌ Data was not processed correctly")
            
    except Exception as e:
        logger.error(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the simulations."""
    logger.info("🚀 Starting empty tables simulation...")
    
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Empty tables dict")
    logger.info("="*50)
    await simulate_database_update_with_empty_tables()
    
    logger.info("\n" + "="*50)
    logger.info("TEST 2: Tables with actual data")
    logger.info("="*50)
    await simulate_database_update_with_actual_data()
    
    logger.info("\n🎯 CONCLUSION:")
    logger.info("The issue is that the server is sending DatabaseUpdate messages with empty 'tables' dict.")
    logger.info("This leads to '✅ Processed database update - Players: 0, Entities: 0' even though callbacks are registered.")

if __name__ == "__main__":
    asyncio.run(main())