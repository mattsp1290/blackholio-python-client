#!/usr/bin/env python3
"""
Integration test for blackholio-python-client
Tests connection, subscription flow, and data retrieval
"""
import asyncio
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blackholio_client import BlackholioClient
from blackholio_client.connection.server_config import ServerConfig


class IntegrationTest:
    def __init__(self):
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        self.client = None
        
    def log(self, level: str, message: str, data: Any = None):
        """Log with structured format"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        if data:
            log_entry["data"] = data
        
        # Color coding for terminal
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m", 
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "DEBUG": "\033[90m"
        }
        reset = "\033[0m"
        
        print(f"{colors.get(level, '')}{timestamp} [{level}] {message}{reset}")
        if data:
            print(f"{colors.get(level, '')}  Data: {json.dumps(data, indent=2)}{reset}")
    
    def add_test_result(self, test_name: str, passed: bool, message: str, details: Dict[str, Any] = None):
        """Record test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            result["details"] = details
            
        self.results["tests"].append(result)
        self.results["summary"]["total"] += 1
        
        if passed:
            self.results["summary"]["passed"] += 1
            self.log("SUCCESS", f"✓ {test_name}: {message}", details)
        else:
            self.results["summary"]["failed"] += 1
            self.log("ERROR", f"✗ {test_name}: {message}", details)
    
    async def test_connection(self):
        """Test 1: Basic connection to SpacetimeDB"""
        self.log("INFO", "Starting connection test...")
        
        try:
            # Get server details from environment or use defaults
            server_url = os.environ.get("SPACETIMEDB_URL", "ws://localhost:3000")
            module_name = os.environ.get("MODULE_NAME", "blackholio")
            
            self.log("INFO", f"Connecting to {server_url}/{module_name}")
            
            # Parse server URL
            if server_url.startswith('ws://') or server_url.startswith('wss://'):
                use_ssl = server_url.startswith('wss://')
                url_parts = server_url.replace('ws://', '').replace('wss://', '').split(':')
                server_ip = url_parts[0]
                server_port = int(url_parts[1]) if len(url_parts) > 1 else (443 if use_ssl else 3000)
            else:
                # Assume ws:// by default
                use_ssl = False
                url_parts = server_url.split(':')
                server_ip = url_parts[0]
                server_port = int(url_parts[1]) if len(url_parts) > 1 else 3000
            
            # Create server config
            config = ServerConfig(
                language='rust',  # Blackholio uses Rust
                host=f"{server_ip}:{server_port}",
                port=server_port,
                db_identity=module_name,
                protocol='v1.bsatn.spacetimedb',
                use_ssl=use_ssl
            )
            
            self.log("DEBUG", "Created config", {
                "server_ip": server_ip,
                "server_port": server_port,
                "module": module_name,
                "use_ssl": use_ssl,
                "host": config.host
            })
            
            # Create client with config
            self.client = BlackholioClient(config)
            
            # Attempt connection
            start_time = time.time()
            
            try:
                # The BlackholioClient connect method returns success/failure
                connected = await asyncio.wait_for(
                    self.client.connect(),
                    timeout=10.0
                )
                connection_time = time.time() - start_time
                
                if connected:
                    # Check if actually connected
                    if hasattr(self.client, 'is_connected') and self.client.is_connected:
                        self.add_test_result(
                            "connection",
                            True,
                            "Successfully connected to SpacetimeDB",
                            {"connection_time": connection_time, "url": f"{server_url}/{module_name}"}
                        )
                        return True
                    else:
                        self.add_test_result(
                            "connection",
                            False,
                            "Connection method returned True but not actually connected",
                            {"time": connection_time}
                        )
                        return False
                else:
                    self.add_test_result(
                        "connection",
                        False,
                        "Connection failed - returned False",
                        {"time": connection_time}
                    )
                    return False
                    
            except asyncio.TimeoutError:
                self.add_test_result(
                    "connection",
                    False,
                    "Connection timeout after 10 seconds",
                    {"url": f"{server_url}/{module_name}"}
                )
                return False
                
        except Exception as e:
            self.add_test_result(
                "connection",
                False,
                f"Unexpected error during connection: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_subscription_registration(self):
        """Test 2: Verify subscription callbacks are registered"""
        self.log("INFO", "Testing subscription registration...")
        
        if not self.client:
            self.add_test_result(
                "subscription_registration",
                False,
                "Cannot test subscriptions - no client connection"
            )
            return False
        
        try:
            # Check subscription manager state
            sub_manager = getattr(self.client, '_subscription_manager', None)
            if not sub_manager:
                self.add_test_result(
                    "subscription_registration", 
                    False,
                    "No subscription manager found"
                )
                return False
            
            # Get callback counts
            callbacks = {}
            for event_type in ['insert', 'update', 'delete']:
                handler = getattr(sub_manager, f'_on_{event_type}', {})
                total_callbacks = sum(len(table_callbacks) for table_callbacks in handler.values())
                callbacks[event_type] = total_callbacks
            
            # Check if any callbacks are registered
            total_callbacks = sum(callbacks.values())
            
            if total_callbacks > 0:
                self.add_test_result(
                    "subscription_registration",
                    True,
                    f"Found {total_callbacks} subscription callbacks registered",
                    {"callbacks": callbacks}
                )
                return True
            else:
                # This might be expected if no explicit subscriptions were set
                self.add_test_result(
                    "subscription_registration",
                    True,
                    "No callbacks registered (this may be expected)",
                    {"note": "Subscriptions may be registered later or on-demand"}
                )
                return True
                
        except Exception as e:
            self.add_test_result(
                "subscription_registration",
                False,
                f"Error checking subscriptions: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_table_access(self):
        """Test 3: Try to access game tables"""
        self.log("INFO", "Testing table access...")
        
        if not self.client:
            self.add_test_result(
                "table_access",
                False,
                "Cannot test table access - no client connection"
            )
            return False
        
        try:
            # Test various table access methods
            table_tests = []
            
            # Test 1: Direct table access
            players_table = getattr(self.client, 'Players', None)
            entities_table = getattr(self.client, 'Entities', None)
            
            table_tests.append({
                "method": "direct_attribute",
                "found_players": players_table is not None,
                "found_entities": entities_table is not None
            })
            
            # Test 2: get_all methods
            try:
                players = await asyncio.wait_for(
                    asyncio.create_task(self.client.get_all_players()),
                    timeout=2.0
                )
                entities = await asyncio.wait_for(
                    asyncio.create_task(self.client.get_all_entities()),
                    timeout=2.0
                )
                
                table_tests.append({
                    "method": "get_all_methods",
                    "players_count": len(players) if players else 0,
                    "entities_count": len(entities) if entities else 0,
                    "players_type": type(players).__name__,
                    "entities_type": type(entities).__name__
                })
            except asyncio.TimeoutError:
                table_tests.append({
                    "method": "get_all_methods",
                    "error": "Timeout waiting for data"
                })
            except AttributeError as e:
                table_tests.append({
                    "method": "get_all_methods",
                    "error": f"Methods not found: {str(e)}"
                })
            
            # Determine if test passed
            has_table_access = any(
                test.get("found_players") or test.get("found_entities") or 
                test.get("players_count", 0) > 0 or test.get("entities_count", 0) > 0
                for test in table_tests
            )
            
            if has_table_access:
                self.add_test_result(
                    "table_access",
                    True,
                    "Successfully accessed game tables",
                    {"tests": table_tests}
                )
            else:
                self.add_test_result(
                    "table_access",
                    False,
                    "Could not access game tables or no data found",
                    {"tests": table_tests, "note": "This is the known issue - tables exist but client can't find data"}
                )
            
            return has_table_access
            
        except Exception as e:
            self.add_test_result(
                "table_access",
                False,
                f"Unexpected error accessing tables: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_reducer_call(self):
        """Test 4: Try to call a reducer"""
        self.log("INFO", "Testing reducer calls...")
        
        if not self.client:
            self.add_test_result(
                "reducer_call",
                False,
                "Cannot test reducers - no client connection"
            )
            return False
        
        try:
            # Generate a test player name
            test_name = f"test_player_{int(time.time())}"
            
            # Try to join the game
            self.log("DEBUG", f"Attempting to join game as '{test_name}'")
            
            # Set up event to track reducer response
            reducer_called = asyncio.Event()
            reducer_error = None
            
            async def on_reducer_error(error):
                nonlocal reducer_error
                reducer_error = error
                reducer_called.set()
            
            # Some clients may have error callbacks
            if hasattr(self.client, 'on_reducer_error'):
                self.client.on_reducer_error(on_reducer_error)
            
            # Try to call join_game reducer
            try:
                # First check if method exists
                # Check for reducer methods
                if hasattr(self.client, 'join_game'):
                    # Direct method
                    result = await asyncio.wait_for(
                        asyncio.create_task(self.client.join_game(test_name)),
                        timeout=5.0
                    )
                elif hasattr(self.client, 'call_reducer'):
                    # Generic reducer call method
                    result = await asyncio.wait_for(
                        asyncio.create_task(self.client.call_reducer('join_game', {'name': test_name})),
                        timeout=5.0
                    )
                else:
                    self.add_test_result(
                        "reducer_call",
                        False,
                        "No reducer call method found on client",
                        {"available_methods": [m for m in dir(self.client) if not m.startswith('_')]}
                    )
                    return False
                
                # Check if we got a response
                if result is not None:
                    self.add_test_result(
                        "reducer_call",
                        True,
                        "Successfully called join_game reducer",
                        {"player_name": test_name, "result": str(result)}
                    )
                    return True
                else:
                    # Even None response means the call went through
                    self.add_test_result(
                        "reducer_call",
                        True,
                        "join_game reducer called (no response data)",
                        {"player_name": test_name, "note": "Reducer may have succeeded server-side"}
                    )
                    return True
                    
            except asyncio.TimeoutError:
                self.add_test_result(
                    "reducer_call",
                    False,
                    "Timeout waiting for reducer response",
                    {"player_name": test_name, "timeout": 5.0}
                )
                return False
                
        except Exception as e:
            self.add_test_result(
                "reducer_call",
                False,
                f"Error calling reducer: {str(e)}",
                {"error_type": type(e).__name__, "error": str(e)}
            )
            return False
    
    async def test_subscription_data_flow(self):
        """Test 5: Check if subscription data flows after actions"""
        self.log("INFO", "Testing subscription data flow...")
        
        if not self.client:
            self.add_test_result(
                "subscription_data_flow",
                False,
                "Cannot test data flow - no client connection"
            )
            return False
        
        try:
            # Set up data tracking
            received_events = []
            
            # Try to subscribe to player updates
            async def on_player_insert(player):
                received_events.append({"type": "player_insert", "data": player})
                self.log("DEBUG", "Received player insert event", player)
            
            async def on_entity_insert(entity):
                received_events.append({"type": "entity_insert", "data": entity})
                self.log("DEBUG", "Received entity insert event", entity)
            
            # Register callbacks (method depends on client implementation)
            if hasattr(self.client, 'on_player_insert'):
                self.client.on_player_insert(on_player_insert)
            elif hasattr(self.client, 'on'):
                # Generic event subscription
                self.client.on('player_insert', on_player_insert)
                
            if hasattr(self.client, 'on_entity_insert'):
                self.client.on_entity_insert(on_entity_insert)
            elif hasattr(self.client, 'on'):
                self.client.on('entity_insert', on_entity_insert)
            
            # Trigger an action that should generate events
            test_name = f"flow_test_{int(time.time())}"
            
            try:
                if hasattr(self.client, 'join_game'):
                    await self.client.join_game(test_name)
                elif hasattr(self.client, 'call_reducer'):
                    await self.client.call_reducer('join_game', {'name': test_name})
                    
                # Wait a bit for events to flow
                await asyncio.sleep(2.0)
                
                # Also try to get fresh data
                if hasattr(self.client, 'get_all_players'):
                    players = await self.client.get_all_players()
                    self.log("DEBUG", f"Found {len(players) if players else 0} players after action")
                
            except Exception as e:
                self.log("WARNING", f"Error during test action: {e}")
            
            # Check results
            if received_events:
                self.add_test_result(
                    "subscription_data_flow",
                    True,
                    f"Received {len(received_events)} subscription events",
                    {"events": received_events}
                )
                return True
            else:
                self.add_test_result(
                    "subscription_data_flow",
                    False,
                    "No subscription events received",
                    {"note": "This is the known critical issue - subscription data not flowing"}
                )
                return False
                
        except Exception as e:
            self.add_test_result(
                "subscription_data_flow",
                False,
                f"Error testing subscription flow: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        self.log("INFO", "Starting blackholio-python-client integration tests")
        self.log("INFO", "=" * 60)
        
        try:
            # Run tests in sequence
            tests = [
                ("Connection Test", self.test_connection),
                ("Subscription Registration", self.test_subscription_registration),
                ("Table Access", self.test_table_access),
                ("Reducer Calls", self.test_reducer_call),
                ("Subscription Data Flow", self.test_subscription_data_flow)
            ]
            
            for test_name, test_func in tests:
                self.log("INFO", f"\nRunning: {test_name}")
                self.log("INFO", "-" * 40)
                
                try:
                    await test_func()
                except Exception as e:
                    self.log("ERROR", f"Test crashed: {e}")
                    self.add_test_result(
                        test_name.lower().replace(" ", "_"),
                        False,
                        f"Test crashed with exception: {str(e)}",
                        {"error_type": type(e).__name__}
                    )
                
                # Small delay between tests
                await asyncio.sleep(0.5)
            
        finally:
            # Clean up
            if self.client:
                try:
                    await self.client.disconnect()
                except:
                    pass
            
            # Print summary
            self.log("INFO", "\n" + "=" * 60)
            self.log("INFO", "TEST SUMMARY")
            self.log("INFO", "=" * 60)
            
            summary = self.results["summary"]
            total = summary["total"]
            passed = summary["passed"]
            failed = summary["failed"]
            
            # Color-coded summary
            if failed == 0:
                self.log("SUCCESS", f"All tests passed! ({passed}/{total})")
            else:
                self.log("ERROR", f"Tests failed: {failed}/{total} (Passed: {passed})")
            
            # Known issues summary
            self.log("INFO", "\nKnown Issues:")
            self.log("WARNING", "- Client queries return empty arrays despite data existing in DB")
            self.log("WARNING", "- Subscription data flow not working (critical issue)")
            self.log("WARNING", "- These are the issues blocking ML training in blackholio-agent")
            
            # Save results to file
            self.results["end_time"] = datetime.now().isoformat()
            with open("integration_test_results.json", "w") as f:
                json.dump(self.results, f, indent=2)
            
            self.log("INFO", "\nDetailed results saved to: integration_test_results.json")
            
            # Exit with appropriate code
            sys.exit(0 if failed == 0 else 1)


async def main():
    test = IntegrationTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())