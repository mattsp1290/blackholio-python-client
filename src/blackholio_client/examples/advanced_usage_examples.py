"""
Advanced Usage Examples for Blackholio Python Client.

Demonstrates sophisticated usage patterns including Docker integration,
monitoring, performance optimization, concurrent operations, and production
deployment patterns.
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from ..client import create_game_client, GameClient
from ..models.game_entities import Vector2, GameEntity, GamePlayer
from ..connection.connection_manager import get_connection_manager
from ..events import get_global_event_manager, EventType
from ..utils.debugging import PerformanceProfiler, DebugCapture
from ..utils.error_handling import RetryManager, CircuitBreaker
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionGameClient:
    """
    Production-ready game client with comprehensive error handling,
    monitoring, and performance optimization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[GameClient] = None
        self.performance_profiler = PerformanceProfiler()
        self.retry_manager = RetryManager(
            max_attempts=config.get('max_retries', 5),
            backoff_strategy='exponential',
            base_delay=config.get('retry_delay', 1.0)
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get('failure_threshold', 5),
            recovery_timeout=config.get('recovery_timeout', 30.0)
        )
        self.metrics = {
            'connections': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_entities_processed': 0,
            'uptime_start': time.time()
        }
        self.is_running = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the production client with full initialization."""
        logger.info("🚀 Starting production game client...")
        
        try:
            # Create client with production configuration
            self.client = create_game_client(
                host=self.config.get('host', 'localhost:3000'),
                database=self.config.get('database', 'blackholio'),
                server_language=self.config.get('server_language', 'rust'),
                auto_reconnect=True
            )
            
            # Configure production settings
            self.client.enable_auto_reconnect(
                max_attempts=self.config.get('reconnect_attempts', 10),
                delay=self.config.get('reconnect_delay', 2.0),
                exponential_backoff=True
            )
            
            # Set up event handlers
            self._setup_event_handlers()
            
            # Connect with retry logic
            async def connect_operation():
                return await self.client.connect()
            
            connected = await self.retry_manager.execute(connect_operation)
            
            if connected:
                self.metrics['connections'] += 1
                self.is_running = True
                logger.info("✅ Production client started successfully")
                
                # Start background monitoring
                asyncio.create_task(self._monitoring_loop())
                
                return True
            else:
                raise ConnectionError("Failed to establish connection")
                
        except Exception as e:
            logger.error(f"❌ Failed to start production client: {e}")
            raise
    
    async def stop(self):
        """Gracefully stop the production client."""
        logger.info("🛑 Stopping production client...")
        
        self.is_running = False
        
        if self.client:
            try:
                await self.client.shutdown()
                logger.info("✅ Production client stopped gracefully")
            except Exception as e:
                logger.error(f"⚠️ Error during shutdown: {e}")
        
        # Log final metrics
        self._log_final_metrics()
    
    def _setup_event_handlers(self):
        """Set up comprehensive event handling."""
        
        def on_connection_state_changed(state):
            logger.info(f"Connection state changed: {state.value}")
            if state.value == "CONNECTED":
                self.metrics['connections'] += 1
        
        def on_error(error_message):
            logger.error(f"Client error: {error_message}")
            self.metrics['failed_operations'] += 1
        
        def on_entity_created(entity: GameEntity):
            self.metrics['total_entities_processed'] += 1
            logger.debug(f"Entity created: {entity.entity_id}")
        
        self.client.on_connection_state_changed(on_connection_state_changed)
        self.client.on_error(on_error)
        self.client.on_entity_created(on_entity_created)
    
    async def join_game_with_monitoring(self, player_name: str) -> bool:
        """Join game with performance monitoring and error handling."""
        
        self.performance_profiler.start_checkpoint("join_game")
        
        try:
            async def join_operation():
                return await self.client.join_game(player_name)
            
            # Use circuit breaker for protection
            success = await self.circuit_breaker.call(join_operation)
            
            if success:
                self.metrics['successful_operations'] += 1
                logger.info(f"✅ Joined game as {player_name}")
            else:
                self.metrics['failed_operations'] += 1
                logger.warning(f"❌ Failed to join game as {player_name}")
            
            return success
            
        except Exception as e:
            self.metrics['failed_operations'] += 1
            logger.error(f"❌ Error joining game: {e}")
            return False
        
        finally:
            self.performance_profiler.end_checkpoint("join_game")
    
    async def perform_game_operations(self, operations: List[Dict[str, Any]]):
        """Perform a series of game operations with optimization."""
        
        logger.info(f"Performing {len(operations)} game operations...")
        
        successful_ops = 0
        failed_ops = 0
        
        for i, operation in enumerate(operations):
            try:
                op_type = operation.get('type')
                
                if op_type == 'move':
                    direction = Vector2(operation['x'], operation['y'])
                    await self.client.move_player(direction)
                    
                elif op_type == 'split':
                    await self.client.player_split()
                    
                elif op_type == 'wait':
                    await asyncio.sleep(operation.get('duration', 0.1))
                
                successful_ops += 1
                self.metrics['successful_operations'] += 1
                
                # Rate limiting
                if i % 10 == 0:
                    await asyncio.sleep(0.01)  # Brief pause every 10 operations
                    
            except Exception as e:
                failed_ops += 1
                self.metrics['failed_operations'] += 1
                logger.warning(f"Operation {i} failed: {e}")
        
        logger.info(f"Operations completed: {successful_ops} successful, {failed_ops} failed")
        
        return {'successful': successful_ops, 'failed': failed_ops}
    
    async def _monitoring_loop(self):
        """Background monitoring loop for health checks and metrics."""
        
        while self.is_running:
            try:
                # Collect metrics
                if self.client and self.client.is_connected():
                    stats = self.client.get_client_statistics()
                    
                    # Log key metrics every minute
                    uptime = time.time() - self.metrics['uptime_start']
                    logger.info(f"📊 Client Health - Uptime: {uptime:.0f}s, "
                              f"Successful Ops: {self.metrics['successful_operations']}, "
                              f"Failed Ops: {self.metrics['failed_operations']}")
                
                # Health check
                if not self.client.is_connected():
                    logger.warning("⚠️ Connection lost - auto-reconnect should handle")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    def _log_final_metrics(self):
        """Log final performance metrics."""
        uptime = time.time() - self.metrics['uptime_start']
        
        logger.info("📊 Final Production Client Metrics:")
        logger.info(f"  Total Uptime: {uptime:.1f} seconds")
        logger.info(f"  Connections: {self.metrics['connections']}")
        logger.info(f"  Successful Operations: {self.metrics['successful_operations']}")
        logger.info(f"  Failed Operations: {self.metrics['failed_operations']}")
        logger.info(f"  Entities Processed: {self.metrics['total_entities_processed']}")
        
        # Calculate success rate
        total_ops = self.metrics['successful_operations'] + self.metrics['failed_operations']
        if total_ops > 0:
            success_rate = (self.metrics['successful_operations'] / total_ops) * 100
            logger.info(f"  Success Rate: {success_rate:.1f}%")


class ConcurrentGameManager:
    """
    Manages multiple concurrent game clients for load testing and
    multi-instance scenarios.
    """
    
    def __init__(self, num_clients: int = 5, server_configs: List[Dict] = None):
        self.num_clients = num_clients
        self.server_configs = server_configs or [
            {'host': 'localhost:3000', 'server_language': 'rust'},
            {'host': 'localhost:3001', 'server_language': 'python'},
            {'host': 'localhost:3002', 'server_language': 'csharp'},
            {'host': 'localhost:3003', 'server_language': 'go'}
        ]
        self.clients: List[GameClient] = []
        self.client_tasks: List[asyncio.Task] = []
        self.results: List[Dict] = []
    
    async def start_concurrent_clients(self):
        """Start multiple clients concurrently across different servers."""
        
        logger.info(f"🚀 Starting {self.num_clients} concurrent clients...")
        
        # Create clients
        for i in range(self.num_clients):
            config = self.server_configs[i % len(self.server_configs)]
            
            client = create_game_client(
                host=config['host'],
                server_language=config['server_language'],
                auto_reconnect=True
            )
            
            self.clients.append(client)
        
        # Start all clients concurrently
        async def start_client(client_id: int, client: GameClient):
            try:
                logger.info(f"Starting client {client_id}...")
                connected = await client.connect()
                
                if connected:
                    joined = await client.join_game(f"ConcurrentPlayer_{client_id}")
                    
                    if joined:
                        logger.info(f"✅ Client {client_id} ready")
                        return {'client_id': client_id, 'status': 'ready', 'client': client}
                    else:
                        logger.warning(f"❌ Client {client_id} failed to join game")
                        return {'client_id': client_id, 'status': 'join_failed', 'client': client}
                else:
                    logger.warning(f"❌ Client {client_id} failed to connect")
                    return {'client_id': client_id, 'status': 'connection_failed', 'client': client}
                    
            except Exception as e:
                logger.error(f"❌ Client {client_id} error: {e}")
                return {'client_id': client_id, 'status': 'error', 'error': str(e), 'client': client}
        
        # Start all clients
        tasks = [start_client(i, client) for i, client in enumerate(self.clients)]
        self.results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful starts
        successful_clients = sum(1 for result in self.results 
                               if isinstance(result, dict) and result.get('status') == 'ready')
        
        logger.info(f"📊 Concurrent client startup: {successful_clients}/{self.num_clients} successful")
        
        return successful_clients
    
    async def run_load_test(self, duration_seconds: int = 60, operations_per_second: int = 10):
        """Run load test with multiple concurrent clients."""
        
        logger.info(f"🔥 Starting load test: {duration_seconds}s duration, "
                   f"{operations_per_second} ops/sec per client")
        
        # Filter to ready clients
        ready_clients = [result['client'] for result in self.results 
                        if isinstance(result, dict) and result.get('status') == 'ready']
        
        if not ready_clients:
            logger.error("❌ No ready clients for load test")
            return
        
        # Define load test operations
        operations = [
            {'type': 'move', 'x': 1.0, 'y': 0.0},
            {'type': 'move', 'x': -1.0, 'y': 0.0},
            {'type': 'move', 'x': 0.0, 'y': 1.0},
            {'type': 'move', 'x': 0.0, 'y': -1.0},
            {'type': 'split'},
            {'type': 'wait', 'duration': 0.1}
        ]
        
        async def client_load_test(client: GameClient, client_id: int):
            """Run load test for a single client."""
            operations_completed = 0
            errors = 0
            start_time = time.time()
            
            try:
                while time.time() - start_time < duration_seconds:
                    # Perform operations
                    for _ in range(operations_per_second):
                        try:
                            # Random operation
                            import random
                            operation = random.choice(operations)
                            
                            if operation['type'] == 'move':
                                await client.move_player(Vector2(operation['x'], operation['y']))
                            elif operation['type'] == 'split':
                                await client.player_split()
                            elif operation['type'] == 'wait':
                                await asyncio.sleep(operation['duration'])
                            
                            operations_completed += 1
                            
                        except Exception as e:
                            errors += 1
                            logger.debug(f"Client {client_id} operation error: {e}")
                    
                    # Rate limiting
                    await asyncio.sleep(1.0 / operations_per_second)
                
            except Exception as e:
                logger.error(f"Client {client_id} load test error: {e}")
            
            return {
                'client_id': client_id,
                'operations_completed': operations_completed,
                'errors': errors,
                'duration': time.time() - start_time
            }
        
        # Run load test on all clients
        load_test_tasks = [client_load_test(client, i) for i, client in enumerate(ready_clients)]
        load_results = await asyncio.gather(*load_test_tasks, return_exceptions=True)
        
        # Analyze results
        total_operations = sum(result.get('operations_completed', 0) for result in load_results 
                             if isinstance(result, dict))
        total_errors = sum(result.get('errors', 0) for result in load_results 
                          if isinstance(result, dict))
        
        logger.info(f"📊 Load Test Results:")
        logger.info(f"  Total Operations: {total_operations}")
        logger.info(f"  Total Errors: {total_errors}")
        logger.info(f"  Operations/Second: {total_operations / duration_seconds:.1f}")
        logger.info(f"  Error Rate: {(total_errors / max(total_operations, 1)) * 100:.1f}%")
        
        return {
            'total_operations': total_operations,
            'total_errors': total_errors,
            'ops_per_second': total_operations / duration_seconds,
            'error_rate': (total_errors / max(total_operations, 1)) * 100,
            'client_results': load_results
        }
    
    async def shutdown_all_clients(self):
        """Gracefully shutdown all clients."""
        logger.info("🛑 Shutting down all concurrent clients...")
        
        shutdown_tasks = []
        for client in self.clients:
            if client:
                shutdown_tasks.append(client.shutdown())
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("✅ All clients shut down")


class MonitoringDashboard:
    """
    Real-time monitoring dashboard for game client metrics.
    """
    
    def __init__(self, clients: List[GameClient]):
        self.clients = clients
        self.metrics_history = []
        self.is_monitoring = False
    
    async def start_monitoring(self, interval_seconds: int = 5):
        """Start real-time monitoring of all clients."""
        logger.info("📊 Starting monitoring dashboard...")
        
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                # Collect metrics from all clients
                timestamp = time.time()
                metrics = {
                    'timestamp': timestamp,
                    'clients': []
                }
                
                for i, client in enumerate(self.clients):
                    if client and client.is_connected():
                        try:
                            client_stats = client.get_client_statistics()
                            client_state = client.get_client_state()
                            
                            client_metrics = {
                                'client_id': i,
                                'connected': client.is_connected(),
                                'in_game': client.is_in_game(),
                                'entities_count': len(client.get_all_entities()),
                                'players_count': len(client.get_all_players()),
                                'stats': client_stats,
                                'state': client_state
                            }
                            
                            metrics['clients'].append(client_metrics)
                            
                        except Exception as e:
                            logger.warning(f"Failed to collect metrics for client {i}: {e}")
                            metrics['clients'].append({
                                'client_id': i,
                                'connected': False,
                                'error': str(e)
                            })
                
                self.metrics_history.append(metrics)
                
                # Keep only last 100 entries
                if len(self.metrics_history) > 100:
                    self.metrics_history.pop(0)
                
                # Log dashboard update
                self._log_dashboard_update(metrics)
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    def _log_dashboard_update(self, metrics: Dict):
        """Log formatted dashboard update."""
        connected_clients = sum(1 for client in metrics['clients'] if client.get('connected', False))
        total_entities = sum(client.get('entities_count', 0) for client in metrics['clients'])
        total_players = sum(client.get('players_count', 0) for client in metrics['clients'])
        
        logger.info(f"📊 Dashboard Update - Connected: {connected_clients}/{len(self.clients)}, "
                   f"Total Entities: {total_entities}, Total Players: {total_players}")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.is_monitoring = False
        logger.info("📊 Monitoring stopped")
    
    def export_metrics(self, filename: str):
        """Export collected metrics to JSON file."""
        try:
            filename = Path(filename).resolve()
            if not str(filename).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {filename}")
            with open(filename, 'w') as f:
                json.dump(self.metrics_history, f, indent=2, default=str)
            logger.info(f"✅ Metrics exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to export metrics: {e}")
            return False


async def docker_deployment_example():
    """
    Demonstrate production deployment patterns for Docker environments.
    """
    print("\n=== Docker Deployment Example ===")
    
    # Configuration for Docker environment
    docker_config = {
        'host': 'rust-server:3000',  # Docker service name
        'database': 'blackholio_production',
        'server_language': 'rust',
        'max_retries': 10,
        'retry_delay': 2.0,
        'failure_threshold': 5,
        'recovery_timeout': 60.0,
        'reconnect_attempts': 20,
        'reconnect_delay': 5.0
    }
    
    print("Docker deployment configuration:")
    for key, value in docker_config.items():
        print(f"  {key}: {value}")
    
    # Simulate production client usage
    async with ProductionGameClient(docker_config) as prod_client:
        # Join game
        success = await prod_client.join_game_with_monitoring("ProductionPlayer")
        
        if success:
            # Simulate production workload
            operations = [
                {'type': 'move', 'x': 1.0, 'y': 0.0},
                {'type': 'wait', 'duration': 0.5},
                {'type': 'move', 'x': 0.0, 'y': 1.0},
                {'type': 'wait', 'duration': 0.5},
                {'type': 'split'},
                {'type': 'wait', 'duration': 2.0}
            ]
            
            result = await prod_client.perform_game_operations(operations)
            print(f"Production operations result: {result}")
        
    print("✅ Docker deployment example completed")


async def performance_optimization_example():
    """
    Demonstrate performance optimization techniques.
    """
    print("\n=== Performance Optimization Example ===")
    
    # Configure connection pooling
    connection_manager = get_connection_manager()
    connection_manager.configure_pool(
        min_connections=2,
        max_connections=10,
        idle_timeout=300.0
    )
    
    print("✅ Connection pooling configured")
    
    # Create optimized client
    client = create_game_client(
        server_language='rust',  # Fastest server
        auto_reconnect=True
    )
    
    # Performance measurement
    profiler = PerformanceProfiler()
    
    try:
        # Measure connection time
        profiler.start_checkpoint("connection")
        await client.connect()
        profiler.end_checkpoint("connection")
        
        # Measure game join time
        profiler.start_checkpoint("join_game")
        await client.join_game("PerformanceTest")
        profiler.end_checkpoint("join_game")
        
        # Measure batch operations
        profiler.start_checkpoint("batch_operations")
        
        # Batch movement operations
        movements = [Vector2(0.1 * i, 0.1 * i) for i in range(50)]
        
        for movement in movements:
            await client.move_player(movement)
        
        profiler.end_checkpoint("batch_operations")
        
        # Get performance report
        report = profiler.get_report()
        
        print("🚀 Performance Report:")
        for operation, time_taken in report.items():
            print(f"  {operation}: {time_taken:.3f}s")
        
        # Calculate operations per second
        ops_per_second = 50 / report.get('batch_operations', 1.0)
        print(f"  Operations per second: {ops_per_second:.1f}")
        
    finally:
        await client.shutdown()
    
    print("✅ Performance optimization example completed")


async def event_driven_architecture_example():
    """
    Demonstrate advanced event-driven architecture patterns.
    """
    print("\n=== Event-Driven Architecture Example ===")
    
    # Get global event manager
    event_manager = get_global_event_manager()
    
    # Event statistics
    event_stats = {
        'player_events': 0,
        'entity_events': 0,
        'connection_events': 0
    }
    
    # Advanced event handlers
    def handle_player_events(event):
        event_stats['player_events'] += 1
        print(f"🎮 Player event: {event.get_event_name()}")
    
    def handle_entity_events(event):
        event_stats['entity_events'] += 1
        print(f"🔵 Entity event: {event.get_event_name()}")
    
    def handle_connection_events(event):
        event_stats['connection_events'] += 1
        print(f"🔗 Connection event: {event.get_event_name()}")
    
    # Subscribe to event categories
    event_manager.subscribe("PlayerJoined", handle_player_events)
    event_manager.subscribe("PlayerLeft", handle_player_events)
    event_manager.subscribe("EntityCreated", handle_entity_events)
    event_manager.subscribe("EntityUpdated", handle_entity_events)
    event_manager.subscribe("ConnectionEstablished", handle_connection_events)
    event_manager.subscribe("ConnectionLost", handle_connection_events)
    
    # Create client with event monitoring
    client = create_game_client()
    
    try:
        # Connect and generate events
        await client.connect()
        await client.join_game("EventTestPlayer")
        
        # Perform operations to generate events
        for i in range(5):
            await client.move_player(Vector2(0.1 * i, 0.1 * i))
            await asyncio.sleep(0.2)
        
        await client.player_split()
        await asyncio.sleep(1.0)
        
        # Report event statistics
        print(f"\n📊 Event Statistics:")
        for event_type, count in event_stats.items():
            print(f"  {event_type}: {count} events")
        
    finally:
        await client.shutdown()
    
    print("✅ Event-driven architecture example completed")


async def run_all_advanced_examples():
    """Run all advanced usage examples."""
    print("🚀 Running all advanced usage examples...")
    
    # Docker deployment example
    await docker_deployment_example()
    
    print("\n" + "="*50)
    
    # Performance optimization example
    await performance_optimization_example()
    
    print("\n" + "="*50)
    
    # Event-driven architecture example
    await event_driven_architecture_example()
    
    print("\n" + "="*50)
    
    # Concurrent client management example
    print("\n=== Concurrent Client Management Example ===")
    
    manager = ConcurrentGameManager(num_clients=3)
    
    try:
        # Start concurrent clients
        successful_clients = await manager.start_concurrent_clients()
        
        if successful_clients > 0:
            # Run short load test
            load_results = await manager.run_load_test(
                duration_seconds=10,
                operations_per_second=5
            )
            
            print(f"Load test completed: {load_results}")
        
    finally:
        await manager.shutdown_all_clients()
    
    print("\n✅ All advanced usage examples completed!")


if __name__ == "__main__":
    # Run examples when script is executed directly
    asyncio.run(run_all_advanced_examples())