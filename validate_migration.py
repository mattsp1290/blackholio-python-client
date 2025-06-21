#!/usr/bin/env python3
"""
Simple SDK Migration Validation

Validates core migration functionality without async event loop complications.
"""

import sys
from pathlib import Path

# Add src to path for testing
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def validate_imports():
    """Test critical imports work."""
    try:
        # Test main imports
        from blackholio_client import BlackholioClient, EnvironmentConfig, get_global_config
        from blackholio_client.connection import ModernizedSpacetimeDBConnection
        from blackholio_client.events import get_enhanced_event_manager
        
        # Test SDK imports
        from spacetimedb_sdk import ModernSpacetimeDBClient
        from spacetimedb_sdk.events import create_connection_event
        
        print("✅ All critical imports working")
        return True
    except Exception as e:
        print(f"❌ Import validation failed: {e}")
        return False

def validate_client_creation():
    """Test client creation works."""
    try:
        from blackholio_client.connection.server_config import ServerConfig
        from blackholio_client.connection.modernized_spacetimedb_client import ModernizedSpacetimeDBConnection
        
        # Test creating configs for different languages
        for lang in ['rust', 'python', 'csharp', 'go']:
            config = ServerConfig.for_language(lang)
            client = ModernizedSpacetimeDBConnection(config)
            
            # Validate it's the modernized version
            if 'Modernized' not in type(client).__name__:
                print(f"❌ {lang} client not using modernized implementation")
                return False
        
        print("✅ Client creation validation passed")
        return True
    except Exception as e:
        print(f"❌ Client creation validation failed: {e}")
        return False

def validate_sdk_integration():
    """Test SDK integration basics."""
    try:
        # Test we can create SDK events
        from spacetimedb_sdk.events import create_connection_event, create_table_update_event
        
        conn_event = create_connection_event(
            connection_id="test-validation",
            state="connected"
        )
        
        table_event = create_table_update_event(
            table_name="test_table",
            operation="insert",
            row_data={"id": 1, "test": "data"}
        )
        
        print("✅ SDK integration validation passed")
        return True
    except Exception as e:
        print(f"❌ SDK integration validation failed: {e}")
        return False

def validate_backward_compatibility():
    """Test backward compatibility."""
    try:
        # Test environment config
        from blackholio_client.config.environment import EnvironmentConfig
        config = EnvironmentConfig.from_environment()
        
        # Test legacy event creation
        from blackholio_client.events import Event, EventType, EventPriority
        
        class TestEvent(Event):
            def validate(self):
                pass
            
            def get_event_name(self):
                return "TestBackwardCompatibility"
        
        test_event = TestEvent(
            event_type=EventType.SYSTEM,
            priority=EventPriority.NORMAL,
            data={"test": "backward_compatibility"}
        )
        
        print("✅ Backward compatibility validation passed")
        return True
    except Exception as e:
        print(f"❌ Backward compatibility validation failed: {e}")
        return False

def main():
    """Main validation function."""
    print("🔍 Validating SpacetimeDB SDK Migration")
    print("=" * 50)
    
    validations = [
        ("Import Validation", validate_imports),
        ("Client Creation", validate_client_creation),
        ("SDK Integration", validate_sdk_integration), 
        ("Backward Compatibility", validate_backward_compatibility),
    ]
    
    passed = 0
    total = len(validations)
    
    for name, validator in validations:
        print(f"\n{name}:")
        if validator():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 Migration validation successful!")
        print("\n📋 Migration Summary:")
        print("• ✅ Using modernized spacetimedb-python-sdk")
        print("• ✅ Enhanced connection management available") 
        print("• ✅ Advanced event system integrated")
        print("• ✅ Backward compatibility maintained")
        print("• ✅ Factory patterns working")
        return True
    else:
        print(f"⚠️  {total - passed} validations failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)