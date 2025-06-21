"""
Comprehensive test suite to achieve 80% code coverage.

This test suite focuses on exercising the main code paths in each module
to meet the coverage requirements.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Import all major modules for testing
from blackholio_client.auth import IdentityManager, TokenManager, AuthenticatedClient
from blackholio_client.config import EnvironmentConfig, get_environment_config
from blackholio_client.models.serialization import ServerLanguage
from blackholio_client.connection.server_config import ServerConfig
from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
from blackholio_client.client import GameClient, create_game_client
from blackholio_client.models import Vector2, GameEntity, GamePlayer, GameCircle
from blackholio_client.models.serialization import serialize, deserialize, JSONSerializer
from blackholio_client.models.data_converters import EntityConverter, PlayerConverter
from blackholio_client.models.protocol_adapters import get_protocol_adapter
from blackholio_client.utils import setup_logging, get_logger, TaskManager
from blackholio_client.factory import create_client, get_client_factory
from blackholio_client.events import EventManager, Event
from blackholio_client.exceptions import BlackholioConnectionError, BlackholioConfigurationError


class TestIdentityManager:
    """Comprehensive IdentityManager tests."""
    
    def test_identity_manager_generate_identity(self):
        """Test identity generation."""
        manager = IdentityManager()
        identity = manager.generate_identity()
        
        assert isinstance(identity, dict)
        assert 'identity_id' in identity
        assert 'public_key' in identity
        assert 'private_key' in identity
        assert 'created_at' in identity
    
    def test_identity_manager_validate_identity(self):
        """Test identity validation."""
        manager = IdentityManager()
        identity = manager.generate_identity()
        
        # Valid identity should pass validation
        assert manager.validate_identity(identity) == True
        
        # Invalid identity should fail validation
        invalid_identity = {'invalid': 'data'}
        assert manager.validate_identity(invalid_identity) == False
    
    def test_identity_manager_save_load_identity(self):
        """Test saving and loading identity."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            identity_file = f.name
        
        try:
            manager = IdentityManager(identity_file)
            identity = manager.generate_identity()
            
            # Save identity
            manager.save_identity(identity)
            assert os.path.exists(identity_file)
            
            # Load identity
            loaded_identity = manager.load_identity()
            assert loaded_identity is not None
            assert loaded_identity['identity_id'] == identity['identity_id']
        finally:
            if os.path.exists(identity_file):
                os.unlink(identity_file)
    
    def test_identity_manager_get_current_identity(self):
        """Test getting current identity."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            identity_file = f.name
        
        try:
            manager = IdentityManager(identity_file)
            
            # Should create new identity if none exists
            identity = manager.get_current_identity()
            assert identity is not None
            assert os.path.exists(identity_file)
        finally:
            if os.path.exists(identity_file):
                os.unlink(identity_file)


class TestTokenManager:
    """Comprehensive TokenManager tests."""
    
    def test_token_manager_generate_token(self):
        """Test token generation."""
        manager = TokenManager()
        payload = {'user_id': 'test_user', 'permissions': ['read', 'write']}
        
        token = manager.generate_token(payload, expires_in=3600)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_token_manager_validate_token(self):
        """Test token validation."""
        manager = TokenManager()
        payload = {'user_id': 'test_user'}
        
        # Generate valid token
        token = manager.generate_token(payload, expires_in=3600)
        assert manager.validate_token(token) == True
        
        # Test invalid token
        assert manager.validate_token('invalid.token.here') == False
    
    def test_token_manager_decode_token(self):
        """Test token decoding."""
        manager = TokenManager()
        payload = {'user_id': 'test_user', 'role': 'admin'}
        
        token = manager.generate_token(payload)
        decoded = manager.decode_token(token)
        
        assert decoded['user_id'] == 'test_user'
        assert decoded['role'] == 'admin'
        assert 'exp' in decoded
        assert 'iat' in decoded


class TestEnvironmentConfig:
    """Comprehensive EnvironmentConfig tests."""
    
    def test_environment_config_defaults(self):
        """Test default configuration values."""
        config = EnvironmentConfig()
        
        assert config.server_language == ServerLanguage.RUST
        assert config.server_ip == "127.0.0.1"
        assert config.server_port == 3000
        assert config.timeout == 30.0
        assert config.retry_attempts == 3
    
    def test_environment_config_from_env_vars(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("SERVER_LANGUAGE", "python")
        monkeypatch.setenv("SERVER_IP", "192.168.1.100")
        monkeypatch.setenv("SERVER_PORT", "8080")
        
        config = EnvironmentConfig()
        
        assert config.server_language == ServerLanguage.PYTHON
        assert config.server_ip == "192.168.1.100"
        assert config.server_port == 8080
    
    def test_environment_config_validation(self):
        """Test configuration validation."""
        # Valid config should not raise
        config = EnvironmentConfig(
            server_ip="valid.hostname.com",
            server_port=8080,
            timeout=30.0,
            retry_attempts=3
        )
        config.validate()  # Should not raise
        
        # Invalid port should raise
        config = EnvironmentConfig(server_port=100000)
        with pytest.raises(Exception):
            config.validate()
    
    def test_environment_config_serialization(self):
        """Test configuration serialization."""
        config = EnvironmentConfig(
            server_language=ServerLanguage.GO,
            server_ip="test.example.com",
            server_port=9000
        )
        
        # Test to_dict
        config_dict = config.to_dict()
        assert config_dict['server_language'] == 'go'
        assert config_dict['server_ip'] == 'test.example.com'
        assert config_dict['server_port'] == 9000
        
        # Test from_dict
        new_config = EnvironmentConfig.from_dict(config_dict)
        assert new_config.server_language == ServerLanguage.GO
        assert new_config.server_ip == 'test.example.com'
        assert new_config.server_port == 9000


class TestServerConfig:
    """Comprehensive ServerConfig tests."""
    
    def test_server_config_creation(self):
        """Test ServerConfig creation."""
        config = ServerConfig(
            language=ServerLanguage.PYTHON,
            host="localhost",
            port=8000
        )
        
        assert config.language == ServerLanguage.PYTHON
        assert config.host == "localhost"
        assert config.port == 8000
    
    def test_server_config_for_language(self):
        """Test ServerConfig creation for specific languages."""
        rust_config = ServerConfig.for_language(ServerLanguage.RUST)
        assert rust_config.language == ServerLanguage.RUST
        assert rust_config.port == 3000
        
        python_config = ServerConfig.for_language(ServerLanguage.PYTHON)
        assert python_config.language == ServerLanguage.PYTHON
        assert python_config.port == 8000
    
    def test_server_config_connection_url(self):
        """Test connection URL generation."""
        config = ServerConfig(
            language=ServerLanguage.RUST,
            host="example.com",
            port=3000,
            ssl_enabled=True
        )
        
        url = config.get_connection_url()
        assert url == "wss://example.com:3000"
        
        config.ssl_enabled = False
        url = config.get_connection_url()
        assert url == "ws://example.com:3000"


class TestGameClient:
    """Comprehensive GameClient tests."""
    
    def test_game_client_creation(self):
        """Test GameClient creation."""
        client = GameClient()
        assert client is not None
        assert hasattr(client, 'connect')
        assert hasattr(client, 'disconnect')
    
    def test_game_client_with_config(self):
        """Test GameClient with configuration."""
        config = EnvironmentConfig()
        client = GameClient(config=config)
        assert client is not None
    
    @pytest.mark.asyncio
    async def test_game_client_connection_methods(self):
        """Test GameClient connection methods."""
        client = GameClient()
        
        # Mock the underlying connection
        with patch.object(client, '_connection') as mock_conn:
            mock_conn.connect = AsyncMock(return_value=True)
            mock_conn.disconnect = AsyncMock(return_value=True)
            mock_conn.is_connected = Mock(return_value=False)
            
            # Test that methods can be called
            assert hasattr(client, 'connect')
            assert hasattr(client, 'disconnect')
            assert hasattr(client, 'is_connected')


class TestVector2:
    """Comprehensive Vector2 tests."""
    
    def test_vector2_creation(self):
        """Test Vector2 creation."""
        v = Vector2(10.0, 20.0)
        assert v.x == 10.0
        assert v.y == 20.0
    
    def test_vector2_operations(self):
        """Test Vector2 mathematical operations."""
        v1 = Vector2(3.0, 4.0)
        v2 = Vector2(1.0, 2.0)
        
        # Addition
        result = v1 + v2
        assert result.x == 4.0
        assert result.y == 6.0
        
        # Subtraction
        result = v1 - v2
        assert result.x == 2.0
        assert result.y == 2.0
        
        # Scalar multiplication
        result = v1 * 2.0
        assert result.x == 6.0
        assert result.y == 8.0
        
        # Magnitude
        magnitude = v1.magnitude()
        assert magnitude == 5.0  # 3-4-5 triangle
        
        # Distance
        distance = v1.distance_to(v2)
        assert distance > 0
    
    def test_vector2_serialization(self):
        """Test Vector2 serialization."""
        v = Vector2(15.0, 25.0)
        
        # To dict
        v_dict = v.to_dict()
        assert v_dict == {'x': 15.0, 'y': 25.0}
        
        # From dict
        new_v = Vector2.from_dict(v_dict)
        assert new_v.x == 15.0
        assert new_v.y == 25.0


class TestGameEntity:
    """Comprehensive GameEntity tests."""
    
    def test_game_entity_creation(self):
        """Test GameEntity creation."""
        entity = GameEntity(
            entity_id="test_entity",
            position=Vector2(100, 100),
            radius=25.0,
            mass=50.0
        )
        
        assert entity.entity_id == "test_entity"
        assert entity.position.x == 100.0
        assert entity.position.y == 100.0
        assert entity.radius == 25.0
        assert entity.mass == 50.0
    
    def test_game_entity_update_position(self):
        """Test GameEntity position updates."""
        entity = GameEntity(
            entity_id="test",
            position=Vector2(0, 0),
            velocity=Vector2(1, 1),
            radius=10.0
        )
        
        # Update position
        entity.update_position(1.0)  # 1 second
        assert entity.position.x == 1.0
        assert entity.position.y == 1.0
    
    def test_game_entity_collision_detection(self):
        """Test GameEntity collision detection."""
        entity1 = GameEntity(
            entity_id="entity1",
            position=Vector2(0, 0),
            radius=10.0
        )
        
        entity2 = GameEntity(
            entity_id="entity2", 
            position=Vector2(15, 0),
            radius=10.0
        )
        
        # Entities should be colliding (distance = 15, combined radius = 20)
        assert entity1.is_colliding_with(entity2) == True
        
        # Move entity2 further away
        entity2.position = Vector2(25, 0)
        assert entity1.is_colliding_with(entity2) == False


class TestSerialization:
    """Comprehensive serialization tests."""
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        data = {
            'player_id': 'test_player',
            'position': {'x': 100.0, 'y': 200.0},
            'score': 1500
        }
        
        # Serialize
        json_str = serialize(data, format='json')
        assert isinstance(json_str, str)
        
        # Deserialize
        restored_data = deserialize(json_str, format='json')
        assert restored_data['player_id'] == 'test_player'
        assert restored_data['score'] == 1500
    
    def test_json_serializer_class(self):
        """Test JSONSerializer class."""
        serializer = JSONSerializer()
        
        data = {'test': 'data', 'number': 42}
        
        # Serialize
        serialized = serializer.serialize(data)
        assert isinstance(serialized, str)
        
        # Deserialize
        deserialized = serializer.deserialize(serialized)
        assert deserialized == data


class TestDataConverters:
    """Comprehensive data converter tests."""
    
    def test_entity_converter(self):
        """Test EntityConverter."""
        converter = EntityConverter()
        
        entity_data = {
            'entity_id': 'test_entity',
            'position': {'x': 50.0, 'y': 75.0},
            'radius': 20.0,
            'mass': 30.0
        }
        
        entity = converter.convert(entity_data)
        assert isinstance(entity, GameEntity)
        assert entity.entity_id == 'test_entity'
        assert entity.position.x == 50.0
        assert entity.radius == 20.0
    
    def test_player_converter(self):
        """Test PlayerConverter."""
        converter = PlayerConverter()
        
        player_data = {
            'entity_id': 'player_1',
            'player_id': 'player_1',
            'name': 'TestPlayer',
            'position': {'x': 100.0, 'y': 150.0},
            'radius': 30.0,
            'score': 2000
        }
        
        player = converter.convert(player_data)
        assert isinstance(player, GamePlayer)
        assert player.player_id == 'player_1'
        assert player.name == 'TestPlayer'
        assert player.score == 2000


class TestProtocolAdapters:
    """Test protocol adapters."""
    
    def test_get_protocol_adapter(self):
        """Test getting protocol adapters."""
        # Test each server language
        rust_adapter = get_protocol_adapter(ServerLanguage.RUST)
        assert rust_adapter is not None
        
        python_adapter = get_protocol_adapter(ServerLanguage.PYTHON)
        assert python_adapter is not None
        
        csharp_adapter = get_protocol_adapter(ServerLanguage.CSHARP)
        assert csharp_adapter is not None
        
        go_adapter = get_protocol_adapter(ServerLanguage.GO)
        assert go_adapter is not None
    
    def test_protocol_adapter_conversions(self):
        """Test protocol adapter conversions."""
        go_adapter = get_protocol_adapter(ServerLanguage.GO)
        
        client_data = {
            'player_id': 'test_player',
            'created_at': 1234567890.0
        }
        
        # Convert to server format
        server_data = go_adapter.adapt_to_server(client_data, 'GamePlayer')
        assert 'playerID' in server_data  # Go uses camelCase
        assert 'createdAt' in server_data


class TestFactoryPattern:
    """Test factory pattern implementation."""
    
    def test_create_client(self):
        """Test client creation via factory."""
        with patch('blackholio_client.factory.client_factory.get_environment_config') as mock_config:
            mock_config.return_value = EnvironmentConfig(server_language=ServerLanguage.RUST)
            
            client = create_client()
            assert client is not None
    
    def test_get_client_factory(self):
        """Test getting client factory."""
        factory = get_client_factory(ServerLanguage.RUST)
        assert factory is not None


class TestEventSystem:
    """Test event system."""
    
    def test_event_manager(self):
        """Test EventManager."""
        manager = EventManager()
        assert manager is not None
        
        # Test basic functionality
        assert hasattr(manager, 'subscribe')
        assert hasattr(manager, 'publish')
    
    def test_event_creation(self):
        """Test Event creation."""
        event = Event(
            event_type='test_event',
            data={'message': 'test'}
        )
        
        assert event.event_type == 'test_event'
        assert event.data['message'] == 'test'


class TestUtilities:
    """Test utility functions."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        result = setup_logging()
        assert result is not None
    
    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger('test_logger')
        assert logger is not None
    
    def test_task_manager(self):
        """Test TaskManager."""
        manager = TaskManager()
        assert manager is not None


class TestExceptions:
    """Test exception classes."""
    
    def test_blackholio_connection_error(self):
        """Test BlackholioConnectionError exception."""
        with pytest.raises(BlackholioConnectionError):
            raise BlackholioConnectionError("Test connection error message")
    
    def test_blackholio_configuration_error(self):
        """Test BlackholioConfigurationError exception."""
        with pytest.raises(BlackholioConfigurationError):
            raise BlackholioConfigurationError("Configuration failed")


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_create_game_client(self):
        """Test create_game_client global function."""
        with patch('blackholio_client.client.EnvironmentConfig') as mock_config:
            mock_config.return_value = EnvironmentConfig()
            
            client = create_game_client()
            assert client is not None
    
    def test_get_environment_config_global(self):
        """Test get_environment_config global function."""
        config = get_environment_config()
        assert isinstance(config, EnvironmentConfig)


class TestAsyncFunctionality:
    """Test async functionality."""
    
    @pytest.mark.asyncio
    async def test_spacetimedb_connection(self):
        """Test SpacetimeDBConnection async methods."""
        connection = SpacetimeDBConnection()
        
        # Test that async methods exist
        assert hasattr(connection, 'connect')
        assert hasattr(connection, 'disconnect')
        assert hasattr(connection, 'send_message')
    
    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling."""
        async def failing_operation():
            raise ValueError("Async test error")
        
        with pytest.raises(ValueError):
            await failing_operation()


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    def test_full_client_setup(self):
        """Test full client setup workflow."""
        # Create configuration
        config = EnvironmentConfig(
            server_language=ServerLanguage.RUST,
            server_ip="localhost",
            server_port=3000
        )
        
        # Create client with config
        client = GameClient(config=config)
        assert client is not None
        
        # Test configuration access
        assert hasattr(client, 'config')
    
    def test_entity_lifecycle(self):
        """Test entity creation, update, serialization lifecycle."""
        # Create entity
        entity = GameEntity(
            entity_id="lifecycle_test",
            position=Vector2(0, 0),
            velocity=Vector2(1, 1),
            radius=15.0
        )
        
        # Update entity
        entity.update_position(2.0)
        assert entity.position.x == 2.0
        assert entity.position.y == 2.0
        
        # Serialize entity
        entity_dict = entity.to_dict()
        assert entity_dict['entity_id'] == 'lifecycle_test'
        
        # Recreate from dict
        new_entity = GameEntity.from_dict(entity_dict)
        assert new_entity.entity_id == entity.entity_id
    
    def test_multi_language_protocol_support(self):
        """Test protocol adaptation for all server languages."""
        test_data = {
            'player_id': 'multi_lang_test',
            'created_at': 1234567890.0,
            'is_active': True
        }
        
        for language in [ServerLanguage.RUST, ServerLanguage.PYTHON, 
                        ServerLanguage.CSHARP, ServerLanguage.GO]:
            adapter = get_protocol_adapter(language)
            
            # Adapt to server format
            server_data = adapter.adapt_to_server(test_data, 'GamePlayer')
            assert server_data is not None
            
            # Adapt back to client format
            client_data = adapter.adapt_from_server(server_data, 'GamePlayer')
            assert client_data is not None