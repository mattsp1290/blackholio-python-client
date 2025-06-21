#!/usr/bin/env python3
"""
Comprehensive load and stress testing for blackholio-python-client.

This module performs extensive load testing to validate the package's behavior under:
- High concurrent connection loads
- Sustained high-throughput operations
- Memory pressure scenarios
- Network failure conditions
- Resource exhaustion scenarios
"""

import asyncio
import concurrent.futures
import json
import multiprocessing
import os
import psutil
import random
import resource
import signal
import statistics
import sys
import threading
import time
import tracemalloc
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pytest

# Add the src directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from blackholio_client import (
    GameClient,
    Vector2,
    GameEntity,
    GamePlayer,
    create_game_client,
    EnvironmentConfig
)
from blackholio_client.exceptions import BlackholioConnectionError, BlackholioTimeoutError
from blackholio_client.utils.performance import PerformanceProfiler


@dataclass
class LoadTestMetrics:
    """Comprehensive metrics collection for load testing."""
    
    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    
    # Connection metrics
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    connection_times: List[float] = field(default_factory=list)
    
    # Operation latencies (in milliseconds)
    operation_latencies: List[float] = field(default_factory=list)
    operation_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    peak_thread_count: int = 0
    peak_fd_count: int = 0
    
    # Error tracking
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_samples: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    # Throughput metrics (operations per second)
    throughput_samples: List[float] = field(default_factory=list)
    
    def record_operation(self, operation_type: str, latency_ms: float, success: bool = True):
        """Record a single operation."""
        self.total_operations += 1
        self.operation_types[operation_type] += 1
        self.operation_latencies.append(latency_ms)
        
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
    
    def record_error(self, error_type: str, error_msg: str):
        """Record an error occurrence."""
        self.error_counts[error_type] += 1
        if len(self.error_samples[error_type]) < 10:  # Keep first 10 samples
            self.error_samples[error_type].append(error_msg)
    
    def record_connection(self, connection_time_ms: float, success: bool = True):
        """Record a connection attempt."""
        self.total_connections += 1
        if success:
            self.active_connections += 1
            self.connection_times.append(connection_time_ms)
        else:
            self.failed_connections += 1
    
    def update_resource_metrics(self):
        """Update resource usage metrics."""
        process = psutil.Process()
        
        # Memory usage
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        
        # CPU usage
        cpu_percent = process.cpu_percent(interval=0.1)
        self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_percent)
        
        # Thread count
        thread_count = process.num_threads()
        self.peak_thread_count = max(self.peak_thread_count, thread_count)
        
        # File descriptor count (Unix only)
        try:
            fd_count = process.num_fds()
            self.peak_fd_count = max(self.peak_fd_count, fd_count)
        except AttributeError:
            pass  # Windows doesn't have num_fds
    
    def calculate_throughput(self):
        """Calculate current throughput."""
        if not self.start_time or not self.total_operations:
            return 0.0
        
        elapsed_seconds = time.time() - self.start_time
        if elapsed_seconds > 0:
            return self.total_operations / elapsed_seconds
        return 0.0
    
    def get_percentiles(self, data: List[float], percentiles: List[int] = None) -> Dict[str, float]:
        """Calculate percentiles for a dataset."""
        if not data:
            return {}
        
        if percentiles is None:
            percentiles = [50, 90, 95, 99]
        
        sorted_data = sorted(data)
        result = {}
        
        for p in percentiles:
            index = int(len(sorted_data) * p / 100)
            if index >= len(sorted_data):
                index = len(sorted_data) - 1
            result[f"p{p}"] = sorted_data[index]
        
        result["min"] = sorted_data[0]
        result["max"] = sorted_data[-1]
        result["mean"] = statistics.mean(sorted_data)
        
        if len(sorted_data) > 1:
            result["stddev"] = statistics.stdev(sorted_data)
        
        return result
    
    def finalize(self):
        """Finalize metrics collection."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        self.finalize()
        
        duration = (self.end_time or time.time()) - self.start_time
        
        return {
            "duration_seconds": duration,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / max(1, self.total_operations),
            "throughput_ops_per_sec": self.calculate_throughput(),
            
            "connections": {
                "total": self.total_connections,
                "active": self.active_connections,
                "failed": self.failed_connections,
                "connection_time_percentiles": self.get_percentiles(self.connection_times),
            },
            
            "latencies": self.get_percentiles(self.operation_latencies),
            "operation_counts": dict(self.operation_types),
            
            "resources": {
                "peak_memory_mb": self.peak_memory_mb,
                "peak_cpu_percent": self.peak_cpu_percent,
                "peak_thread_count": self.peak_thread_count,
                "peak_fd_count": self.peak_fd_count,
            },
            
            "errors": {
                "total_errors": sum(self.error_counts.values()),
                "error_types": dict(self.error_counts),
                "error_samples": dict(self.error_samples),
            }
        }


class LoadTestRunner:
    """Orchestrates load testing scenarios."""
    
    def __init__(self, server_language: str = "rust", max_workers: int = None):
        self.server_language = server_language
        self.max_workers = max_workers or multiprocessing.cpu_count() * 2
        self.metrics = LoadTestMetrics()
        self._stop_event = threading.Event()
        self._resource_monitor_thread = None
    
    def start_resource_monitoring(self, interval: float = 1.0):
        """Start background resource monitoring."""
        def monitor():
            while not self._stop_event.is_set():
                self.metrics.update_resource_metrics()
                time.sleep(interval)
        
        self._resource_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._resource_monitor_thread.start()
    
    def stop_resource_monitoring(self):
        """Stop resource monitoring."""
        self._stop_event.set()
        if self._resource_monitor_thread:
            self._resource_monitor_thread.join(timeout=5)
    
    @contextmanager
    def resource_monitoring(self):
        """Context manager for resource monitoring."""
        self.start_resource_monitoring()
        try:
            yield
        finally:
            self.stop_resource_monitoring()
    
    async def create_client_with_metrics(self) -> Optional[GameClient]:
        """Create a client and record metrics."""
        start_time = time.time()
        
        try:
            client = create_game_client(server_language=self.server_language)
            await client.connect()
            
            connection_time_ms = (time.time() - start_time) * 1000
            self.metrics.record_connection(connection_time_ms, success=True)
            
            return client
            
        except Exception as e:
            connection_time_ms = (time.time() - start_time) * 1000
            self.metrics.record_connection(connection_time_ms, success=False)
            self.metrics.record_error(type(e).__name__, str(e))
            return None
    
    async def perform_operation(self, client: GameClient, operation_type: str):
        """Perform a single operation and record metrics."""
        start_time = time.time()
        success = False
        
        try:
            if operation_type == "auth":
                await client.authenticate()
                success = True
                
            elif operation_type == "enter_game":
                await client.enter_game(f"Player{random.randint(1000, 9999)}")
                success = True
                
            elif operation_type == "move":
                direction = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalized()
                await client.move_player(direction)
                success = True
                
            elif operation_type == "get_entities":
                entities = await client.get_game_entities()
                success = True
                
            elif operation_type == "get_players":
                players = await client.get_players()
                success = True
                
            elif operation_type == "split":
                await client.player_split()
                success = True
                
        except Exception as e:
            self.metrics.record_error(type(e).__name__, str(e))
        
        finally:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_operation(operation_type, latency_ms, success)
    
    async def concurrent_operations_test(self, num_clients: int, operations_per_client: int):
        """Test concurrent operations from multiple clients."""
        print(f"\n🔥 Running concurrent operations test with {num_clients} clients...")
        
        # Create clients concurrently
        client_tasks = [self.create_client_with_metrics() for _ in range(num_clients)]
        clients = await asyncio.gather(*client_tasks)
        clients = [c for c in clients if c is not None]
        
        if not clients:
            print("❌ Failed to create any clients")
            return
        
        print(f"✅ Successfully created {len(clients)} clients")
        
        # Define operation mix
        operations = [
            ("move", 0.4),      # 40% move operations
            ("get_entities", 0.3),  # 30% get entities
            ("get_players", 0.2),   # 20% get players
            ("enter_game", 0.05),   # 5% enter game
            ("split", 0.05),        # 5% split operations
        ]
        
        # Perform operations concurrently
        operation_tasks = []
        for client in clients:
            for _ in range(operations_per_client):
                # Select operation based on weights
                rand = random.random()
                cumulative = 0
                for op_type, weight in operations:
                    cumulative += weight
                    if rand <= cumulative:
                        operation_tasks.append(self.perform_operation(client, op_type))
                        break
        
        # Execute all operations
        await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Cleanup clients
        cleanup_tasks = [client.disconnect() for client in clients if client]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.metrics.active_connections = 0
    
    async def sustained_load_test(self, target_ops_per_sec: int, duration_seconds: int):
        """Test sustained load at a target operations per second."""
        print(f"\n🔥 Running sustained load test: {target_ops_per_sec} ops/sec for {duration_seconds}s...")
        
        # Create a pool of clients
        num_clients = min(target_ops_per_sec // 10, self.max_workers)  # Estimate clients needed
        num_clients = max(1, num_clients)
        
        client_tasks = [self.create_client_with_metrics() for _ in range(num_clients)]
        clients = await asyncio.gather(*client_tasks)
        clients = [c for c in clients if c is not None]
        
        if not clients:
            print("❌ Failed to create any clients")
            return
        
        print(f"✅ Created {len(clients)} clients for sustained load")
        
        # Calculate operations per client per second
        ops_per_client_per_sec = target_ops_per_sec / len(clients)
        interval_between_ops = 1.0 / ops_per_client_per_sec
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        async def client_worker(client: GameClient):
            """Worker that performs operations at a steady rate."""
            operations = ["move", "get_entities", "get_players"]
            
            while time.time() < end_time:
                op_type = random.choice(operations)
                await self.perform_operation(client, op_type)
                
                # Sleep to maintain target rate
                await asyncio.sleep(interval_between_ops)
        
        # Run workers concurrently
        worker_tasks = [client_worker(client) for client in clients]
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        # Cleanup
        cleanup_tasks = [client.disconnect() for client in clients if client]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def connection_pool_stress_test(self, max_connections: int, churn_rate: float):
        """Test connection pool behavior under stress with connection churn."""
        print(f"\n🔥 Running connection pool stress test: {max_connections} max connections, {churn_rate} churn rate...")
        
        active_clients = []
        
        async def connection_churn():
            """Simulate connection churn."""
            for _ in range(int(max_connections * 2)):  # Test 2x the max connections
                # Create new connection
                client = await self.create_client_with_metrics()
                if client:
                    active_clients.append(client)
                
                # Maybe close an existing connection
                if active_clients and random.random() < churn_rate:
                    client_to_close = random.choice(active_clients)
                    active_clients.remove(client_to_close)
                    await client_to_close.disconnect()
                    self.metrics.active_connections -= 1
                
                # Perform some operations on active clients
                if active_clients:
                    sample_size = min(5, len(active_clients))
                    sample_clients = random.sample(active_clients, sample_size)
                    
                    op_tasks = []
                    for client in sample_clients:
                        op_type = random.choice(["move", "get_entities", "get_players"])
                        op_tasks.append(self.perform_operation(client, op_type))
                    
                    await asyncio.gather(*op_tasks, return_exceptions=True)
                
                await asyncio.sleep(0.1)  # Small delay between iterations
        
        await connection_churn()
        
        # Cleanup remaining connections
        cleanup_tasks = [client.disconnect() for client in active_clients]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def memory_pressure_test(self, num_entities: int, duration_seconds: int):
        """Test behavior under memory pressure with large numbers of entities."""
        print(f"\n🔥 Running memory pressure test: {num_entities} entities for {duration_seconds}s...")
        
        # Enable memory tracing
        tracemalloc.start()
        
        # Create clients
        num_clients = min(10, self.max_workers)
        client_tasks = [self.create_client_with_metrics() for _ in range(num_clients)]
        clients = await asyncio.gather(*client_tasks)
        clients = [c for c in clients if c is not None]
        
        if not clients:
            print("❌ Failed to create any clients")
            return
        
        # Create large numbers of entities in memory
        entities = []
        for i in range(num_entities):
            entity = GameEntity(
                id=f"entity_{i}",
                owner_id=f"player_{i % 100}",
                position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
                mass=random.uniform(10, 100),
                entity_type=random.choice(["circle", "food", "obstacle"])
            )
            entities.append(entity)
        
        # Perform operations while holding entities in memory
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Simulate processing entities
            for client in clients:
                # Random operations that might involve entities
                if random.random() < 0.3:
                    await self.perform_operation(client, "get_entities")
                else:
                    await self.perform_operation(client, "move")
            
            # Update resource metrics
            self.metrics.update_resource_metrics()
            
            # Get memory snapshot
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # Record memory usage
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, peak_memory / 1024 / 1024)
            
            await asyncio.sleep(0.5)
        
        # Cleanup
        tracemalloc.stop()
        cleanup_tasks = [client.disconnect() for client in clients if client]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def error_recovery_test(self, num_operations: int, error_rate: float):
        """Test error handling and recovery under various failure scenarios."""
        print(f"\n🔥 Running error recovery test: {num_operations} operations with {error_rate} error rate...")
        
        # Create clients with potential for failure
        num_clients = min(20, self.max_workers)
        clients = []
        
        for _ in range(num_clients):
            client = await self.create_client_with_metrics()
            if client:
                clients.append(client)
        
        if not clients:
            print("❌ Failed to create any clients")
            return
        
        # Perform operations with simulated errors
        for _ in range(num_operations):
            client = random.choice(clients)
            
            # Simulate network errors
            if random.random() < error_rate:
                # Force a connection error by manipulating the client
                try:
                    # This will fail and test error recovery
                    client._connection = None
                except:
                    pass
            
            # Try various operations
            op_type = random.choice(["move", "get_entities", "get_players", "enter_game"])
            await self.perform_operation(client, op_type)
            
            # Maybe try to recover the connection
            if random.random() < 0.1:  # 10% chance to attempt recovery
                try:
                    await client.connect()
                except:
                    pass
        
        # Cleanup
        cleanup_tasks = []
        for client in clients:
            try:
                await client.disconnect()
            except:
                pass
    
    def run_load_tests(self):
        """Run comprehensive load test suite."""
        print("\n" + "="*80)
        print("🚀 BLACKHOLIO PYTHON CLIENT - COMPREHENSIVE LOAD TESTING")
        print("="*80)
        print(f"Server Language: {self.server_language}")
        print(f"Max Workers: {self.max_workers}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        with self.resource_monitoring():
            # Run async tests
            asyncio.run(self._run_async_tests())
        
        # Print results
        self._print_results()
    
    async def _run_async_tests(self):
        """Run all async load tests."""
        # Test 1: Concurrent operations
        await self.concurrent_operations_test(
            num_clients=50,
            operations_per_client=100
        )
        
        # Test 2: Sustained load
        await self.sustained_load_test(
            target_ops_per_sec=1000,
            duration_seconds=30
        )
        
        # Test 3: Connection pool stress
        await self.connection_pool_stress_test(
            max_connections=100,
            churn_rate=0.3
        )
        
        # Test 4: Memory pressure
        await self.memory_pressure_test(
            num_entities=10000,
            duration_seconds=20
        )
        
        # Test 5: Error recovery
        await self.error_recovery_test(
            num_operations=1000,
            error_rate=0.1
        )
    
    def _print_results(self):
        """Print comprehensive test results."""
        summary = self.metrics.get_summary()
        
        print("\n" + "="*80)
        print("📊 LOAD TEST RESULTS SUMMARY")
        print("="*80)
        
        # Overall performance
        print(f"\n⏱️  PERFORMANCE METRICS:")
        print(f"  Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"  Total Operations: {summary['total_operations']:,}")
        print(f"  Successful: {summary['successful_operations']:,} ({summary['success_rate']:.1%})")
        print(f"  Failed: {summary['failed_operations']:,}")
        print(f"  Throughput: {summary['throughput_ops_per_sec']:.1f} ops/sec")
        
        # Connection metrics
        print(f"\n🔌 CONNECTION METRICS:")
        print(f"  Total Connections: {summary['connections']['total']}")
        print(f"  Failed Connections: {summary['connections']['failed']}")
        
        if summary['connections']['connection_time_percentiles']:
            print(f"  Connection Times (ms):")
            for metric, value in summary['connections']['connection_time_percentiles'].items():
                print(f"    {metric}: {value:.2f}")
        
        # Latency metrics
        print(f"\n⚡ LATENCY METRICS (ms):")
        if summary['latencies']:
            for metric, value in summary['latencies'].items():
                print(f"  {metric}: {value:.2f}")
        
        # Operation breakdown
        print(f"\n📊 OPERATION BREAKDOWN:")
        for op_type, count in summary['operation_counts'].items():
            percentage = (count / max(1, summary['total_operations'])) * 100
            print(f"  {op_type}: {count:,} ({percentage:.1f}%)")
        
        # Resource usage
        print(f"\n💾 RESOURCE USAGE:")
        print(f"  Peak Memory: {summary['resources']['peak_memory_mb']:.1f} MB")
        print(f"  Peak CPU: {summary['resources']['peak_cpu_percent']:.1f}%")
        print(f"  Peak Threads: {summary['resources']['peak_thread_count']}")
        if summary['resources']['peak_fd_count'] > 0:
            print(f"  Peak File Descriptors: {summary['resources']['peak_fd_count']}")
        
        # Error summary
        if summary['errors']['total_errors'] > 0:
            print(f"\n❌ ERROR SUMMARY:")
            print(f"  Total Errors: {summary['errors']['total_errors']}")
            for error_type, count in summary['errors']['error_types'].items():
                print(f"  {error_type}: {count}")
        
        # Performance verdict
        print(f"\n🏆 PERFORMANCE VERDICT:")
        
        # Check success rate
        if summary['success_rate'] >= 0.99:
            print("  ✅ Excellent reliability (99%+ success rate)")
        elif summary['success_rate'] >= 0.95:
            print("  ✅ Good reliability (95%+ success rate)")
        else:
            print("  ⚠️  Reliability needs improvement")
        
        # Check throughput
        if summary['throughput_ops_per_sec'] >= 1000:
            print("  ✅ Excellent throughput (1000+ ops/sec)")
        elif summary['throughput_ops_per_sec'] >= 500:
            print("  ✅ Good throughput (500+ ops/sec)")
        else:
            print("  ⚠️  Throughput could be improved")
        
        # Check latencies
        if summary['latencies'] and summary['latencies'].get('p99', float('inf')) < 100:
            print("  ✅ Excellent latency (p99 < 100ms)")
        elif summary['latencies'] and summary['latencies'].get('p99', float('inf')) < 500:
            print("  ✅ Good latency (p99 < 500ms)")
        else:
            print("  ⚠️  Latency needs optimization")
        
        # Check resource usage
        if summary['resources']['peak_memory_mb'] < 500:
            print("  ✅ Excellent memory efficiency (< 500MB)")
        elif summary['resources']['peak_memory_mb'] < 1000:
            print("  ✅ Good memory efficiency (< 1GB)")
        else:
            print("  ⚠️  High memory usage detected")
        
        print("\n" + "="*80)
        
        # Save detailed results
        self._save_results(summary)
    
    def _save_results(self, summary: Dict[str, Any]):
        """Save detailed results to file."""
        results_dir = Path(__file__).parent / "load_test_results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"load_test_{self.server_language}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {filename}")


def main():
    """Main entry point for load testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test blackholio-python-client")
    parser.add_argument(
        "--server-language",
        choices=["rust", "python", "csharp", "go"],
        default="rust",
        help="Server language to test against"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of concurrent workers"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["SERVER_LANGUAGE"] = args.server_language
    
    # Run load tests
    runner = LoadTestRunner(
        server_language=args.server_language,
        max_workers=args.max_workers
    )
    
    try:
        runner.run_load_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Load test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Load test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()