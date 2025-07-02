#!/usr/bin/env python3
"""Debug script to understand subscription data structure."""

import asyncio
import logging
import sys
import json
sys.path.insert(0, 'src')

from blackholio_client import GameClient

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_subscription():
    """Debug the subscription data structure."""
    print("\n" + "="*60)
    print("🔍 Debugging Subscription Data Structure")
    print("="*60 + "\n")
    
    client = GameClient("localhost:3000", "blackholio")
    
    # Monkey-patch to see what data we get
    original_handler = client._handle_initial_subscription_data
    
    async def debug_handler(data):
        print(f"\n🔍 Handler received:")
        print(f"   Type: {type(data)}")
        if isinstance(data, dict):
            print(f"   Keys: {list(data.keys())}")
            if 'subscription_data' in data:
                sub_data = data['subscription_data']
                print(f"   subscription_data type: {type(sub_data)}")
                if isinstance(sub_data, dict):
                    print(f"   subscription_data keys: {list(sub_data.keys())[:10]}")
                    # Check for common keys
                    for key in ['database_update', 'tables', 'DatabaseUpdate']:
                        if key in sub_data:
                            print(f"   ✓ Found '{key}' in subscription_data")
                            if isinstance(sub_data[key], dict):
                                print(f"     {key} keys: {list(sub_data[key].keys())[:5]}")
                elif sub_data is None:
                    print("   ❌ subscription_data is None!")
        
        # Still call original to see if it errors
        try:
            return await original_handler(data)
        except Exception as e:
            print(f"\n❌ Original handler error: {e}")
            import traceback
            traceback.print_exc()
    
    client._handle_initial_subscription_data = debug_handler
    
    # Also check what's stored
    async def check_stored_data():
        await asyncio.sleep(0.2)  # Let connection process
        if hasattr(client._active_connection, '_last_initial_subscription'):
            stored = client._active_connection._last_initial_subscription
            print(f"\n📦 Stored subscription data:")
            print(f"   Type: {type(stored)}")
            if isinstance(stored, dict):
                print(f"   Keys: {list(stored.keys())[:10]}")
                # Sample the structure
                for key in list(stored.keys())[:3]:
                    value = stored[key]
                    if isinstance(value, (dict, list)):
                        print(f"   {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        print(f"   {key}: {type(value).__name__}")
    
    # Connect and wait a bit
    connected = await client.connect()
    if connected:
        await check_stored_data()
        await asyncio.sleep(0.5)
    
    await client.disconnect()
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(debug_subscription())