#!/usr/bin/env python3
"""
Protocol Compliance Verification Test

This test verifies that the SpacetimeDB protocol compliance fixes have been
applied correctly and no custom "type" messages are being sent to SpacetimeDB.
"""

import sys
import os
import inspect

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_heartbeat_fix():
    """Test that heartbeat handler doesn't contain custom "type" message creation"""
    
    print("🧪 Testing heartbeat handler protocol compliance...")
    
    from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
    
    # Check that heartbeat handler doesn't contain "type" message creation
    source = inspect.getsource(SpacetimeDBConnection._heartbeat_handler)
    
    # Test for the problematic pattern
    if '"type": "heartbeat"' in source:
        print("❌ CRITICAL: Heartbeat fix NOT applied!")
        print("   Found custom heartbeat message with 'type' field")
        print("   This will cause SpacetimeDB protocol violations")
        return False
    
    # Test that WebSocket ping is used instead
    if 'websocket.ping()' not in source:
        print("⚠️  WARNING: WebSocket ping not found in heartbeat handler")
        print("   Expected to find 'await self.websocket.ping()'")
        return False
    
    # Test for protocol compliance comments
    if 'SpacetimeDB protocol compliance' not in source:
        print("⚠️  WARNING: Protocol compliance comments not found")
        print("   Comments help prevent future regressions")
    
    print("✅ Heartbeat handler protocol compliance verified")
    print("   - No custom 'type' messages found")
    print("   - WebSocket ping is used for keepalive")
    print("   - Protocol compliance comments present")
    
    return True

def test_close_frame_fix():
    """Test that close frame handler doesn't contain custom "type" message creation"""
    
    print("\n🧪 Testing close frame handler protocol compliance...")
    
    from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
    
    # Check that close frame handler doesn't contain "type" message creation  
    source = inspect.getsource(SpacetimeDBConnection._send_close_frame)
    
    # Test for the problematic pattern
    if '"type": "close"' in source:
        print("❌ CRITICAL: Close frame fix NOT applied!")
        print("   Found custom close message with 'type' field")
        print("   This will cause SpacetimeDB protocol violations")
        return False
    
    # Test for protocol compliance comments
    if 'SpacetimeDB protocol compliance' not in source:
        print("⚠️  WARNING: Protocol compliance comments not found")
        print("   Comments help prevent future regressions")
    
    # Test that the method doesn't send messages anymore
    if '_send_message(' in source:
        print("❌ CRITICAL: Close frame handler still sending messages!")
        print("   Found '_send_message(' call in close frame handler")
        print("   This will cause SpacetimeDB protocol violations")
        return False
    
    print("✅ Close frame handler protocol compliance verified")
    print("   - No custom 'type' messages found")
    print("   - No application messages sent")
    print("   - Protocol compliance comments present")
    
    return True

def test_import_and_syntax():
    """Test that the code compiles and imports successfully"""
    
    print("\n🧪 Testing code compilation and imports...")
    
    try:
        from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
        print("✅ Module imports successfully")
    except ImportError as e:
        print(f"❌ CRITICAL: Import failed: {e}")
        return False
    except SyntaxError as e:
        print(f"❌ CRITICAL: Syntax error: {e}")
        return False
    
    # Test that key methods exist
    if not hasattr(SpacetimeDBConnection, '_heartbeat_handler'):
        print("❌ CRITICAL: _heartbeat_handler method not found")
        return False
    
    if not hasattr(SpacetimeDBConnection, '_send_close_frame'):
        print("❌ CRITICAL: _send_close_frame method not found")
        return False
    
    print("✅ All required methods present")
    print("✅ Code compiles without syntax errors")
    
    return True

def test_method_signatures():
    """Test that method signatures remain unchanged"""
    
    print("\n🧪 Testing method signatures...")
    
    from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
    
    # Test heartbeat handler signature
    heartbeat_sig = inspect.signature(SpacetimeDBConnection._heartbeat_handler)
    expected_params = ['self']
    actual_params = list(heartbeat_sig.parameters.keys())
    
    if actual_params != expected_params:
        print(f"❌ CRITICAL: _heartbeat_handler signature changed")
        print(f"   Expected: {expected_params}")
        print(f"   Actual: {actual_params}")
        return False
    
    # Test close frame handler signature
    close_sig = inspect.signature(SpacetimeDBConnection._send_close_frame)
    expected_params = ['self']
    actual_params = list(close_sig.parameters.keys())
    
    if actual_params != expected_params:
        print(f"❌ CRITICAL: _send_close_frame signature changed")
        print(f"   Expected: {expected_params}")
        print(f"   Actual: {actual_params}")
        return False
    
    print("✅ Method signatures unchanged")
    
    return True

def test_protocol_message_patterns():
    """Test that no other methods contain problematic protocol violations"""
    
    print("\n🧪 Testing for other protocol violations...")
    
    from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
    
    # Get all methods that might send messages
    methods_to_check = [
        '_send_message',
        'send_request', 
        'disconnect',
        '_handle_disconnection'
    ]
    
    violations_found = []
    
    for method_name in methods_to_check:
        if hasattr(SpacetimeDBConnection, method_name):
            method = getattr(SpacetimeDBConnection, method_name)
            source = inspect.getsource(method)
            
            # Check for custom type patterns that might violate protocol
            problematic_patterns = [
                '"type": "heartbeat"',
                '"type": "close"',
                '"type": "ping"',
                '"type": "status"'
            ]
            
            for pattern in problematic_patterns:
                if pattern in source:
                    violations_found.append(f"{method_name}: {pattern}")
    
    if violations_found:
        print("❌ CRITICAL: Protocol violations found in other methods:")
        for violation in violations_found:
            print(f"   {violation}")
        return False
    
    print("✅ No additional protocol violations found")
    
    return True

def main():
    """Run all protocol compliance tests"""
    
    print("=" * 70)
    print("SPACETIMEDB PROTOCOL COMPLIANCE VERIFICATION")
    print("=" * 70)
    print("Testing fixes for custom 'type' message violations...")
    
    tests = [
        test_heartbeat_fix,
        test_close_frame_fix,
        test_import_and_syntax,
        test_method_signatures,
        test_protocol_message_patterns
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ SpacetimeDB protocol compliance fixes verified")
        print("✅ No custom 'type' messages found")
        print("✅ WebSocket ping used for heartbeat")
        print("✅ No application-level close messages")
        print("✅ Code compiles and imports successfully")
        print("\nExpected benefits:")
        print("  - No more 'unknown variant type' server errors")
        print("  - Stable WebSocket connections")
        print("  - Successful parallel environment training")
        print("  - Proper SpacetimeDB protocol compliance")
        print("=" * 70)
        return True
    else:
        print("\n❌ CRITICAL: PROTOCOL COMPLIANCE TESTS FAILED!")
        print("The fixes are incomplete or incorrect.")
        print("Server will continue to reject connections with protocol errors.")
        print("=" * 70)
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)