#!/usr/bin/env python3
"""
Test script to verify binary frame fixes for Blackholio Python Client.

This tests that all WebSocket messages are sent as binary frames, not text frames,
preventing server disconnections due to protocol mismatches.
"""

import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock
from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection, BlackholioClient, ConnectionState
from blackholio_client.connection.server_config import ServerConfig
from blackholio_client.models.game_entities import Vector2

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestBinaryFrames:
    """Test that all messages are sent as binary frames."""
    
    def __init__(self):
        self.sent_messages = []
        self.mock_websocket = None
    
    async def capture_send(self, message):
        """Capture sent messages for verification."""
        self.sent_messages.append({
            'data': message,
            'type': type(message).__name__,
            'is_bytes': isinstance(message, bytes)
        })
        logger.info(f"Captured message: type={type(message).__name__}, is_bytes={isinstance(message, bytes)}, length={len(message) if message else 0}")
    
    async def test_connection_messages(self):
        """Test that connection-level messages are sent as binary frames."""
        logger.info("\n=== Testing Connection Messages ===")
        
        # Create test config
        config = ServerConfig(
            language="python",
            host="localhost",
            port=3000,
            db_identity="test-db",
            protocol="v1.json.spacetimedb",
            use_ssl=False
        )
        
        # Create connection
        connection = SpacetimeDBConnection(config)
        
        # Mock the websocket
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send = self.capture_send
        self.mock_websocket.closed = False
        connection.websocket = self.mock_websocket
        connection.state = ConnectionState.CONNECTED
        
        # Clear captured messages
        self.sent_messages.clear()
        
        # Test 1: Subscription request
        logger.info("\nTest 1: Testing _send_subscription_request")
        await connection._send_subscription_request()
        
        # Test 2: Regular message
        logger.info("\nTest 2: Testing _send_message")
        await connection._send_message({"type": "test", "data": "hello"})
        
        # Verify all messages were sent as bytes
        logger.info("\n=== Verification Results ===")
        all_binary = True
        for i, msg in enumerate(self.sent_messages):
            logger.info(f"Message {i+1}: type={msg['type']}, is_bytes={msg['is_bytes']}")
            if not msg['is_bytes']:
                logger.error(f"ERROR: Message {i+1} was sent as {msg['type']} instead of bytes!")
                all_binary = False
        
        return all_binary
    
    async def test_client_messages(self):
        """Test that client-level messages are sent as binary frames."""
        logger.info("\n=== Testing Client Messages ===")
        
        # Create client
        client = BlackholioClient(server_language="python")
        
        # Mock the connection's websocket
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send = self.capture_send
        self.mock_websocket.closed = False
        client.connection.websocket = self.mock_websocket
        client.connection.state = ConnectionState.CONNECTED
        
        # Clear captured messages
        self.sent_messages.clear()
        
        # Test 1: enter_game
        logger.info("\nTest 1: Testing enter_game")
        await client.enter_game("TestPlayer")
        
        # Test 2: update_player_input
        logger.info("\nTest 2: Testing update_player_input")
        direction = Vector2(1.0, 0.0)
        await client.update_player_input(direction)
        
        # Verify all messages were sent as bytes
        logger.info("\n=== Verification Results ===")
        all_binary = True
        for i, msg in enumerate(self.sent_messages):
            logger.info(f"Message {i+1}: type={msg['type']}, is_bytes={msg['is_bytes']}")
            if not msg['is_bytes']:
                logger.error(f"ERROR: Message {i+1} was sent as {msg['type']} instead of bytes!")
                all_binary = False
        
        return all_binary
    
    async def test_sdk_string_return(self):
        """Test handling when SDK returns string instead of bytes."""
        logger.info("\n=== Testing SDK String Return Handling ===")
        
        config = ServerConfig(
            language="python",
            host="localhost",
            port=3000,
            db_identity="test-db",
            protocol="v1.json.spacetimedb",
            use_ssl=False
        )
        
        connection = SpacetimeDBConnection(config)
        
        # Mock protocol helper to return strings (simulating the bug)
        mock_protocol_helper = Mock()
        mock_protocol_helper.encode_subscription = Mock(return_value="string_instead_of_bytes")
        mock_protocol_helper.encode_message = Mock(return_value="another_string")
        mock_protocol_helper.encode_reducer_call = Mock(return_value="reducer_string")
        connection.protocol_helper = mock_protocol_helper
        
        # Mock websocket
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send = self.capture_send
        self.mock_websocket.closed = False
        connection.websocket = self.mock_websocket
        connection.state = ConnectionState.CONNECTED
        
        # Clear captured messages
        self.sent_messages.clear()
        
        # Test that strings get converted to bytes
        logger.info("\nTesting string-to-bytes conversion")
        await connection._send_subscription_request()
        await connection._send_message({"test": "data"})
        
        # Verify conversion happened
        logger.info("\n=== Verification Results ===")
        all_converted = True
        for i, msg in enumerate(self.sent_messages):
            logger.info(f"Message {i+1}: type={msg['type']}, is_bytes={msg['is_bytes']}")
            if not msg['is_bytes']:
                logger.error(f"ERROR: Message {i+1} was not converted to bytes!")
                all_converted = False
            else:
                logger.info(f"SUCCESS: String was converted to bytes for message {i+1}")
        
        return all_converted


async def main():
    """Run all tests."""
    tester = TestBinaryFrames()
    
    logger.info("=" * 60)
    logger.info("BINARY FRAME FIX VERIFICATION TEST")
    logger.info("=" * 60)
    
    results = []
    
    # Test 1: Connection messages
    result1 = await tester.test_connection_messages()
    results.append(("Connection Messages", result1))
    
    # Test 2: Client messages
    result2 = await tester.test_client_messages()
    results.append(("Client Messages", result2))
    
    # Test 3: SDK string return handling
    result3 = await tester.test_sdk_string_return()
    results.append(("SDK String Handling", result3))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("ALL TESTS PASSED - Binary frames are properly enforced!")
    else:
        logger.error("SOME TESTS FAILED - Check the logs above for details")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())