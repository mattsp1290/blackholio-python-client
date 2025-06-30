#!/usr/bin/env python3
"""
Protocol Debugging Example for Blackholio Client

This script demonstrates how to use the enhanced protocol validation
and debugging features to troubleshoot connection issues.
"""

import asyncio
import logging
from src.blackholio_client.connection.spacetimedb_connection import BlackholioClient

# Set up logging to see protocol validation messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def protocol_debugging_example():
    """Example of using protocol debugging features."""
    
    # Create client instance
    client = BlackholioClient()
    
    # Enable protocol debugging for detailed logging
    client.enable_protocol_debugging()
    
    try:
        # Attempt connection
        print("Attempting to connect to SpacetimeDB...")
        success = await client.connect()
        
        if success:
            print("✅ Connection successful!")
            
            # Get protocol information
            protocol_info = client.get_protocol_info()
            print(f"📊 Protocol Information:")
            for key, value in protocol_info.items():
                print(f"  {key}: {value}")
            
            # Wait for some messages to demonstrate frame type validation
            print("🔍 Monitoring for protocol validation warnings...")
            await asyncio.sleep(5)
            
        else:
            print("❌ Connection failed!")
            
            # Still show protocol info even if connection failed
            protocol_info = client.get_protocol_info()
            print(f"📊 Protocol Information (failed connection):")
            for key, value in protocol_info.items():
                print(f"  {key}: {value}")
    
    except Exception as e:
        print(f"❌ Error during connection: {e}")
        
        # Show protocol info for debugging
        protocol_info = client.get_protocol_info()
        print(f"📊 Protocol Information (error state):")
        for key, value in protocol_info.items():
            print(f"  {key}: {value}")
    
    finally:
        try:
            await client.disconnect()
            print("🔌 Disconnected from SpacetimeDB")
        except Exception as e:
            print(f"⚠️  Error during disconnect: {e}")

def main():
    """Main function."""
    print("🚀 Blackholio Client Protocol Debugging Example")
    print("=" * 50)
    print()
    print("This example demonstrates the enhanced protocol validation")
    print("and debugging features implemented to address protocol")
    print("mismatch issues reported in the SpacetimeDB integration.")
    print()
    print("Expected warnings to look for:")
    print("• 'Received BINARY frame with v1.json.spacetimedb protocol'")
    print("• 'Unknown message type in data: {'IdentityToken': {...}}'") 
    print("• 'Protocol mismatch - requested JSON but got: ...'")
    print()
    
    try:
        asyncio.run(protocol_debugging_example())
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()