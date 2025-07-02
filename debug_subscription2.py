#!/usr/bin/env python3
"""Debug subscription data processing with detailed logs."""

import asyncio
from src.blackholio_client.connection.spacetimedb_connection import BlackholioClient
from src.blackholio_client.models.game_entities import GameEntity, GamePlayer

async def test_detailed_processing():
    """Test detailed processing with manual implementation."""
    
    print("🔍 Testing detailed subscription processing...")
    
    # Create client
    client = BlackholioClient(server_language="python")
    
    # Test table data processing with debug
    table_data = {
        "table_name": "entities",
        "rows": [
            {
                "entity_id": "test_entity_1",
                "position": {"x": 10, "y": 20},
                "mass": 50,
                "radius": 5,
                "entity_type": "food"
            }
        ]
    }
    
    print(f"Table name: '{table_data.get('table_name', '').lower()}'")
    print(f"'entity' in table name: {'entity' in table_data.get('table_name', '').lower()}")
    print(f"Number of rows: {len(table_data.get('rows', []))}")
    
    # Manual processing
    table_name = table_data.get('table_name', '').lower()
    if table_name in ['entities', 'entity', 'game_entities']:
        print("Processing entity table...")
        for i, row in enumerate(table_data.get('rows', [])):
            print(f"Processing row {i}: {row}")
            try:
                entity = GameEntity.from_dict(row)
                print(f"Created entity: {entity.entity_id}")
                client.game_entities[entity.entity_id] = entity
                print(f"Added to game_entities. Total: {len(client.game_entities)}")
            except Exception as e:
                print(f"Error creating entity from row {i}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"Final entities count: {len(client.game_entities)}")
    for eid, entity in client.game_entities.items():
        print(f"  Entity {eid}: {entity}")

if __name__ == "__main__":
    asyncio.run(test_detailed_processing())