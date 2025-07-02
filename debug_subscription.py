#!/usr/bin/env python3
"""Debug subscription data processing."""

import asyncio
from src.blackholio_client.connection.spacetimedb_connection import BlackholioClient
from src.blackholio_client.models.game_entities import GameEntity, GamePlayer

async def test_subscription_processing():
    """Test subscription data processing step by step."""
    
    print("🔍 Testing subscription data processing...")
    
    # Create client
    client = BlackholioClient(server_language="python")
    print(f"Initial entities: {len(client.game_entities)}")
    print(f"Initial players: {len(client.game_players)}")
    
    # Test entity creation directly
    print("\n🧪 Testing GameEntity.from_dict...")
    entity_data = {
        "entity_id": "test_entity_1",
        "position": {"x": 10, "y": 20},
        "mass": 50,
        "radius": 5,
        "entity_type": "food"
    }
    
    try:
        entity = GameEntity.from_dict(entity_data)
        print(f"✅ Created entity: {entity.entity_id} at {entity.position.x}, {entity.position.y}")
    except Exception as e:
        print(f"❌ Failed to create entity: {e}")
        return
    
    # Test player creation directly
    print("\n🧪 Testing GamePlayer.from_dict...")
    player_data = {
        "entity_id": "test_player_1",  # GamePlayer extends GameEntity
        "player_id": "test_player_1",
        "name": "TestPlayer",
        "position": {"x": 0, "y": 0},
        "mass": 100,
        "radius": 10
    }
    
    try:
        player = GamePlayer.from_dict(player_data)
        print(f"✅ Created player: {player.name} ({player.player_id}) at {player.position.x}, {player.position.y}")
    except Exception as e:
        print(f"❌ Failed to create player: {e}")
        return
    
    # Test table data processing
    print("\n🧪 Testing _process_table_data...")
    table_data = {
        "table_name": "entities",
        "rows": [entity_data]
    }
    
    try:
        await client._process_table_data(table_data)
        print(f"✅ Processed table data. Entities: {len(client.game_entities)}")
        if client.game_entities:
            for eid, entity in client.game_entities.items():
                print(f"  Entity {eid}: {entity.entity_type} at {entity.position.x}, {entity.position.y}")
        else:
            print("  ⚠️ No entities were added")
    except Exception as e:
        print(f"❌ Failed to process table data: {e}")
        import traceback
        traceback.print_exc()
    
    # Test player table data processing
    print("\n🧪 Testing player table data...")
    player_table_data = {
        "table_name": "players", 
        "rows": [player_data]
    }
    
    try:
        await client._process_table_data(player_table_data)
        print(f"✅ Processed player table data. Players: {len(client.game_players)}")
        if client.game_players:
            for pid, player in client.game_players.items():
                print(f"  Player {pid}: {player.name} at {player.position.x}, {player.position.y}")
        else:
            print("  ⚠️ No players were added")
    except Exception as e:
        print(f"❌ Failed to process player table data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subscription_processing())