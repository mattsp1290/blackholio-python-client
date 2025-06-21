"""
Data Models Examples - Comprehensive Usage Demonstrations

Shows how to use the advanced data model features including
serialization, validation, protocol adaptation, and data pipelines
for seamless integration with different SpacetimeDB server languages.
"""

import asyncio
import time
from typing import List

from blackholio_client.models import (
    # Core entities
    GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState,
    
    # Serialization
    serialize, deserialize, SerializationFormat, ServerLanguage,
    
    # Validation
    validate_entity, validate_player, validate_game_state, ValidationError,
    
    # Protocol adaptation
    adapt_to_server, adapt_from_server, ProtocolVersion,
    
    # Data pipeline
    DataPipeline, PipelineConfiguration, process_for_server, process_from_server
)


def basic_serialization_example():
    """Demonstrate basic serialization capabilities."""
    print("=== Basic Serialization Example ===")
    
    # Create a sample player
    player = GamePlayer(
        entity_id="player_123",
        player_id="player_123",
        name="TestPlayer",
        position=Vector2(100.0, 200.0),
        velocity=Vector2(10.0, -5.0),
        mass=50.0,
        radius=25.0,
        score=1500
    )
    
    print(f"Original player: {player.name} at {player.position}")
    
    # Serialize to different formats for different servers
    server_configs = [
        (ServerLanguage.RUST, "Rust"),
        (ServerLanguage.PYTHON, "Python"), 
        (ServerLanguage.CSHARP, "C#"),
        (ServerLanguage.GO, "Go")
    ]
    
    for server_lang, server_name in server_configs:
        # JSON serialization
        json_data = serialize(player, SerializationFormat.JSON, server_lang)
        print(f"{server_name} JSON: {len(json_data)} bytes")
        
        # Binary serialization
        binary_data = serialize(player, SerializationFormat.BINARY, server_lang)
        print(f"{server_name} Binary: {len(binary_data)} bytes")
        
        # Deserialize back
        restored_player = deserialize(json_data, GamePlayer, SerializationFormat.JSON, server_lang)
        print(f"Restored: {restored_player.name} at {restored_player.position}")
        print()


def protocol_adaptation_example():
    """Demonstrate protocol adaptation for different server languages."""
    print("=== Protocol Adaptation Example ===")
    
    # Create sample data
    entity_data = {
        'entity_id': 'test_entity_456',
        'position': {'x': 150.0, 'y': 300.0},
        'velocity': {'x': 20.0, 'y': -10.0},
        'mass': 75.0,
        'radius': 30.0,
        'entity_type': 'player',
        'is_active': True,
        'created_at': time.time(),
        'updated_at': time.time()
    }
    
    print("Original data format:")
    for key, value in entity_data.items():
        print(f"  {key}: {value}")
    print()
    
    # Adapt to different server formats
    server_adaptations = [
        (ServerLanguage.RUST, "Rust (snake_case, lowercase enums)"),
        (ServerLanguage.CSHARP, "C# (PascalCase)"),
        (ServerLanguage.GO, "Go (camelCase)"),
        (ServerLanguage.PYTHON, "Python (native format)")
    ]
    
    for server_lang, description in server_adaptations:
        adapted_data = adapt_to_server(entity_data, 'GameEntity', server_lang)
        print(f"{description}:")
        for key, value in adapted_data.items():
            print(f"  {key}: {value}")
        
        # Adapt back to client format
        client_data = adapt_from_server(adapted_data, 'GameEntity', server_lang)
        print(f"Restored client format matches: {client_data == entity_data}")
        print()


def validation_example():
    """Demonstrate data validation capabilities."""
    print("=== Data Validation Example ===")
    
    # Create valid entities
    valid_player = GamePlayer(
        entity_id="valid_player",
        player_id="valid_player",
        name="ValidPlayer",
        position=Vector2(50.0, 75.0),
        velocity=Vector2(0.0, 0.0),
        mass=40.0,
        radius=20.0,
        score=100
    )
    
    valid_circle = GameCircle(
        entity_id="valid_circle",
        circle_id="valid_circle",
        position=Vector2(200.0, 150.0),
        mass=5.0,
        radius=8.0,
        circle_type="food",
        value=10
    )
    
    # Validate individual objects
    try:
        validate_player(valid_player)
        print("✓ Valid player passed validation")
    except ValidationError as e:
        print(f"✗ Player validation failed: {e}")
    
    try:
        from blackholio_client.models import validate_circle
        validate_circle(valid_circle)
        print("✓ Valid circle passed validation")
    except ValidationError as e:
        print(f"✗ Circle validation failed: {e}")
    
    # Validate complete game state
    entities = [valid_player, valid_circle]
    players = [valid_player]
    circles = [valid_circle]
    
    try:
        validate_game_state(entities, players, circles)
        print("✓ Complete game state passed validation")
    except ValidationError as e:
        print(f"✗ Game state validation failed: {e}")
    
    # Demonstrate validation failure
    print("\nTesting validation failures:")
    
    # Create invalid player (negative mass)
    try:
        invalid_player = GamePlayer(
            entity_id="invalid_player",
            player_id="invalid_player", 
            name="InvalidPlayer",
            position=Vector2(0.0, 0.0),
            mass=-10.0,  # Invalid negative mass
            radius=15.0
        )
        validate_player(invalid_player)
        print("✗ Should have failed validation")
    except ValidationError as e:
        print(f"✓ Correctly caught validation error: {e}")
    except Exception as e:
        print(f"✓ Validation prevented creation: {type(e).__name__}")


def data_pipeline_example():
    """Demonstrate comprehensive data pipeline usage."""
    print("=== Data Pipeline Example ===")
    
    # Create sample game objects
    players = [
        GamePlayer(
            entity_id=f"player_{i}",
            player_id=f"player_{i}",
            name=f"Player{i}",
            position=Vector2(float(i * 50), float(i * 30)),
            velocity=Vector2(float(i * 2), float(i * -1)),
            mass=50.0 + i * 5,
            radius=20.0 + i * 2,
            score=i * 100
        )
        for i in range(1, 4)
    ]
    
    circles = [
        GameCircle(
            entity_id=f"circle_{i}",
            circle_id=f"circle_{i}",
            position=Vector2(float(i * 80), float(i * 60)),
            mass=5.0,
            radius=8.0,
            circle_type="food",
            value=10 + i
        )
        for i in range(1, 6)
    ]
    
    print(f"Created {len(players)} players and {len(circles)} circles")
    
    # Configure pipeline for different server scenarios
    pipeline_configs = [
        {
            'name': 'Rust Production',
            'config': PipelineConfiguration(
                server_language=ServerLanguage.RUST,
                serialization_format=SerializationFormat.JSON,
                enable_validation=True,
                enable_protocol_adaptation=True,
                enable_compression=False
            )
        },
        {
            'name': 'C# Development',
            'config': PipelineConfiguration(
                server_language=ServerLanguage.CSHARP,
                serialization_format=SerializationFormat.JSON,
                enable_validation=True,
                enable_protocol_adaptation=True,
                enable_compression=False
            )
        },
        {
            'name': 'Go High-Performance',
            'config': PipelineConfiguration(
                server_language=ServerLanguage.GO,
                serialization_format=SerializationFormat.BINARY,
                enable_validation=False,  # Skip validation for performance
                enable_protocol_adaptation=True,
                enable_compression=True
            )
        }
    ]
    
    for scenario in pipeline_configs:
        print(f"\n--- {scenario['name']} Scenario ---")
        pipeline = DataPipeline(scenario['config'])
        
        # Process outbound data (client to server)
        start_time = time.time()
        
        # Process players batch
        players_data = pipeline.process_outbound(players)
        players_time = time.time() - start_time
        
        # Process circles batch
        start_time = time.time()
        circles_data = pipeline.process_outbound(circles)
        circles_time = time.time() - start_time
        
        print(f"Outbound processing:")
        print(f"  Players: {len(players_data)} bytes in {players_time:.4f}s")
        print(f"  Circles: {len(circles_data)} bytes in {circles_time:.4f}s")
        
        # Process inbound data (server to client)
        start_time = time.time()
        restored_players = pipeline.process_inbound(players_data, GamePlayer)
        restore_time = time.time() - start_time
        
        print(f"Inbound processing:")
        print(f"  Restored {len(restored_players)} players in {restore_time:.4f}s")
        
        # Verify data integrity
        original_names = [p.name for p in players]
        restored_names = [p.name for p in restored_players]
        integrity_check = original_names == restored_names
        
        print(f"  Data integrity: {'✓ Passed' if integrity_check else '✗ Failed'}")
        
        # Show pipeline metrics
        metrics = pipeline.get_metrics()
        print(f"Pipeline metrics:")
        print(f"  Success rate: {metrics['success_rate']:.1f}%")
        print(f"  Avg processing time: {metrics['average_processing_time']:.4f}s")
        print(f"  Objects processed: {metrics['objects_processed']}")


async def async_pipeline_example():
    """Demonstrate asynchronous data pipeline usage."""
    print("=== Async Pipeline Example ===")
    
    # Create pipeline with async enabled
    config = PipelineConfiguration(
        server_language=ServerLanguage.PYTHON,
        serialization_format=SerializationFormat.JSON,
        enable_async=True
    )
    pipeline = DataPipeline(config)
    
    # Create sample data
    entities = [
        GameEntity(
            entity_id=f"async_entity_{i}",
            position=Vector2(float(i * 25), float(i * 35)),
            velocity=Vector2(float(i), float(-i)),
            mass=10.0 + i,
            radius=5.0 + i,
            entity_type=EntityType.CIRCLE
        )
        for i in range(1, 11)
    ]
    
    print(f"Processing {len(entities)} entities asynchronously...")
    
    # Process multiple batches concurrently
    tasks = []
    batch_size = 3
    
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]
        task = pipeline.process_outbound_async(batch)
        tasks.append(task)
    
    # Wait for all processing to complete
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    processing_time = time.time() - start_time
    
    total_bytes = sum(len(data) for data in results)
    print(f"Processed {len(results)} batches in {processing_time:.4f}s")
    print(f"Total data: {total_bytes} bytes")
    
    # Process one batch back asynchronously
    if results:
        restored_entities = await pipeline.process_inbound_async(results[0], GameEntity)
        print(f"Restored {len(restored_entities)} entities from first batch")
    
    pipeline.close()


def migration_helper_example():
    """Demonstrate migration helpers for existing codebases."""
    print("=== Migration Helper Example ===")
    
    # Simulate legacy data format from blackholio-agent
    legacy_player_data = {
        'id': 'legacy_player_001',
        'name': 'LegacyPlayer',
        'x': 125.0,
        'y': 175.0,
        'vx': 15.0,
        'vy': -8.0,
        'mass': 45.0,
        'radius': 22.5,
        'score': 750,
        'active': True
    }
    
    print("Legacy player data format:")
    for key, value in legacy_player_data.items():
        print(f"  {key}: {value}")
    
    # Convert to modern format using data converters
    from blackholio_client.models import PlayerConverter
    converter = PlayerConverter()
    
    # The converter handles field mapping automatically
    modern_player = converter.from_dict(legacy_player_data)
    print(f"\nConverted to modern format:")
    print(f"  Player: {modern_player.name}")
    print(f"  Position: {modern_player.position}")
    print(f"  Velocity: {modern_player.velocity}")
    print(f"  Score: {modern_player.score}")
    
    # Show how the modern format works with all servers
    for server_lang in [ServerLanguage.RUST, ServerLanguage.CSHARP, ServerLanguage.GO]:
        serialized = serialize(modern_player, SerializationFormat.JSON, server_lang)
        print(f"  {server_lang.value} format: {len(serialized)} bytes")


def performance_comparison_example():
    """Demonstrate performance characteristics of different configurations."""
    print("=== Performance Comparison Example ===")
    
    # Create substantial test data
    large_dataset = [
        GamePlayer(
            entity_id=f"perf_player_{i}",
            player_id=f"perf_player_{i}",
            name=f"Player{i:04d}",
            position=Vector2(float(i % 1000), float(i % 800)),
            velocity=Vector2(float(i % 50 - 25), float(i % 40 - 20)),
            mass=50.0 + (i % 100),
            radius=20.0 + (i % 20),
            score=i * 10
        )
        for i in range(100)  # 100 players for performance test
    ]
    
    print(f"Testing with {len(large_dataset)} players")
    
    # Test different configurations
    test_configs = [
        ('JSON + Validation', {
            'serialization_format': SerializationFormat.JSON,
            'enable_validation': True,
            'enable_protocol_adaptation': True
        }),
        ('JSON - Validation', {
            'serialization_format': SerializationFormat.JSON,
            'enable_validation': False,
            'enable_protocol_adaptation': True
        }),
        ('Binary + Validation', {
            'serialization_format': SerializationFormat.BINARY,
            'enable_validation': True,
            'enable_protocol_adaptation': True
        }),
        ('Binary - Validation', {
            'serialization_format': SerializationFormat.BINARY,
            'enable_validation': False,
            'enable_protocol_adaptation': False
        })
    ]
    
    for config_name, config_params in test_configs:
        config = PipelineConfiguration(
            server_language=ServerLanguage.RUST,
            **config_params
        )
        pipeline = DataPipeline(config)
        
        # Measure processing time
        start_time = time.time()
        serialized_data = pipeline.process_outbound(large_dataset)
        processing_time = time.time() - start_time
        
        # Measure restoration time
        start_time = time.time()
        restored_data = pipeline.process_inbound(serialized_data, GamePlayer)
        restoration_time = time.time() - start_time
        
        metrics = pipeline.get_metrics()
        
        print(f"\n{config_name}:")
        print(f"  Processing: {processing_time:.4f}s")
        print(f"  Restoration: {restoration_time:.4f}s")
        print(f"  Data size: {len(serialized_data)} bytes")
        print(f"  Throughput: {len(large_dataset) / (processing_time + restoration_time):.1f} objects/sec")
        print(f"  Success rate: {metrics['success_rate']:.1f}%")


def main():
    """Run all examples."""
    print("Blackholio Client - Data Models Examples")
    print("=" * 50)
    
    basic_serialization_example()
    print("\n" + "=" * 50)
    
    protocol_adaptation_example()
    print("\n" + "=" * 50)
    
    validation_example()
    print("\n" + "=" * 50)
    
    data_pipeline_example()
    print("\n" + "=" * 50)
    
    migration_helper_example()
    print("\n" + "=" * 50)
    
    performance_comparison_example()
    print("\n" + "=" * 50)
    
    # Run async example
    print("Running async example...")
    asyncio.run(async_pipeline_example())
    
    print("\nAll examples completed successfully!")


if __name__ == "__main__":
    main()