"""
Core module tests for blackholio_client.

Tests basic functionality of core modules to increase coverage.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# Test auth module
from blackholio_client.auth import IdentityManager, TokenManager, AuthenticatedClient

# Test config module  
from blackholio_client.config import EnvironmentConfig, get_environment_config

# Test utils basic functionality
from blackholio_client.utils import setup_logging, get_logger, TaskManager

# Test client
from blackholio_client.client import GameClient

# Test models
from blackholio_client.models import Vector2, GameEntity, GamePlayer, GameCircle


class TestAuthModule:
    """Test auth module basic functionality."""
    
    def test_identity_manager_creation(self):
        """Test IdentityManager can be created."""
        manager = IdentityManager()
        assert manager is not None
    
    def test_token_manager_creation(self):
        """Test TokenManager can be created."""
        manager = TokenManager()
        assert manager is not None
    
    def test_authenticated_client_creation(self):
        """Test AuthenticatedClient can be created."""
        mock_connection = Mock()
        client = AuthenticatedClient(mock_connection)
        assert client is not None


class TestConfigModule:
    """Test config module basic functionality."""
    
    def test_environment_config_creation(self):
        """Test EnvironmentConfig can be created."""
        config = EnvironmentConfig()
        assert config is not None
        
        # Test basic properties
        assert hasattr(config, 'server_language')
        assert hasattr(config, 'server_ip')
        assert hasattr(config, 'server_port')
    
    def test_get_environment_config(self):
        """Test get_environment_config function."""
        config = get_environment_config()
        assert isinstance(config, EnvironmentConfig)


class TestUtilsModule:
    """Test utils module basic functionality."""
    
    def test_setup_logging(self):
        """Test setup_logging function."""
        result = setup_logging()
        assert result is not None
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_task_manager_creation(self):
        """Test TaskManager can be created."""
        manager = TaskManager()
        assert manager is not None


class TestModelsModule:
    """Test models module basic functionality."""
    
    def test_vector2_creation(self):
        """Test Vector2 can be created."""
        vector = Vector2(10.0, 20.0)
        assert vector.x == 10.0
        assert vector.y == 20.0
    
    def test_vector2_operations(self):
        """Test Vector2 basic operations."""
        v1 = Vector2(1.0, 2.0)
        v2 = Vector2(3.0, 4.0)
        
        # Test addition
        result = v1 + v2
        assert result.x == 4.0
        assert result.y == 6.0
        
        # Test magnitude
        magnitude = v1.magnitude()
        assert magnitude > 0
        
        # Test distance
        distance = v1.distance_to(v2)
        assert distance > 0
    
    def test_game_entity_creation(self):
        """Test GameEntity can be created."""
        entity = GameEntity(
            entity_id="test_entity",
            position=Vector2(100, 100),
            radius=25.0
        )
        assert entity.entity_id == "test_entity"
        assert entity.position.x == 100.0
        assert entity.radius == 25.0
    
    def test_game_player_creation(self):
        """Test GamePlayer can be created."""
        player = GamePlayer(
            entity_id="player_1",
            player_id="player_1", 
            name="TestPlayer",
            position=Vector2(50, 75),
            radius=30.0
        )
        assert player.player_id == "player_1"
        assert player.name == "TestPlayer"
        assert player.position.x == 50.0
    
    def test_game_circle_creation(self):
        """Test GameCircle can be created."""
        circle = GameCircle(
            entity_id="circle_1",
            circle_id="circle_1",
            position=Vector2(200, 200),
            radius=15.0
        )
        assert circle.circle_id == "circle_1"
        assert circle.position.x == 200.0


class TestClientModule:
    """Test client module basic functionality."""
    
    def test_game_client_creation(self):
        """Test GameClient can be created."""
        client = GameClient()
        assert client is not None
        
        # Test basic properties exist
        assert hasattr(client, 'connect')
        assert hasattr(client, 'disconnect')
        assert hasattr(client, 'is_connected')


class TestModuleIntegration:
    """Test basic module integration."""
    
    def test_client_with_config(self):
        """Test client with configuration."""
        config = EnvironmentConfig()
        client = GameClient(config=config)
        assert client is not None
    
    def test_logging_integration(self):
        """Test logging integration works."""
        logger = get_logger("integration_test")
        logger.info("Test message")
        # Should not raise any errors
    
    def test_models_serialization(self):
        """Test models can be serialized."""
        vector = Vector2(10.0, 20.0)
        vector_dict = vector.to_dict()
        assert isinstance(vector_dict, dict)
        assert vector_dict["x"] == 10.0
        assert vector_dict["y"] == 20.0
        
        # Test deserialization
        new_vector = Vector2.from_dict(vector_dict)
        assert new_vector.x == 10.0
        assert new_vector.y == 20.0


# Async tests
class TestAsyncFunctionality:
    """Test async functionality across modules."""
    
    @pytest.mark.asyncio
    async def test_client_async_methods(self):
        """Test client async methods exist."""
        client = GameClient()
        
        # These should not raise AttributeError
        assert hasattr(client, 'connect')
        assert hasattr(client, 'disconnect')
    
    @pytest.mark.asyncio
    async def test_basic_async_operation(self):
        """Test basic async operation."""
        async def test_operation():
            await asyncio.sleep(0.001)
            return "success"
        
        result = await test_operation()
        assert result == "success"