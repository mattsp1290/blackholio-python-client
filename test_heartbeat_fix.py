#!/usr/bin/env python3
"""
Test script to verify the heartbeat handler AttributeError fix.

This test verifies that the _is_websocket_open() method safely handles
different websocket states without raising AttributeError.
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
from blackholio_client.connection.server_config import ServerConfig

def test_is_websocket_open():
    """Test the _is_websocket_open method with various websocket states"""
    
    # Create a test connection
    config = ServerConfig(
        language="rust",
        host="localhost", 
        port=3000,
        db_identity="test-db",
        protocol="v1.json.spacetimedb",
        use_ssl=False
    )
    
    conn = SpacetimeDBConnection(config)
    
    print("🧪 Testing _is_websocket_open method...")
    
    # Test 1: No websocket (should return False)
    conn.websocket = None
    result = conn._is_websocket_open()
    assert result == False, f"Expected False when no websocket, got {result}"
    print("✅ Test 1 passed: No websocket returns False")
    
    # Test 2: Websocket with closed attribute (open)
    mock_ws_open = Mock()
    mock_ws_open.closed = False
    conn.websocket = mock_ws_open
    result = conn._is_websocket_open()
    assert result == True, f"Expected True when websocket.closed=False, got {result}"
    print("✅ Test 2 passed: Websocket with closed=False returns True")
    
    # Test 3: Websocket with closed attribute (closed)
    mock_ws_closed = Mock()
    mock_ws_closed.closed = True
    conn.websocket = mock_ws_closed
    result = conn._is_websocket_open()
    assert result == False, f"Expected False when websocket.closed=True, got {result}"
    print("✅ Test 3 passed: Websocket with closed=True returns False")
    
    # Test 4: Websocket without closed attribute but with close_code (open)
    mock_ws_close_code_open = Mock()
    del mock_ws_close_code_open.closed  # Remove closed attribute
    mock_ws_close_code_open.close_code = None
    conn.websocket = mock_ws_close_code_open
    result = conn._is_websocket_open()
    assert result == True, f"Expected True when close_code=None, got {result}"
    print("✅ Test 4 passed: Websocket with close_code=None returns True")
    
    # Test 5: Websocket with close_code (closed)
    mock_ws_close_code_closed = Mock()
    del mock_ws_close_code_closed.closed
    mock_ws_close_code_closed.close_code = 1000
    conn.websocket = mock_ws_close_code_closed
    result = conn._is_websocket_open()
    assert result == False, f"Expected False when close_code=1000, got {result}"
    print("✅ Test 5 passed: Websocket with close_code=1000 returns False")
    
    # Test 6: Websocket with state attribute (open)
    mock_ws_state_open = Mock()
    del mock_ws_state_open.closed
    del mock_ws_state_open.close_code
    mock_ws_state_open.state = "OPEN"
    conn.websocket = mock_ws_state_open
    result = conn._is_websocket_open()
    assert result == True, f"Expected True when state='OPEN', got {result}"
    print("✅ Test 6 passed: Websocket with state='OPEN' returns True")
    
    # Test 7: Websocket with state attribute (connected)
    mock_ws_state_connected = Mock()
    del mock_ws_state_connected.closed
    del mock_ws_state_connected.close_code
    mock_ws_state_connected.state = "Connected"
    conn.websocket = mock_ws_state_connected
    result = conn._is_websocket_open()
    assert result == True, f"Expected True when state='Connected', got {result}"
    print("✅ Test 7 passed: Websocket with state='Connected' returns True")
    
    # Test 8: Websocket with no recognizable attributes (fallback)
    mock_ws_fallback = Mock()
    del mock_ws_fallback.closed
    del mock_ws_fallback.close_code  
    del mock_ws_fallback.state
    conn.websocket = mock_ws_fallback
    result = conn._is_websocket_open()
    assert result == True, f"Expected True for fallback case, got {result}"
    print("✅ Test 8 passed: Fallback case returns True")
    
    # Test 9: Websocket that raises exception during attribute access
    mock_ws_exception = Mock()
    mock_ws_exception.closed = Mock(side_effect=Exception("Attribute access failed"))
    conn.websocket = mock_ws_exception
    result = conn._is_websocket_open()
    assert result == False, f"Expected False when exception occurs, got {result}"
    print("✅ Test 9 passed: Exception during check returns False")
    
    # Test 10: Test the problematic case from the bug report
    # This simulates a websocket object that doesn't have a 'closed' attribute
    mock_ws_no_closed = type('MockWebSocket', (), {})()
    conn.websocket = mock_ws_no_closed
    result = conn._is_websocket_open()
    # Should not raise AttributeError and should return True (fallback)
    assert result == True, f"Expected True for websocket without closed attribute, got {result}"
    print("✅ Test 10 passed: Websocket without closed attribute returns True (no AttributeError)")
    
    print("\n🎉 All tests passed! The heartbeat handler fix is working correctly.")
    return True

def test_heartbeat_handler_no_error():
    """Test that heartbeat handler doesn't crash with different websocket types"""
    
    config = ServerConfig(
        language="rust",
        host="localhost", 
        port=3000,
        db_identity="test-db", 
        protocol="v1.json.spacetimedb",
        use_ssl=False
    )
    
    conn = SpacetimeDBConnection(config)
    
    print("\n🧪 Testing heartbeat handler error handling...")
    
    # Test with websocket that doesn't have 'closed' attribute
    mock_ws_no_closed = type('MockWebSocket', (), {})()
    conn.websocket = mock_ws_no_closed
    
    # This should not raise an exception
    try:
        is_open = conn._is_websocket_open()
        print(f"✅ Heartbeat handler check succeeded: websocket is_open = {is_open}")
        return True
    except AttributeError as e:
        print(f"❌ AttributeError still occurs: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("HEARTBEAT HANDLER ATTRIBUTEERROR FIX TEST")
    print("=" * 60)
    
    try:
        # Test the _is_websocket_open method
        test1_passed = test_is_websocket_open()
        
        # Test heartbeat handler specifically 
        test2_passed = test_heartbeat_handler_no_error()
        
        if test1_passed and test2_passed:
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("The heartbeat handler AttributeError fix is working correctly.")
            print("No more 'ClientConnection object has no attribute closed' errors!")
            print("=" * 60)
            exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ SOME TESTS FAILED!")
            print("The fix may need additional work.")
            print("=" * 60)
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)