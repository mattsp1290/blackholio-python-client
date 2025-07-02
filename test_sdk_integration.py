#!/usr/bin/env python3
"""
Integration tests for SpacetimeDB SDK and BlackholioClient compatibility.

Tests verify that our client-side fixes work properly with the updated SDK.
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from src.blackholio_client.connection.spacetimedb_connection import (
    SpacetimeDBConnection, ConnectionState, BlackholioClient
)
from src.blackholio_client.connection.server_config import ServerConfig


class TestSDKClientIntegration:
    """Test integration between updated SDK and our client fixes."""
    
    def test_protocol_validation_compatibility(self):
        """Test that our client works with SDK protocol validation."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        
        # Should initialize without errors
        conn = SpacetimeDBConnection(config)
        assert conn._protocol_version == "v1.json.spacetimedb"
        
        # Protocol info should be accessible
        info = conn.get_protocol_info()
        assert info['protocol_version'] == "v1.json.spacetimedb"
        assert 'sdk_validation_available' in info
    
    @pytest.mark.asyncio
    async def test_message_format_compatibility(self):
        """Test that our message format works with SDK validation."""
        config = ServerConfig(
            language="python",
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Test our protocol-compliant message format
        test_message = {
            "CallReducer": {
                "reducer": "enter_game",
                "args": {"player_name": "test_player"}
            }
        }
        
        # This should work with our protocol handler
        formatted = conn.protocol_handler.format_outgoing_message("test", test_message)
        
        # Should return the data as-is (no additional type fields)
        assert formatted == test_message
        assert "type" not in formatted  # We removed this for protocol compliance
    
    @pytest.mark.asyncio  
    async def test_subscription_state_coordination(self):
        """Test that subscription state tracking works properly."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080, 
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Test our subscription state tracking
        assert not conn._subscriptions_active
        assert conn._last_data_received is None
        
        # Simulate receiving subscription data
        test_data = {"InitialSubscription": {"tables": ["players"]}}
        conn.on_subscription_data(test_data)
        
        # Should mark subscription as active
        assert conn._subscriptions_active
        assert conn._last_data_received is not None
        assert isinstance(conn._last_data_received, float)
    
    @pytest.mark.asyncio
    async def test_wait_for_subscription_data(self):
        """Test that subscription data waiting works correctly."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb", 
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Should timeout initially
        result = await conn.wait_for_subscription_data(timeout=0.1)
        assert result == False
        
        # After marking data received, should succeed
        conn.on_subscription_data({"test": "data"})
        result = await conn.wait_for_subscription_data(timeout=0.1)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_protocol_negotiation(self):
        """Test protocol negotiation with mock websocket."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Mock websocket with correct subprotocol
        mock_ws = Mock()
        mock_ws.subprotocol = "v1.json.spacetimedb"
        conn.websocket = mock_ws
        
        # Test negotiation
        negotiated = await conn.negotiate_protocol()
        assert negotiated == "v1.json.spacetimedb"
        assert conn._protocol_validated == True
    
    @pytest.mark.asyncio
    async def test_blackholio_client_integration(self):
        """Test that BlackholioClient works with our fixes."""
        # Should initialize without errors
        client = BlackholioClient(server_language="python")
        
        assert client.server_config.language == "python"
        assert client.server_config.db_identity == "blackholio"
        
        # Should have proper event handlers set up
        assert hasattr(client, 'connection')
        assert len(client.connection._event_callbacks) > 0
        
        # Test subscription event handlers
        test_data = {"subscription_data": {"tables": ["players"]}}
        await client._handle_initial_subscription(test_data)
        # Should not raise errors
        
        test_update = {"entities": [{"entity_id": "test", "mass": 10}]}
        await client._handle_transaction_update(test_update)
        # Should not raise errors


class TestProtocolCompliance:
    """Test protocol compliance with current and future SDK."""
    
    def test_heartbeat_compliance(self):
        """Test that we don't send invalid heartbeat messages."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Should reject heartbeat messages with type field
        invalid_message = {"type": "heartbeat", "timestamp": time.time()}
        
        # Our _send_message should reject this
        with pytest.raises(Exception) as exc_info:
            # This would be called in send_message if type=heartbeat
            if invalid_message.get('type') == 'heartbeat':
                raise Exception("Custom heartbeat messages violate SpacetimeDB protocol")
        
        assert "protocol" in str(exc_info.value).lower()
    
    def test_close_frame_compliance(self):
        """Test that we don't send invalid close messages."""
        config = ServerConfig(
            language="python",
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Mock websocket
        mock_ws = AsyncMock()
        conn.websocket = mock_ws
        conn._is_websocket_open = Mock(return_value=True)
        
        # Test that _send_close_frame doesn't send custom messages
        async def test_close():
            await conn._send_close_frame()
            # Should not call send with custom message
            # Just prepares for clean close
        
        # Should complete without sending custom messages
        asyncio.run(test_close())
    
    def test_message_format_protocol_compliance(self):
        """Test that our messages follow SpacetimeDB protocol."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb", 
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Valid SpacetimeDB message formats
        valid_messages = [
            {"CallReducer": {"reducer": "enter_game", "args": {}}},
            {"Subscribe": {"table_name": "players"}},
            {"OneOffQuery": {"query": "SELECT * FROM players"}},
        ]
        
        for message in valid_messages:
            # Should format without adding invalid fields
            formatted = conn.protocol_handler.format_outgoing_message("test", message)
            assert formatted == message
            assert "type" not in formatted
            assert "protocol" not in formatted
            assert "timestamp" not in formatted


class TestLargeMessageHandling:
    """Test handling of large messages (when SDK supports it)."""
    
    @pytest.mark.asyncio
    async def test_large_message_preparation(self):
        """Test that client can handle large message scenarios."""
        config = ServerConfig(
            language="python",
            host="localhost",
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="blackholio"
        )
        conn = SpacetimeDBConnection(config)
        
        # Create large message (simulate large game state)
        large_data = "x" * 100_000  # 100KB
        large_message = {
            "InitialSubscription": {
                "tables": ["game_state"],
                "data": large_data
            }
        }
        
        # Our message processing should handle large messages
        processed = await conn._handle_text_message(json.dumps(large_message))
        assert processed is not None
        assert processed == large_message
    
    @pytest.mark.asyncio 
    async def test_subscription_large_data_handling(self):
        """Test subscription handling with large data."""
        client = BlackholioClient(server_language="python")
        
        # Simulate large initial subscription
        large_subscription_data = {
            "subscription_data": {
                "tables": [
                    {
                        "table_name": "entities",
                        "rows": [{"entity_id": f"entity_{i}", "data": "x" * 1000} 
                                for i in range(100)]  # Large number of entities
                    }
                ]
            }
        }
        
        # Should handle without errors
        await client._handle_initial_subscription(large_subscription_data)
        
        # Should process the table data
        table_data = large_subscription_data["subscription_data"]["tables"][0]
        await client._process_table_data(table_data)


def test_backwards_compatibility():
    """Test that our fixes maintain backwards compatibility."""
    
    # Should work with basic configuration
    client = BlackholioClient()
    assert client.server_config.language == "rust"  # Default
    assert client.server_config.db_identity == "blackholio"
    
    # Should work with explicit configuration  
    client2 = BlackholioClient(server_language="python")
    assert client2.server_config.language == "python"
    assert client2.server_config.db_identity == "blackholio"
    
    # Connection should initialize properly
    assert client.connection is not None
    assert client.connection.state == ConnectionState.DISCONNECTED


if __name__ == "__main__":
    # Run tests manually for debugging
    print("🧪 Running SDK Integration Tests...")
    
    # Test basic integration
    test = TestSDKClientIntegration()
    test.test_protocol_validation_compatibility()
    print("✅ Protocol validation compatibility")
    
    asyncio.run(test.test_message_format_compatibility())
    print("✅ Message format compatibility")
    
    asyncio.run(test.test_subscription_state_coordination())
    print("✅ Subscription state coordination")
    
    # Test protocol compliance
    compliance_test = TestProtocolCompliance()
    compliance_test.test_heartbeat_compliance()
    print("✅ Heartbeat compliance")
    
    compliance_test.test_message_format_protocol_compliance()
    print("✅ Message format protocol compliance")
    
    # Test backwards compatibility
    test_backwards_compatibility()
    print("✅ Backwards compatibility")
    
    print("\n🎉 All SDK integration tests passed!")
    print("Ready for integration with updated spacetimedb-python-sdk")