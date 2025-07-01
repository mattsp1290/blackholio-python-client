#!/usr/bin/env python3
"""
Test suite for protocol fixes implemented in SpacetimeDB connection.

Tests the enhanced protocol validation, frame type detection, and message
type recognition features.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.blackholio_client.connection.spacetimedb_connection import (
    SpacetimeDBConnection, ConnectionState, BlackholioClient
)
from src.blackholio_client.connection.server_config import ServerConfig


class TestProtocolValidation:
    """Test protocol validation and configuration features."""
    
    def test_protocol_initialization(self):
        """Test that protocol configuration is properly initialized."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        assert conn._protocol_version == "v1.json.spacetimedb"
        assert conn._protocol_validated == False
        assert hasattr(conn, 'protocol_helper')
        assert hasattr(conn, '_protocol_version')
    
    @pytest.mark.asyncio
    async def test_protocol_negotiation_validation(self):
        """Test protocol negotiation validation during connection."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Mock websocket with correct protocol
        mock_ws = AsyncMock()
        mock_ws.subprotocol = "v1.json.spacetimedb"
        
        with patch('websockets.connect') as mock_connect:
            async def return_mock_ws():
                return mock_ws
            mock_connect.return_value = return_mock_ws()
            
            # Attempt connection
            with patch.object(conn, '_send_subscription_request', AsyncMock()):
                result = await conn._connect_with_auth("ws://localhost/test")
                
            assert result == True
            assert conn._protocol_validated == True
    
    @pytest.mark.asyncio
    async def test_protocol_mismatch_warning(self, caplog):
        """Test that protocol mismatches generate warnings."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Mock websocket with wrong protocol
        mock_ws = AsyncMock()
        mock_ws.subprotocol = "v1.bsatn.spacetimedb"  # Binary protocol instead of JSON
        
        with patch('websockets.connect') as mock_connect:
            async def return_mock_ws():
                return mock_ws
            mock_connect.return_value = return_mock_ws()
            
            # Attempt connection
            with patch.object(conn, '_send_subscription_request', AsyncMock()):
                await conn._connect_with_auth("ws://localhost/test")
                
            # Check for warning
            assert "Protocol mismatch" in caplog.text


class TestFrameTypeValidation:
    """Test frame type validation in message handler."""
    
    @pytest.mark.asyncio
    async def test_binary_frame_warning_with_json_protocol(self, caplog):
        """Test that binary frames with JSON protocol generate warnings."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        conn.state = ConnectionState.CONNECTED
        
        # Mock websocket that returns binary message
        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [b'binary data']
        conn.websocket = mock_ws
        
        # Run message handler briefly
        handler_task = asyncio.create_task(conn._message_handler())
        await asyncio.sleep(0.1)
        handler_task.cancel()
        try:
            await handler_task
        except asyncio.CancelledError:
            pass
        
        # Check for warning about binary frame with JSON protocol
        assert "Protocol mismatch: negotiated JSON but received binary frame" in caplog.text
    
    @pytest.mark.asyncio
    async def test_text_frame_handling(self, caplog):
        """Test proper handling of text frames with JSON protocol."""
        caplog.set_level(logging.DEBUG)
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        conn.state = ConnectionState.CONNECTED
        
        # Mock websocket that returns text message
        test_message = json.dumps({"type": "test", "data": "hello"})
        mock_ws = AsyncMock()
        mock_ws.__aiter__.return_value = [test_message]
        conn.websocket = mock_ws
        
        # Run message handler briefly
        handler_task = asyncio.create_task(conn._message_handler())
        await asyncio.sleep(0.1)
        handler_task.cancel()
        try:
            await handler_task
        except asyncio.CancelledError:
            pass
        
        # Check for proper text frame handling
        assert "Received TEXT frame" in caplog.text
        assert "parsing with JSON protocol" in caplog.text


class TestMessageTypeRecognition:
    """Test enhanced message type recognition."""
    
    @pytest.mark.asyncio
    async def test_identity_token_recognition(self, caplog):
        """Test recognition of IdentityToken messages."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Create IdentityToken message in the correct format
        message = {
            "identity": "test-identity-123",
            "token": "test-token-12345",
            "connection_id": "conn-456"
        }
        
        # Mock event trigger
        with patch.object(conn, '_trigger_event', AsyncMock()) as mock_trigger:
            await conn._process_message(message)
            
            # Verify event was triggered with correct type
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            assert call_args[0][0] == 'IdentityToken'
            processed_data = call_args[0][1]
            assert processed_data['type'] == 'IdentityToken'
            assert processed_data['token'] == "test-token-12345"
        
        # The message should be processed without errors (no specific log message expected)
    
    @pytest.mark.asyncio
    async def test_initial_subscription_recognition(self):
        """Test recognition of InitialSubscription messages."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Create InitialSubscription message
        message = {"InitialSubscription": {"tables": ["player", "entity"]}}
        
        # Mock event trigger
        with patch.object(conn, '_trigger_event', AsyncMock()) as mock_trigger:
            await conn._process_message(message)
            
            # Verify event was triggered with correct type
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            assert call_args[0][0] == 'initial_subscription'
            assert 'subscription_data' in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_transaction_update_recognition(self):
        """Test recognition of TransactionUpdate messages."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Create TransactionUpdate message
        message = {"TransactionUpdate": {"id": "tx-123", "status": "committed"}}
        
        # Mock event trigger
        with patch.object(conn, '_trigger_event', AsyncMock()) as mock_trigger:
            await conn._process_message(message)
            
            # Verify event was triggered with correct type
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            assert call_args[0][0] == 'transaction_update'
            assert 'update_data' in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_unknown_message_handling(self, caplog):
        """Test handling of unknown message types."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Create unknown message
        message = {"UnknownType": {"data": "test"}, "AnotherUnknown": {}}
        
        # Mock event trigger
        with patch.object(conn, '_trigger_event', AsyncMock()) as mock_trigger:
            await conn._process_message(message)
            
            # Verify raw message event was triggered
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            assert call_args[0][0] == 'raw_message'
        
        # Check logging
        assert "Received unrecognized message format" in caplog.text


class TestTimeoutHandling:
    """Test improved timeout handling."""
    
    @pytest.mark.asyncio
    async def test_wait_until_connected_timeout(self, caplog):
        """Test that wait_until_connected properly times out."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        conn.state = ConnectionState.CONNECTING
        
        # Test with short timeout
        start_time = asyncio.get_event_loop().time()
        result = await conn.wait_until_connected(timeout=0.5)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        assert result == False
        assert elapsed >= 0.5
        assert elapsed < 0.7  # Should not take much longer than timeout
        assert "Connection timeout reached" in caplog.text
    
    @pytest.mark.asyncio
    async def test_wait_until_connected_success(self):
        """Test successful connection wait."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Simulate connection after delay
        async def connect_after_delay():
            await asyncio.sleep(0.2)
            conn.state = ConnectionState.CONNECTED
        
        asyncio.create_task(connect_after_delay())
        
        # Wait for connection
        result = await conn.wait_until_connected(timeout=1.0)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_wait_until_connected_failure(self):
        """Test connection failure during wait."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Simulate connection failure after delay
        async def fail_after_delay():
            await asyncio.sleep(0.2)
            conn.state = ConnectionState.FAILED
        
        asyncio.create_task(fail_after_delay())
        
        # Wait for connection
        result = await conn.wait_until_connected(timeout=1.0)
        assert result == False


class TestProtocolDebugging:
    """Test protocol debugging features."""
    
    def test_enable_protocol_debugging(self, caplog):
        """Test enabling protocol debugging."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Enable debugging
        conn.enable_protocol_debugging()
        
        # Check logging
        assert "Protocol debugging enabled" in caplog.text
        assert "Current protocol version: v1.json.spacetimedb" in caplog.text
    
    def test_get_protocol_info(self):
        """Test getting protocol information."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Get protocol info
        info = conn.get_protocol_info()
        
        # Verify expected fields
        assert 'protocol_version' in info
        assert 'protocol_validated' in info
        assert 'connection_state' in info
        assert 'sdk_validation_available' in info
        assert info['protocol_version'] == "v1.json.spacetimedb"
        assert info['connection_state'] == "disconnected"
    
    def test_blackholio_client_debugging_methods(self):
        """Test that BlackholioClient exposes debugging methods."""
        client = BlackholioClient()
        
        # Test that methods exist
        assert hasattr(client, 'enable_protocol_debugging')
        assert hasattr(client, 'get_protocol_info')
        
        # Test calling them
        client.enable_protocol_debugging()
        info = client.get_protocol_info()
        assert isinstance(info, dict)


class TestTextMessageHandler:
    """Test the new text message handler."""
    
    @pytest.mark.asyncio
    async def test_text_message_json_parsing(self):
        """Test JSON parsing in text message handler."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Test valid JSON
        message = '{"type": "test", "data": {"value": 123}}'
        result = await conn._handle_text_message(message)
        
        assert result is not None
        assert result['type'] == 'test'
        assert result['data']['value'] == 123
    
    @pytest.mark.asyncio
    async def test_text_message_unknown_type_detection(self, caplog):
        """Test detection of unknown message types in text handler."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Test with unknown SpacetimeDB message type
        message = '{"IdentityToken": "abc123", "UnknownField": "test"}'
        result = await conn._handle_text_message(message)
        
        assert result is not None
        assert "Unknown message type in data" in caplog.text
    
    @pytest.mark.asyncio
    async def test_text_message_invalid_json(self, caplog):
        """Test handling of invalid JSON in text messages."""
        config = ServerConfig(
            language="python", 
            host="localhost", 
            port=8080,
            protocol="v1.json.spacetimedb",
            db_identity="test"
        )
        conn = SpacetimeDBConnection(config)
        
        # Test invalid JSON
        message = 'invalid json {not valid}'
        result = await conn._handle_text_message(message)
        
        assert result is None
        assert "Failed to decode text message as JSON" in caplog.text


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])