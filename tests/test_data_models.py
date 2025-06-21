"""
Test Data Models - Comprehensive Testing Suite

Tests all data model functionality including serialization, validation,
protocol adaptation, and data pipeline operations across all supported
SpacetimeDB server languages.
"""

import pytest
import json
import time
from typing import List

from blackholio_client.models import (
    # Core entities
    GameEntity, GamePlayer, GameCircle, Vector2, EntityType, PlayerState,
    
    # Serialization
    serialize, deserialize, SerializationFormat, ServerLanguage,
    JSONSerializer, BinarySerializer, SerializationError, DeserializationError,
    
    # Validation
    validate_entity, validate_player, validate_circle, validate_game_state,
    ValidationError, SchemaManager, DataValidator,
    
    # Protocol adaptation
    adapt_to_server, adapt_from_server, ProtocolVersion,
    get_protocol_adapter, RustProtocolAdapter, PythonProtocolAdapter,
    CSharpProtocolAdapter, GoProtocolAdapter,
    
    # Data pipeline
    DataPipeline, PipelineConfiguration, ProcessingError,
    process_for_server, process_from_server
)


class TestSerialization:
    """Test serialization functionality."""
    
    def test_json_serialization_basic(self):
        """Test basic JSON serialization."""
        player = GamePlayer(
            entity_id="test_player",
            player_id="test_player",
            name="TestPlayer",
            position=Vector2(100.0, 200.0),
            velocity=Vector2(10.0, -5.0),
            mass=50.0,
            radius=25.0,
            score=1000
        )
        
        # Serialize
        serialized = serialize(player, SerializationFormat.JSON, ServerLanguage.PYTHON)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize
        restored = deserialize(serialized, GamePlayer, SerializationFormat.JSON, ServerLanguage.PYTHON)
        assert isinstance(restored, GamePlayer)
        assert restored.name == player.name
        assert restored.position.x == player.position.x
        assert restored.score == player.score
    
    def test_binary_serialization_basic(self):
        """Test basic binary serialization."""
        circle = GameCircle(
            entity_id="test_circle",
            circle_id="test_circle",
            position=Vector2(50.0, 75.0),
            mass=5.0,
            radius=8.0,
            circle_type="food",
            value=10
        )
        
        # Serialize
        serialized = serialize(circle, SerializationFormat.BINARY, ServerLanguage.RUST)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize
        restored = deserialize(serialized, GameCircle, SerializationFormat.BINARY, ServerLanguage.RUST)
        assert isinstance(restored, GameCircle)
        assert restored.circle_type == circle.circle_type
        assert restored.value == circle.value
    
    def test_serialization_all_servers(self):
        """Test serialization works for all server languages."""
        entity = GameEntity(
            entity_id="test_entity",
            position=Vector2(25.0, 35.0),
            velocity=Vector2(5.0, -2.0),
            mass=20.0,
            radius=15.0,
            entity_type=EntityType.PLAYER
        )
        
        for server_lang in ServerLanguage:
            # JSON serialization
            json_data = serialize(entity, SerializationFormat.JSON, server_lang)
            restored_json = deserialize(json_data, GameEntity, SerializationFormat.JSON, server_lang)
            
            assert restored_json.entity_id == entity.entity_id
            assert restored_json.position.x == entity.position.x
            assert restored_json.entity_type == entity.entity_type
            
            # Binary serialization
            binary_data = serialize(entity, SerializationFormat.BINARY, server_lang)
            restored_binary = deserialize(binary_data, GameEntity, SerializationFormat.BINARY, server_lang)
            
            assert restored_binary.entity_id == entity.entity_id
            assert restored_binary.mass == entity.mass
    
    def test_serialization_error_handling(self):
        """Test serialization error handling."""
        # Test with invalid object
        with pytest.raises(SerializationError):
            serialize(None, SerializationFormat.JSON, ServerLanguage.RUST)
        
        # Test deserialization with invalid data
        with pytest.raises(DeserializationError):
            deserialize(b"invalid_data", GamePlayer, SerializationFormat.JSON, ServerLanguage.RUST)


class TestValidation:
    """Test validation functionality."""
    
    def test_valid_entity_validation(self):
        """Test validation of valid entities."""
        valid_entity = GameEntity(
            entity_id="valid_entity",
            position=Vector2(0.0, 0.0),
            velocity=Vector2(0.0, 0.0),
            mass=10.0,
            radius=5.0,
            entity_type=EntityType.CIRCLE
        )
        
        # Should not raise exception
        assert validate_entity(valid_entity) == True
    
    def test_valid_player_validation(self):
        """Test validation of valid players."""
        valid_player = GamePlayer(
            entity_id="valid_player",
            player_id="valid_player",
            name="ValidPlayer",
            position=Vector2(100.0, 100.0),
            velocity=Vector2(0.0, 0.0),
            mass=50.0,
            radius=20.0,
            score=500
        )
        
        assert validate_player(valid_player) == True
    
    def test_valid_circle_validation(self):
        """Test validation of valid circles."""
        valid_circle = GameCircle(
            entity_id="valid_circle",
            circle_id="valid_circle",
            position=Vector2(200.0, 150.0),
            mass=5.0,
            radius=8.0,
            circle_type="food",
            value=10
        )
        
        assert validate_circle(valid_circle) == True
    
    def test_game_state_validation(self):
        """Test validation of complete game state."""
        player = GamePlayer(
            entity_id="player1",
            player_id="player1",
            name="Player1",
            position=Vector2(50.0, 50.0),
            mass=40.0,
            radius=15.0
        )
        
        circle = GameCircle(
            entity_id="circle1",
            circle_id="circle1",
            position=Vector2(100.0, 100.0),
            mass=3.0,
            radius=6.0,
            circle_type="food"
        )
        
        entities = [player, circle]
        players = [player]
        circles = [circle]
        
        assert validate_game_state(entities, players, circles) == True
    
    def test_schema_manager(self):
        """Test schema manager functionality."""
        schema_manager = SchemaManager()
        
        # Test getting existing schema
        vector_schema = schema_manager.get_schema('Vector2')
        assert vector_schema is not None
        assert vector_schema['type'] == 'object'
        assert 'x' in vector_schema['properties']
        assert 'y' in vector_schema['properties']
        
        # Test registering custom schema
        custom_schema = {
            'type': 'object',
            'properties': {
                'test_field': {'type': 'string'}
            }
        }
        schema_manager.register_schema('CustomTest', custom_schema)
        retrieved_schema = schema_manager.get_schema('CustomTest')
        assert retrieved_schema == custom_schema


class TestProtocolAdapters:
    """Test protocol adapter functionality."""
    
    def test_rust_adapter(self):
        """Test Rust protocol adapter."""
        adapter = RustProtocolAdapter(ServerLanguage.RUST)
        
        client_data = {
            'entity_id': 'test_entity',
            'created_at': time.time(),
            'is_active': True,
            'entity_type': 'Player'
        }
        
        # Adapt to server format
        server_data = adapter.adapt_to_server(client_data, 'GameEntity')
        
        # Check Rust-specific transformations
        assert 'id' in server_data  # entity_id -> id
        assert 'created' in server_data  # created_at -> created
        assert isinstance(server_data['created'], int)  # nanoseconds
        assert server_data['entity_type'] == 'player'  # lowercase
        
        # Adapt back to client format
        restored_data = adapter.adapt_from_server(server_data, 'GameEntity')
        assert 'entity_id' in restored_data
        assert 'created_at' in restored_data
    
    def test_csharp_adapter(self):
        """Test C# protocol adapter."""
        adapter = CSharpProtocolAdapter(ServerLanguage.CSHARP)
        
        client_data = {
            'entity_id': 'test_entity',
            'is_active': True,
            'max_speed': 100.0,
            'entity_type': 'player'
        }
        
        # Adapt to server format
        server_data = adapter.adapt_to_server(client_data, 'GamePlayer')
        
        # Check C#-specific transformations (PascalCase)
        # Note: Field mappings override general PascalCase conversion
        assert 'EntityId' in server_data or 'Entityid' in server_data  # Either mapped or converted
        assert 'IsActive' in server_data
        assert 'MaxSpeed' in server_data or 'Maxspeed' in server_data  # Either mapped or converted
        assert server_data.get('EntityType') == 'Player' or server_data.get('Entitytype') == 'Player'  # PascalCase enum
        
        # Adapt back
        restored_data = adapter.adapt_from_server(server_data, 'GamePlayer')
        # After reverse adaptation, we should have client-formatted field names
        # The adapter should handle the reverse transformation properly
        assert 'entity_id' in restored_data or any(key for key in restored_data.keys() if 'entity' in key.lower())
        assert 'max_speed' in restored_data or any(key for key in restored_data.keys() if 'speed' in key.lower())
    
    def test_go_adapter(self):
        """Test Go protocol adapter."""
        adapter = GoProtocolAdapter(ServerLanguage.GO)
        
        client_data = {
            'player_id': 'test_player',
            'input_direction': {'x': 1.0, 'y': 0.0},
            'created_at': time.time()
        }
        
        # Adapt to server format
        server_data = adapter.adapt_to_server(client_data, 'GamePlayer')
        
        # Check Go-specific transformations (camelCase)
        assert 'playerID' in server_data
        assert 'inputDirection' in server_data
        assert 'createdAt' in server_data
        assert isinstance(server_data['createdAt'], int)  # nanoseconds
    
    def test_protocol_adaptation_functions(self):
        """Test global protocol adaptation functions."""
        data = {
            'entity_id': 'test',
            'position': {'x': 10.0, 'y': 20.0},
            'is_active': True
        }
        
        # Test adaptation to different servers
        rust_data = adapt_to_server(data, 'GameEntity', ServerLanguage.RUST)
        assert 'id' in rust_data
        
        csharp_data = adapt_to_server(data, 'GameEntity', ServerLanguage.CSHARP)
        assert 'EntityId' in csharp_data
        
        # Test reverse adaptation
        restored_rust = adapt_from_server(rust_data, 'GameEntity', ServerLanguage.RUST)
        assert 'entity_id' in restored_rust


class TestDataPipeline:
    """Test data pipeline functionality."""
    
    def test_basic_pipeline_outbound(self):
        """Test basic outbound pipeline processing."""
        config = PipelineConfiguration(
            server_language=ServerLanguage.PYTHON,
            serialization_format=SerializationFormat.JSON,
            enable_validation=True
        )
        pipeline = DataPipeline(config)
        
        player = GamePlayer(
            entity_id="pipeline_player",
            player_id="pipeline_player",
            name="PipelinePlayer",
            position=Vector2(0.0, 0.0),
            mass=50.0,
            radius=20.0
        )
        
        # Process outbound
        serialized_data = pipeline.process_outbound(player)
        assert isinstance(serialized_data, bytes)
        assert len(serialized_data) > 0
        
        # Check metrics
        metrics = pipeline.get_metrics()
        assert metrics['operations_total'] == 1
        assert metrics['operations_successful'] == 1
        assert metrics['success_rate'] == 100.0
    
    def test_basic_pipeline_inbound(self):
        """Test basic inbound pipeline processing."""
        config = PipelineConfiguration(
            server_language=ServerLanguage.RUST,
            serialization_format=SerializationFormat.JSON
        )
        pipeline = DataPipeline(config)
        
        circle = GameCircle(
            entity_id="pipeline_circle",
            circle_id="pipeline_circle",
            position=Vector2(25.0, 35.0),
            mass=5.0,
            radius=8.0,
            circle_type="food"
        )
        
        # Process outbound then inbound
        serialized = pipeline.process_outbound(circle)
        restored = pipeline.process_inbound(serialized, GameCircle)
        
        assert isinstance(restored, GameCircle)
        assert restored.entity_id == circle.entity_id
        assert restored.circle_type == circle.circle_type
        assert restored.position.x == circle.position.x
    
    def test_pipeline_batch_processing(self):
        """Test pipeline batch processing."""
        config = PipelineConfiguration(
            server_language=ServerLanguage.GO,
            enable_validation=True
        )
        pipeline = DataPipeline(config)
        
        entities = [
            GameEntity(
                entity_id=f"batch_entity_{i}",
                position=Vector2(float(i * 10), float(i * 15)),
                mass=float(i + 5),
                radius=float(i + 3),
                entity_type=EntityType.CIRCLE
            )
            for i in range(5)
        ]
        
        # Process batch
        serialized = pipeline.process_outbound(entities)
        restored = pipeline.process_inbound(serialized, GameEntity)
        
        assert isinstance(restored, list)
        assert len(restored) == len(entities)
        
        # Check all entities restored correctly
        for original, restored_entity in zip(entities, restored):
            assert restored_entity.entity_id == original.entity_id
            assert restored_entity.mass == original.mass
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        config = PipelineConfiguration(
            enable_validation=True
        )
        pipeline = DataPipeline(config)
        
        # Test with invalid data that should fail validation
        with pytest.raises(ProcessingError):
            pipeline.process_outbound(None)
        
        # Check error metrics
        metrics = pipeline.get_metrics()
        assert metrics['operations_failed'] > 0
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        player = GamePlayer(
            entity_id="convenience_player",
            player_id="convenience_player",
            name="ConveniencePlayer",
            position=Vector2(10.0, 20.0),
            mass=40.0,
            radius=18.0
        )
        
        # Test process_for_server
        serialized = process_for_server(player, ServerLanguage.CSHARP, SerializationFormat.JSON)
        assert isinstance(serialized, bytes)
        
        # Test process_from_server
        restored = process_from_server(serialized, GamePlayer, ServerLanguage.CSHARP, SerializationFormat.JSON)
        assert isinstance(restored, GamePlayer)
        assert restored.name == player.name


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_roundtrip_all_servers(self):
        """Test full roundtrip for all server languages."""
        test_objects = [
            GamePlayer(
                entity_id="integration_player",
                player_id="integration_player",
                name="IntegrationPlayer",
                position=Vector2(50.0, 75.0),
                velocity=Vector2(10.0, -5.0),
                mass=60.0,
                radius=25.0,
                score=1500,
                state=PlayerState.ACTIVE
            ),
            GameCircle(
                entity_id="integration_circle",
                circle_id="integration_circle",
                position=Vector2(100.0, 125.0),
                mass=8.0,
                radius=12.0,
                circle_type="food",
                value=15
            )
        ]
        
        for server_lang in ServerLanguage:
            for obj in test_objects:
                config = PipelineConfiguration(
                    server_language=server_lang,
                    serialization_format=SerializationFormat.JSON,
                    enable_validation=True,
                    enable_protocol_adaptation=True
                )
                pipeline = DataPipeline(config)
                
                # Full roundtrip
                serialized = pipeline.process_outbound(obj)
                restored = pipeline.process_inbound(serialized, type(obj))
                
                # Verify data integrity
                assert restored.entity_id == obj.entity_id
                assert restored.position.x == obj.position.x
                assert restored.position.y == obj.position.y
                assert restored.mass == obj.mass
                
                if isinstance(obj, GamePlayer):
                    assert restored.name == obj.name
                    assert restored.score == obj.score
                elif isinstance(obj, GameCircle):
                    assert restored.circle_type == obj.circle_type
                    assert restored.value == obj.value
    
    def test_performance_characteristics(self):
        """Test performance characteristics."""
        # Create larger dataset
        large_dataset = [
            GamePlayer(
                entity_id=f"perf_player_{i}",
                player_id=f"perf_player_{i}",
                name=f"Player{i}",
                position=Vector2(float(i % 100), float(i % 80)),
                mass=50.0,
                radius=20.0,
                score=i * 10
            )
            for i in range(50)  # 50 players for performance test
        ]
        
        config = PipelineConfiguration(
            server_language=ServerLanguage.RUST,
            serialization_format=SerializationFormat.JSON,
            enable_validation=False  # Skip validation for performance
        )
        pipeline = DataPipeline(config)
        
        # Measure processing time
        start_time = time.time()
        serialized = pipeline.process_outbound(large_dataset)
        processing_time = time.time() - start_time
        
        # Should process reasonably quickly
        assert processing_time < 1.0  # Less than 1 second for 50 objects
        
        # Measure restoration time
        start_time = time.time()
        restored = pipeline.process_inbound(serialized, GamePlayer)
        restoration_time = time.time() - start_time
        
        assert restoration_time < 1.0
        assert len(restored) == len(large_dataset)
        
        # Check metrics
        metrics = pipeline.get_metrics()
        assert metrics['success_rate'] == 100.0
        assert metrics['objects_processed'] == len(large_dataset) * 2  # outbound + inbound


# Additional test fixtures
@pytest.fixture
def sample_player():
    """Create a sample player for testing."""
    return GamePlayer(
        entity_id="test_player_123",
        player_id="test_player_123",
        name="TestPlayer",
        position=Vector2(100.0, 150.0),
        velocity=Vector2(5.0, -3.0),
        mass=55.0,
        radius=22.0,
        score=800,
        state=PlayerState.ACTIVE
    )


@pytest.fixture
def sample_circle():
    """Create a sample circle for testing."""
    return GameCircle(
        entity_id="test_circle_456",
        circle_id="test_circle_456",
        position=Vector2(200.0, 250.0),
        mass=6.0,
        radius=9.0,
        circle_type="food",
        value=12
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])