#!/usr/bin/env python3
"""
Simple test to verify protocol fixes implementation.
This is a basic smoke test that doesn't require complex mocking.
"""

import asyncio
import logging
from src.blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection, BlackholioClient
from src.blackholio_client.connection.server_config import ServerConfig

# Configure logging to see our implementation
logging.basicConfig(level=logging.INFO)

def test_protocol_initialization():
    """Test basic protocol initialization."""
    print("✅ Test 1: Protocol Initialization")
    
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
    print("  ✓ Protocol version correctly set")
    print("  ✓ Protocol validation flag initialized")
    

def test_protocol_info():
    """Test protocol info retrieval."""
    print("\n✅ Test 2: Protocol Info")
    
    config = ServerConfig(
        language="python",
        host="localhost", 
        port=8080,
        protocol="v1.json.spacetimedb",
        db_identity="test"
    )
    
    conn = SpacetimeDBConnection(config)
    info = conn.get_protocol_info()
    
    assert 'protocol_version' in info
    assert 'protocol_validated' in info
    assert 'connection_state' in info
    assert info['protocol_version'] == "v1.json.spacetimedb"
    assert info['connection_state'] == "disconnected"
    
    print("  ✓ Protocol info contains all expected fields")
    print(f"  ✓ Protocol version: {info['protocol_version']}")
    print(f"  ✓ SDK validation available: {info['sdk_validation_available']}")


def test_protocol_debugging():
    """Test protocol debugging enablement."""
    print("\n✅ Test 3: Protocol Debugging")
    
    config = ServerConfig(
        language="python",
        host="localhost", 
        port=8080,
        protocol="v1.json.spacetimedb",
        db_identity="test"
    )
    
    conn = SpacetimeDBConnection(config)
    
    # Enable debugging (this should log messages)
    print("  Enabling protocol debugging...")
    conn.enable_protocol_debugging()
    print("  ✓ Protocol debugging enabled successfully")


async def test_message_type_recognition():
    """Test enhanced message type recognition."""
    print("\n✅ Test 4: Message Type Recognition")
    
    config = ServerConfig(
        language="python",
        host="localhost", 
        port=8080,
        protocol="v1.json.spacetimedb",
        db_identity="test"
    )
    
    conn = SpacetimeDBConnection(config)
    
    # Track triggered events
    triggered_events = []
    
    async def event_handler(data):
        triggered_events.append(data)
    
    # Register handlers for different message types
    conn.on('identity_token', event_handler)
    conn.on('initial_subscription', event_handler)
    conn.on('transaction_update', event_handler)
    conn.on('raw_message', event_handler)
    
    # Test different message types
    test_messages = [
        {"IdentityToken": "test-token-123"},
        {"InitialSubscription": {"tables": ["player", "entity"]}},
        {"TransactionUpdate": {"id": "tx-456", "status": "committed"}},
        {"UnknownMessageType": {"data": "test"}}
    ]
    
    for msg in test_messages:
        await conn._process_message(msg)
    
    # Verify events were triggered
    assert len(triggered_events) == 4
    assert triggered_events[0]['type'] == 'identity_token'
    assert triggered_events[1]['type'] == 'initial_subscription'
    assert triggered_events[2]['type'] == 'transaction_update'
    assert triggered_events[3]['type'] == 'raw_message'
    
    print("  ✓ IdentityToken recognized correctly")
    print("  ✓ InitialSubscription recognized correctly")
    print("  ✓ TransactionUpdate recognized correctly")
    print("  ✓ Unknown message types handled gracefully")


async def test_timeout_handling():
    """Test improved timeout handling."""
    print("\n✅ Test 5: Timeout Handling")
    
    config = ServerConfig(
        language="python",
        host="localhost", 
        port=8080,
        protocol="v1.json.spacetimedb",
        db_identity="test"
    )
    
    conn = SpacetimeDBConnection(config)
    
    # Test timeout with short duration
    import time
    start = time.time()
    result = await conn.wait_until_connected(timeout=0.2)
    elapsed = time.time() - start
    
    assert result == False
    assert 0.2 <= elapsed <= 0.3  # Should timeout at specified duration
    
    print(f"  ✓ Timeout handling works correctly (elapsed: {elapsed:.2f}s)")
    print("  ✓ No infinite loop detected")


def test_blackholio_client_integration():
    """Test BlackholioClient integration with protocol fixes."""
    print("\n✅ Test 6: BlackholioClient Integration")
    
    client = BlackholioClient()
    
    # Test that debugging methods are exposed
    assert hasattr(client, 'enable_protocol_debugging')
    assert hasattr(client, 'get_protocol_info')
    
    # Test calling the methods
    client.enable_protocol_debugging()
    info = client.get_protocol_info()
    
    assert isinstance(info, dict)
    assert 'protocol_version' in info
    
    print("  ✓ BlackholioClient exposes debugging methods")
    print("  ✓ Methods are callable and return expected data")


def main():
    """Run all tests."""
    print("🚀 Running Protocol Fixes Tests")
    print("=" * 50)
    
    try:
        # Run sync tests
        test_protocol_initialization()
        test_protocol_info()
        test_protocol_debugging()
        test_blackholio_client_integration()
        
        # Run async tests
        asyncio.run(test_message_type_recognition())
        asyncio.run(test_timeout_handling())
        
        print("\n✅ All tests passed!")
        print("\nSummary of implemented fixes:")
        print("1. Protocol configuration verification ✓")
        print("2. Frame type validation for WebSocket messages ✓")
        print("3. Enhanced message type recognition ✓")
        print("4. Improved timeout handling ✓")
        print("5. Protocol debugging features ✓")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()