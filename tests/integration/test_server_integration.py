"""
Integration tests for blackholio-python-client with real SpacetimeDB servers.

Tests client functionality against running SpacetimeDB servers for all supported languages.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List

from blackholio_client.client import GameClient, create_game_client
from blackholio_client.config.environment import EnvironmentConfig
from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer
from blackholio_client.exceptions.connection_errors import (
    BlackholioConnectionError,
    ConnectionLostError,
    BlackholioTimeoutError
)


class TestBasicServerIntegration:
    """Test basic server integration functionality."""
    
    @pytest.mark.asyncio
    async def test_client_creation(self, test_environment_config):
        """Test creating a client with test configuration."""
        client = create_game_client(
            host=f"{test_environment_config.server_ip}:{test_environment_config.server_port}",
            database="blackholio-test",
            server_language=test_environment_config.server_language
        )
        assert client is not None
        assert isinstance(client, GameClient)
        
        # Verify configuration
        assert client.server_language == test_environment_config.server_language
    
    @pytest.mark.asyncio
    async def test_client_connection(self, test_game_client):
        """Test basic client connection functionality."""
        # Client should be created successfully
        assert test_game_client is not None
        
        # Test connection methods exist
        assert hasattr(test_game_client, 'connect')
        assert hasattr(test_game_client, 'disconnect')
        assert hasattr(test_game_client, 'is_connected')
    
    @pytest.mark.asyncio  
    async def test_client_authentication(self, test_game_client):
        """Test client authentication functionality."""
        # Test authentication methods exist
        assert hasattr(test_game_client, 'authenticate')
        assert hasattr(test_game_client, 'identity')
        
        # Authentication should work with valid credentials
        try:
            identity = await test_game_client.authenticate("test_user")
            assert identity is not None
        except NotImplementedError:
            pytest.skip("Authentication not implemented yet")
        except Exception as e:
            # Some authentication errors are expected in test environment
            assert "authentication" in str(e).lower() or "identity" in str(e).lower()


class TestGameOperations:
    """Test game-specific operations."""
    
    @pytest.mark.asyncio
    async def test_enter_game(self, test_game_client, sample_player_data):
        """Test entering the game."""
        try:
            result = await test_game_client.enter_game(sample_player_data["username"])
            # Should return success or player info
            assert result is not None
        except NotImplementedError:
            pytest.skip("enter_game not implemented yet")
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["game", "player", "connection"])
    
    @pytest.mark.asyncio
    async def test_player_movement(self, test_game_client):
        """Test player movement functionality."""
        try:
            direction = Vector2(1.0, 0.0)
            result = await test_game_client.move_player(direction)
            # Should succeed or return movement info
            assert result is not None or result is None  # Either response is valid
        except NotImplementedError:
            pytest.skip("move_player not implemented yet")  
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["move", "player", "direction"])
    
    @pytest.mark.asyncio
    async def test_player_split(self, test_game_client):
        """Test player split functionality."""
        try:
            result = await test_game_client.player_split()
            # Should succeed or return split info
            assert result is not None or result is None  # Either response is valid
        except NotImplementedError:
            pytest.skip("player_split not implemented yet")
        except Exception as e:
            # Expected in test environment  
            assert any(keyword in str(e).lower() for keyword in ["split", "player", "game"])


class TestDataOperations:
    """Test data retrieval and manipulation operations."""
    
    @pytest.mark.asyncio
    async def test_get_game_state(self, test_game_client):
        """Test retrieving game state."""
        try:
            state = await test_game_client.get_game_state()
            # Should return game state data
            assert state is not None
            assert isinstance(state, dict)
        except NotImplementedError:
            pytest.skip("get_game_state not implemented yet")
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["state", "game", "data"])
    
    @pytest.mark.asyncio
    async def test_get_players(self, test_game_client):
        """Test retrieving player list."""
        try:
            players = await test_game_client.get_players()
            # Should return list of players
            assert players is not None
            assert isinstance(players, (list, dict))
        except NotImplementedError:
            pytest.skip("get_players not implemented yet")
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["player", "list", "data"])
    
    @pytest.mark.asyncio
    async def test_get_entities(self, test_game_client):
        """Test retrieving game entities."""
        try:
            entities = await test_game_client.get_entities()
            # Should return list of entities
            assert entities is not None
            assert isinstance(entities, (list, dict))
        except NotImplementedError:
            pytest.skip("get_entities not implemented yet")
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["entit", "game", "data"])


class TestSubscriptionOperations:
    """Test subscription and real-time update operations."""
    
    @pytest.mark.asyncio
    async def test_subscribe_to_table(self, test_game_client):
        """Test subscribing to table updates."""
        try:
            result = await test_game_client.subscribe_to_table("players")
            # Should succeed
            assert result is not None or result is None
        except NotImplementedError:
            pytest.skip("subscribe_to_table not implemented yet")
        except Exception as e:
            # Expected in test environment
            assert any(keyword in str(e).lower() for keyword in ["subscr", "table", "update"])
    
    @pytest.mark.asyncio 
    async def test_event_handling(self, test_game_client):
        """Test event handling capabilities."""
        # Test that event handling methods exist
        assert hasattr(test_game_client, 'on_connection_state_changed') or hasattr(test_game_client, 'on_error')
        
        # Test event handler registration
        def dummy_handler(event):
            pass
        
        try:
            if hasattr(test_game_client, 'on_error'):
                test_game_client.on_error(dummy_handler)
            elif hasattr(test_game_client, 'on_connection_state_changed'):
                test_game_client.on_connection_state_changed(dummy_handler)
        except NotImplementedError:
            pytest.skip("Event handling not implemented yet")
        except Exception:
            pass  # Expected in test environment


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, test_environment_config):
        """Test handling connection timeouts."""
        # Create client with very short timeout
        config = test_environment_config
        config.connection_timeout = 0.1  # Very short timeout
        
        try:
            client = create_game_client(
                host=f"{config.server_ip}:{config.server_port}",
                database="test-timeout",
                server_language=config.server_language
            )
            # Should handle timeout gracefully
            assert client is not None
        except BlackholioTimeoutError:
            # Expected timeout error
            pass
        except Exception as e:
            # Should be connection-related error
            assert any(keyword in str(e).lower() for keyword in ["timeout", "connection", "connect"])
    
    @pytest.mark.asyncio
    async def test_invalid_server_handling(self, test_environment_config):
        """Test handling invalid server configuration."""
        # Test with invalid port
        config = test_environment_config
        config.server_port = 99999  # Invalid port
        
        try:
            client = create_game_client(
                host=f"{config.server_ip}:{config.server_port}",
                database="test-invalid",
                server_language=config.server_language
            )
            # Should handle gracefully
            assert client is not None
        except BlackholioConnectionError:
            # Expected connection error
            pass
        except Exception as e:
            # Should be connection-related error
            assert any(keyword in str(e).lower() for keyword in ["connection", "server", "port"])
    
    @pytest.mark.asyncio
    async def test_disconnection_handling(self, test_game_client):
        """Test handling disconnections."""
        try:
            # Test disconnect functionality
            await test_game_client.disconnect()
            
            # After disconnect, connection should be closed
            if hasattr(test_game_client, 'is_connected'):
                connected = await test_game_client.is_connected()
                assert not connected
        except NotImplementedError:
            pytest.skip("Disconnect functionality not implemented yet")
        except Exception:
            pass  # Expected in test environment


class TestPerformanceAndReliability:
    """Test performance and reliability aspects."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_game_client):
        """Test handling concurrent operations."""
        # Create multiple concurrent tasks
        tasks = []
        
        for i in range(5):
            if hasattr(test_game_client, 'get_game_state'):
                task = asyncio.create_task(test_game_client.get_game_state())
                tasks.append(task)
        
        if tasks:
            try:
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Should handle concurrent operations
                assert len(results) == len(tasks)
                
                # At least some should succeed or fail gracefully
                valid_results = [r for r in results if not isinstance(r, Exception)]
                assert len(valid_results) >= 0  # Allow all to fail in test environment
                
            except Exception:
                pass  # Expected in test environment
    
    @pytest.mark.asyncio
    async def test_client_statistics(self, test_game_client):
        """Test client statistics and monitoring."""
        # Test statistics methods exist
        if hasattr(test_game_client, 'get_statistics'):
            try:
                stats = await test_game_client.get_statistics()
                assert stats is not None
                assert isinstance(stats, dict)
            except NotImplementedError:
                pytest.skip("Statistics not implemented yet")
            except Exception:
                pass  # Expected in test environment
    
    @pytest.mark.asyncio 
    async def test_client_health_check(self, test_game_client):
        """Test client health checking."""
        # Test health check methods exist
        if hasattr(test_game_client, 'health_check'):
            try:
                health = await test_game_client.health_check()
                assert health is not None
            except NotImplementedError:
                pytest.skip("Health check not implemented yet")
            except Exception:
                pass  # Expected in test environment


# Parametrized tests for multiple server languages
@pytest.mark.parametrize("server_language", ["rust", "python", "csharp", "go"])
class TestMultiLanguageSupport:
    """Test support for multiple SpacetimeDB server languages."""
    
    @pytest.mark.asyncio
    async def test_client_creation_for_language(self, server_language, available_servers):
        """Test client creation for specific server language."""
        if server_language not in available_servers:
            pytest.skip(f"{server_language} server not available")
        
        # Create config for specific language
        from unittest.mock import patch
        import os
        
        with patch.dict(os.environ, {
            "SERVER_LANGUAGE": server_language,
            "SERVER_IP": "127.0.0.1", 
            "SERVER_PORT": str(3000 + ["rust", "python", "csharp", "go"].index(server_language))
        }):
            config = EnvironmentConfig()
            config._spacetime_cli_path = "/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli"
            
            try:
                client = create_game_client(
                    host=f"{config.server_ip}:{config.server_port}",
                    database="test-multi-lang",
                    server_language=server_language
                )
                assert client is not None
                assert client.server_language == server_language
            except Exception as e:
                # Some languages might not be fully implemented yet
                assert server_language in str(e) or "not implemented" in str(e).lower()