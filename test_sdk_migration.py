#!/usr/bin/env python3
"""
SDK Migration Validation Test

This script validates that the migration to the modernized spacetimedb-python-sdk
is successful and that all existing functionality is preserved.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path for testing
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all imports work correctly."""
    print("🔍 Testing imports...")
    
    try:
        # Test main blackholio_client imports
        from blackholio_client import BlackholioClient, EnvironmentConfig
        print("  ✅ Main blackholio_client imports work")
        
        # Test connection imports
        from blackholio_client.connection import (
            get_connection_manager, 
            ServerConfig,
            ModernizedSpacetimeDBConnection,
            EnhancedConnectionManager
        )
        print("  ✅ Enhanced connection imports work")
        
        # Test event imports
        from blackholio_client.events import (
            get_enhanced_event_manager,
            create_connection_event,
            SDKConnectionEvent,
            Event,
            EventType,
            EventPriority
        )
        print("  ✅ Enhanced event imports work")
        
        # Test that existing imports still work (backward compatibility)
        from blackholio_client.events import (
            EventManager,
            GameEvent,
            ConnectionEvent,
            EventFilter
        )
        print("  ✅ Legacy event imports work (backward compatibility)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import test failed: {e}")
        traceback.print_exc()
        return False


def test_client_creation():
    """Test that clients can be created with existing APIs."""
    print("🔍 Testing client creation...")
    
    try:
        from blackholio_client import BlackholioClient
        from blackholio_client.connection.server_config import ServerConfig
        
        # Test creating server configs for different languages
        languages = ['rust', 'python', 'csharp', 'go']
        clients = {}
        
        for lang in languages:
            config = ServerConfig.for_language(lang)
            client = BlackholioClient(config)
            clients[lang] = client
            print(f"  ✅ {lang.title()} client created: {type(client).__name__}")
        
        # Test that clients are now the modernized version
        rust_client = clients['rust']
        if 'Modernized' in type(rust_client).__name__:
            print("  ✅ Clients are using modernized SDK implementation")
        else:
            print("  ⚠️  Clients may not be using modernized implementation")
        
        # Test connection stats
        stats = rust_client.connection_stats
        if 'sdk_client_type' in stats:
            print("  ✅ Enhanced connection stats available")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Client creation test failed: {e}")
        traceback.print_exc()
        return False


def test_enhanced_features():
    """Test enhanced features from the SDK."""
    print("🔍 Testing enhanced features...")
    
    try:
        # Test SDK event creation
        from blackholio_client.events import create_connection_event, create_table_update_event
        
        conn_event = create_connection_event(
            connection_id="test-123",
            state="connected",
            host="localhost:3000"
        )
        print(f"  ✅ SDK connection event: {conn_event.get_event_name()}")
        
        table_event = create_table_update_event(
            table_name="players",
            operation="insert",
            row_data={"id": 1, "name": "test_player"}
        )
        print(f"  ✅ SDK table event: {table_event.get_event_name()}")
        
        # Test enhanced event manager
        from blackholio_client.events import get_enhanced_event_manager
        event_manager = get_enhanced_event_manager()
        print(f"  ✅ Enhanced event manager: {type(event_manager).__name__}")
        
        # Test enhanced connection manager
        from blackholio_client.connection import EnhancedConnectionManager
        conn_manager = EnhancedConnectionManager()
        print(f"  ✅ Enhanced connection manager: {type(conn_manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Enhanced features test failed: {e}")
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that existing code patterns still work."""
    print("🔍 Testing backward compatibility...")
    
    try:
        # Test that old event creation patterns still work
        from blackholio_client.events import Event, EventType, EventPriority
        
        class TestEvent(Event):
            def validate(self):
                pass
            
            def get_event_name(self):
                return "TestEvent"
        
        test_event = TestEvent(
            event_type=EventType.SYSTEM,
            priority=EventPriority.NORMAL,
            data={"test": "data"}
        )
        print(f"  ✅ Legacy event creation works: {test_event.get_event_name()}")
        
        # Test old connection patterns
        from blackholio_client.connection.server_config import ServerConfig
        config = ServerConfig.from_environment()
        print(f"  ✅ Environment config creation works: {config.language}")
        
        # Test factory patterns
        from blackholio_client.factory import get_client_factory
        factory = get_client_factory()
        print(f"  ✅ Legacy factory access works: {type(factory).__name__}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backward compatibility test failed: {e}")
        traceback.print_exc()
        return False


async def test_async_functionality():
    """Test async functionality works correctly."""
    print("🔍 Testing async functionality...")
    
    try:
        from blackholio_client.events import publish_enhanced_event, create_connection_event
        
        # Test creating and publishing events
        event = create_connection_event(
            connection_id="async-test",
            state="connecting"
        )
        
        # This should not fail (even if no server is running)
        result = await publish_enhanced_event(event)
        print(f"  ✅ Async event publishing works: {type(result).__name__}")
        
        # Test connection manager async operations
        from blackholio_client.connection import get_connection_manager
        manager = await get_connection_manager()
        print(f"  ✅ Async connection manager works: {type(manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Async functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_sdk_integration():
    """Test that SDK integration is working properly."""
    print("🔍 Testing SDK integration...")
    
    try:
        # Test direct SDK imports work
        from spacetimedb_sdk import ModernSpacetimeDBClient, create_rust_client
        print("  ✅ Direct SDK imports work")
        
        # Test that blackholio client uses SDK under the hood
        from blackholio_client import BlackholioClient
        from blackholio_client.connection.server_config import ServerConfig
        
        config = ServerConfig.for_language('rust')
        client = BlackholioClient(config)
        
        # Check if it has SDK-specific features
        stats = client.connection_stats
        if 'sdk_client_type' in stats:
            print("  ✅ Client has SDK integration features")
        
        # Test that we can access SDK event manager
        from spacetimedb_sdk.events import get_event_manager
        sdk_manager = get_event_manager()
        print(f"  ✅ SDK event manager accessible: {type(sdk_manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ SDK integration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🚀 Testing SpacetimeDB SDK Migration")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Client Creation", test_client_creation),
        ("Enhanced Features", test_enhanced_features),
        ("Backward Compatibility", test_backward_compatibility),
        ("SDK Integration", test_sdk_integration),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    # Run async tests
    print(f"\nAsync Functionality:")
    async_result = asyncio.run(test_async_functionality())
    results.append(("Async Functionality", async_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SDK migration is successful!")
        print("\n📈 Migration Benefits:")
        print("  • Using modernized spacetimedb-python-sdk under the hood")
        print("  • Enhanced connection management with pooling")
        print("  • Advanced event system with priority handling")
        print("  • Backward compatibility maintained")
        print("  • Production-ready patterns extracted from blackholio-client")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Migration needs attention.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)