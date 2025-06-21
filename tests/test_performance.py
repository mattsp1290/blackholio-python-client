"""
Performance Testing Suite - Comprehensive Benchmarks and Performance Validation

Tests performance characteristics of the blackholio-python-client package to ensure
it performs as well as or better than the original implementations in blackholio-agent
and client-pygame.
"""

import asyncio
import gc
import pytest
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import MagicMock, patch

import psutil
from memory_profiler import profile

from blackholio_client.client import GameClient, create_game_client
from blackholio_client.config.environment import EnvironmentConfig, get_environment_config
from blackholio_client.connection.connection_manager import ConnectionManager, get_connection_manager
from blackholio_client.factory.client_factory import create_client
from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle
from blackholio_client.models.serialization import JSONSerializer, BinarySerializer
from blackholio_client.models.data_converters import EntityConverter, PlayerConverter, CircleConverter
from blackholio_client.models.data_pipeline import DataPipeline, PipelineConfiguration
from blackholio_client.events import get_global_event_manager
from blackholio_client.utils.debugging import PerformanceProfiler
from blackholio_client.exceptions.connection_errors import BlackholioConnectionError


@dataclass
class PerformanceBenchmark:
    """Performance benchmark result."""
    test_name: str
    operation_count: int
    total_time: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_percent: float
    min_time: float
    max_time: float
    avg_time: float
    percentile_95: float
    percentile_99: float
    success_rate: float
    additional_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'test_name': self.test_name,
            'operation_count': self.operation_count,
            'total_time': self.total_time,
            'operations_per_second': self.operations_per_second,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_percent': self.cpu_percent,
            'min_time': self.min_time,
            'max_time': self.max_time,
            'avg_time': self.avg_time,
            'percentile_95': self.percentile_95,
            'percentile_99': self.percentile_99,
            'success_rate': self.success_rate,
            'additional_metrics': self.additional_metrics
        }


class PerformanceTester:
    """
    Comprehensive performance testing framework.
    
    Provides benchmarking capabilities for testing various aspects of the
    blackholio-python-client package performance.
    """
    
    def __init__(self):
        """Initialize performance tester."""
        self.process = psutil.Process()
        self.benchmarks: List[PerformanceBenchmark] = []
        
    def measure_operation(self, 
                         operation: Callable,
                         iterations: int = 1000,
                         warmup_iterations: int = 100,
                         operation_name: str = "operation") -> PerformanceBenchmark:
        """
        Measure performance of an operation.
        
        Args:
            operation: Function to measure
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            operation_name: Name of the operation for reporting
            
        Returns:
            Performance benchmark results
        """
        # Warmup
        for _ in range(warmup_iterations):
            try:
                operation()
            except Exception:
                pass  # Ignore warmup errors
        
        # Collect garbage before measurement
        gc.collect()
        
        # Record initial state
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        initial_time = time.perf_counter()
        
        # Run benchmark
        execution_times = []
        success_count = 0
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                operation()
                success_count += 1
            except Exception:
                pass  # Count failures but continue
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        
        # Calculate final metrics
        total_time = time.perf_counter() - initial_time
        final_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        # Calculate statistics
        execution_times.sort()
        min_time = min(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate percentiles
        if execution_times:
            p95_idx = int(0.95 * len(execution_times))
            p99_idx = int(0.99 * len(execution_times))
            percentile_95 = execution_times[p95_idx]
            percentile_99 = execution_times[p99_idx]
        else:
            percentile_95 = percentile_99 = 0
        
        # Create benchmark result
        benchmark = PerformanceBenchmark(
            test_name=operation_name,
            operation_count=iterations,
            total_time=total_time,
            operations_per_second=success_count / total_time if total_time > 0 else 0,
            memory_usage_mb=final_memory - initial_memory,
            cpu_percent=cpu_percent,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            success_rate=success_count / iterations if iterations > 0 else 0,
            additional_metrics={}
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def measure_async_operation(self,
                                    async_operation: Callable,
                                    iterations: int = 1000,
                                    warmup_iterations: int = 100,
                                    operation_name: str = "async_operation") -> PerformanceBenchmark:
        """
        Measure performance of an async operation.
        
        Args:
            async_operation: Async function to measure  
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            operation_name: Name of the operation for reporting
            
        Returns:
            Performance benchmark results
        """
        # Warmup
        for _ in range(warmup_iterations):
            try:
                await async_operation()
            except Exception:
                pass  # Ignore warmup errors
        
        # Collect garbage before measurement
        gc.collect()
        
        # Record initial state
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        initial_time = time.perf_counter()
        
        # Run benchmark
        execution_times = []
        success_count = 0
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                await async_operation()
                success_count += 1
            except Exception:
                pass  # Count failures but continue
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        
        # Calculate final metrics
        total_time = time.perf_counter() - initial_time
        final_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        # Calculate statistics
        execution_times.sort()
        min_time = min(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate percentiles
        if execution_times:
            p95_idx = int(0.95 * len(execution_times))
            p99_idx = int(0.99 * len(execution_times))
            percentile_95 = execution_times[p95_idx]
            percentile_99 = execution_times[p99_idx]
        else:
            percentile_95 = percentile_99 = 0
        
        # Create benchmark result
        benchmark = PerformanceBenchmark(
            test_name=operation_name,
            operation_count=iterations,
            total_time=total_time,
            operations_per_second=success_count / total_time if total_time > 0 else 0,
            memory_usage_mb=final_memory - initial_memory,
            cpu_percent=cpu_percent,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            success_rate=success_count / iterations if iterations > 0 else 0,
            additional_metrics={}
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    def measure_concurrent_operations(self,
                                    operation: Callable,
                                    concurrent_workers: int = 10,
                                    operations_per_worker: int = 100,
                                    operation_name: str = "concurrent_operation") -> PerformanceBenchmark:
        """
        Measure performance under concurrent load.
        
        Args:
            operation: Function to measure
            concurrent_workers: Number of concurrent workers
            operations_per_worker: Operations per worker
            operation_name: Name of the operation for reporting
            
        Returns:
            Performance benchmark results
        """
        total_operations = concurrent_workers * operations_per_worker
        
        # Collect garbage before measurement
        gc.collect()
        
        # Record initial state
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        initial_time = time.perf_counter()
        
        # Run concurrent benchmark
        execution_times = []
        success_count = 0
        
        def worker_function():
            worker_times = []
            worker_successes = 0
            
            for _ in range(operations_per_worker):
                start_time = time.perf_counter()
                try:
                    operation()
                    worker_successes += 1
                except Exception:
                    pass  # Count failures but continue
                end_time = time.perf_counter()
                worker_times.append(end_time - start_time)
            
            return worker_times, worker_successes
        
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(worker_function) for _ in range(concurrent_workers)]
            
            for future in as_completed(futures):
                try:
                    times, successes = future.result()
                    execution_times.extend(times)
                    success_count += successes
                except Exception:
                    pass  # Handle worker failures
        
        # Calculate final metrics
        total_time = time.perf_counter() - initial_time
        final_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        # Calculate statistics
        execution_times.sort()
        min_time = min(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate percentiles
        if execution_times:
            p95_idx = int(0.95 * len(execution_times))
            p99_idx = int(0.99 * len(execution_times))
            percentile_95 = execution_times[p95_idx]
            percentile_99 = execution_times[p99_idx]
        else:
            percentile_95 = percentile_99 = 0
        
        # Create benchmark result
        benchmark = PerformanceBenchmark(
            test_name=operation_name,
            operation_count=total_operations,
            total_time=total_time,
            operations_per_second=success_count / total_time if total_time > 0 else 0,
            memory_usage_mb=final_memory - initial_memory,
            cpu_percent=cpu_percent,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            success_rate=success_count / total_operations if total_operations > 0 else 0,
            additional_metrics={
                'concurrent_workers': concurrent_workers,
                'operations_per_worker': operations_per_worker
            }
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    def get_benchmarks(self) -> List[PerformanceBenchmark]:
        """Get all benchmark results."""
        return self.benchmarks.copy()
    
    def save_benchmarks(self, file_path: str) -> None:
        """Save benchmark results to file."""
        data = [benchmark.to_dict() for benchmark in self.benchmarks]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)


# Global performance tester instance
performance_tester = PerformanceTester()


class TestDataModelPerformance:
    """Test performance of data models and serialization."""
    
    def test_vector2_operations_performance(self):
        """Test Vector2 mathematical operations performance."""
        def vector_operations():
            v1 = Vector2(1.0, 2.0)
            v2 = Vector2(3.0, 4.0)
            # Test common operations
            result = v1 + v2
            result = v1 - v2
            result = v1 * 2.0
            result = v1.dot(v2)
            result = v1.distance_to(v2)
            result = v1.normalize()
            return result
        
        benchmark = performance_tester.measure_operation(
            vector_operations, 
            iterations=10000,
            operation_name="vector2_operations"
        )
        
        # Performance targets: > 10,000 ops/sec
        assert benchmark.operations_per_second > 10000, \
            f"Vector2 operations too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.99, \
            f"Vector2 operations failure rate too high: {1 - benchmark.success_rate}"
    
    def test_game_entity_creation_performance(self):
        """Test GameEntity creation and manipulation performance."""
        def entity_operations():
            entity = GameEntity(
                entity_id="test_123",
                position=Vector2(10.0, 20.0),
                velocity=Vector2(1.0, 0.0),
                radius=5.0,
                entity_type="player"
            )
            # Test common operations
            entity.position = Vector2(11.0, 21.0)  
            entity.velocity = Vector2(2.0, 1.0)
            diameter = entity.diameter
            distance = entity.distance_to(entity)
            area = entity.area
            return entity
        
        benchmark = performance_tester.measure_operation(
            entity_operations,
            iterations=5000,
            operation_name="game_entity_operations"
        )
        
        # Performance targets: > 5,000 ops/sec
        assert benchmark.operations_per_second > 5000, \
            f"GameEntity operations too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.99, \
            f"GameEntity operations failure rate too high: {1 - benchmark.success_rate}"
    
    def test_serialization_performance(self):
        """Test data serialization performance."""
        # Create test data
        entities = [
            GameEntity(
                entity_id=f"entity_{i}",
                position=Vector2(float(i), float(i * 2)),
                velocity=Vector2(1.0, 0.0),
                radius=5.0,
                entity_type="player" if i % 2 == 0 else "circle"
            )
            for i in range(100)
        ]
        
        def json_serialization():
            serializer = JSONSerializer()
            return serializer.serialize(entities[0])
        
        def binary_serialization():
            serializer = BinarySerializer()
            return serializer.serialize(entities[0])
        
        # Test JSON serialization
        json_benchmark = performance_tester.measure_operation(
            json_serialization,
            iterations=1000,
            operation_name="json_serialization"
        )
        
        # Test binary serialization
        binary_benchmark = performance_tester.measure_operation(
            binary_serialization,
            iterations=1000,
            operation_name="binary_serialization"
        )
        
        # Performance targets: > 1,000 ops/sec for serialization
        assert json_benchmark.operations_per_second > 1000, \
            f"JSON serialization too slow: {json_benchmark.operations_per_second} ops/sec"
        assert binary_benchmark.operations_per_second > 1000, \
            f"Binary serialization too slow: {binary_benchmark.operations_per_second} ops/sec"
    
    def test_data_conversion_performance(self):
        """Test data converter performance."""
        # Create test data
        test_data = {
            "entity_id": "test_123",
            "position": {"x": 10.0, "y": 20.0},
            "velocity": {"x": 1.0, "y": 0.0},
            "radius": 5.0,
            "entity_type": "player"
        }
        
        def entity_conversion():
            converter = EntityConverter()
            return converter.from_dict(test_data)
        
        benchmark = performance_tester.measure_operation(
            entity_conversion,
            iterations=2000,
            operation_name="entity_conversion"
        )
        
        # Performance targets: > 2,000 ops/sec
        assert benchmark.operations_per_second > 2000, \
            f"Entity conversion too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.99, \
            f"Entity conversion failure rate too high: {1 - benchmark.success_rate}"


class TestConnectionPerformance:
    """Test connection management performance."""
    
    @patch('blackholio_client.factory.client_factory.create_client')
    def test_connection_manager_performance(self, mock_create_client):
        """Test connection manager performance."""
        # Mock client creation
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        def connection_operations():
            manager = get_connection_manager()
            # Simulate getting and releasing connections
            conn = manager.get_connection("rust", "localhost:3000", "test_db")
            if conn:
                manager.release_connection(conn)
            return conn
        
        benchmark = performance_tester.measure_operation(
            connection_operations,
            iterations=1000,
            operation_name="connection_manager_operations"
        )
        
        # Performance targets: > 1,000 ops/sec
        assert benchmark.operations_per_second > 1000, \
            f"Connection manager too slow: {benchmark.operations_per_second} ops/sec"
    
    @patch('blackholio_client.factory.client_factory.create_client')
    def test_concurrent_connection_performance(self, mock_create_client):
        """Test connection manager under concurrent load."""
        # Mock client creation
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        def connection_operations():
            manager = get_connection_manager()
            conn = manager.get_connection("rust", "localhost:3000", "test_db")
            time.sleep(0.001)  # Simulate work
            if conn:
                manager.release_connection(conn)
            return conn
        
        benchmark = performance_tester.measure_concurrent_operations(
            connection_operations,
            concurrent_workers=20,
            operations_per_worker=50,
            operation_name="concurrent_connection_operations"
        )
        
        # Performance targets: > 500 ops/sec under concurrent load
        assert benchmark.operations_per_second > 500, \
            f"Concurrent connections too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.95, \
            f"Concurrent connection failure rate too high: {1 - benchmark.success_rate}"


class TestEventSystemPerformance:
    """Test event system performance."""
    
    def test_event_publishing_performance(self):
        """Test event publishing performance."""
        from blackholio_client.events.game_events import PlayerJoinedEvent
        
        def event_publishing():
            manager = get_global_event_manager()
            event = PlayerJoinedEvent(
                player_id="test_player",
                username="test_user",
                position=Vector2(0.0, 0.0),
                timestamp=time.time()
            )
            manager.publish(event)
            return event
        
        benchmark = performance_tester.measure_operation(
            event_publishing,
            iterations=5000,
            operation_name="event_publishing"
        )
        
        # Performance targets: > 5,000 ops/sec
        assert benchmark.operations_per_second > 5000, \
            f"Event publishing too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.99, \
            f"Event publishing failure rate too high: {1 - benchmark.success_rate}"
    
    def test_event_subscription_performance(self):
        """Test event subscription and handling performance."""
        from blackholio_client.events.game_events import PlayerJoinedEvent
        from blackholio_client.events.subscriber import CallbackEventSubscriber
        
        event_count = 0
        
        def event_handler(event):
            nonlocal event_count
            event_count += 1
        
        def event_subscription():
            manager = get_global_event_manager()
            subscriber = CallbackEventSubscriber(event_handler)
            manager.subscribe(PlayerJoinedEvent, subscriber)
            
            event = PlayerJoinedEvent(
                player_id="test_player",
                username="test_user", 
                position=Vector2(0.0, 0.0),
                timestamp=time.time()
            )
            manager.publish(event)
            return event
        
        benchmark = performance_tester.measure_operation(
            event_subscription,
            iterations=2000,
            operation_name="event_subscription_handling"
        )
        
        # Performance targets: > 2,000 ops/sec
        assert benchmark.operations_per_second > 2000, \
            f"Event subscription too slow: {benchmark.operations_per_second} ops/sec"
        assert event_count > 0, "Events not being handled"


class TestDataPipelinePerformance:
    """Test data pipeline performance."""
    
    def test_data_pipeline_performance(self):
        """Test complete data pipeline performance."""
        # Create test data
        test_entities = [
            {
                "entity_id": f"entity_{i}",
                "position": {"x": float(i), "y": float(i * 2)},
                "velocity": {"x": 1.0, "y": 0.0},
                "radius": 5.0,
                "entity_type": "player"
            }
            for i in range(10)
        ]
        
        def pipeline_operations():
            config = PipelineConfiguration(
                server_language="rust",
                serialization_format="json",
                validation_enabled=True,
                protocol_adaptation_enabled=True
            )
            pipeline = DataPipeline(config)
            
            # Process data through complete pipeline
            for entity_data in test_entities:
                processed = pipeline.process_for_server(entity_data, "GameEntity")
                pipeline.process_from_server(processed, "GameEntity")
            
            return len(test_entities)
        
        benchmark = performance_tester.measure_operation(
            pipeline_operations,
            iterations=100,
            operation_name="data_pipeline_processing"
        )
        
        # Performance targets: > 100 ops/sec (each op processes 10 entities)
        assert benchmark.operations_per_second > 100, \
            f"Data pipeline too slow: {benchmark.operations_per_second} ops/sec"
        assert benchmark.success_rate > 0.99, \
            f"Data pipeline failure rate too high: {1 - benchmark.success_rate}"


class TestMemoryUsage:
    """Test memory usage and memory leaks."""
    
    def test_memory_usage_stability(self):
        """Test that operations don't cause memory leaks."""
        import gc
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Perform many operations that could cause memory leaks
        for _ in range(1000):
            # Create and destroy objects
            entities = [
                GameEntity(
                    entity_id=f"entity_{i}",
                    position=Vector2(float(i), float(i)),
                    velocity=Vector2(1.0, 0.0),
                    radius=5.0,
                    entity_type="player"
                )
                for i in range(100)
            ]
            
            # Process with serializers
            serializer = JSONSerializer()
            for entity in entities[:10]:  # Sample to avoid too much processing
                data = serializer.serialize(entity)
                serializer.deserialize(data, "GameEntity")
            
            # Clear references
            del entities
            
            # Force garbage collection every 100 iterations
            if _ % 100 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for this test)
        assert memory_increase < 50, \
            f"Excessive memory usage: {memory_increase}MB increase"
    
    @profile
    def test_memory_profiling(self):
        """Test memory usage with detailed profiling."""
        # Create large dataset
        entities = [
            GameEntity(
                entity_id=f"entity_{i}",
                position=Vector2(float(i), float(i)),
                velocity=Vector2(1.0, 0.0),
                radius=5.0,
                entity_type="player"
            )
            for i in range(1000)
        ]
        
        # Process data
        serializer = JSONSerializer()
        for entity in entities:
            data = serializer.serialize(entity)
            # Don't deserialize to save memory in test
        
        return len(entities)


@pytest.fixture(scope="session", autouse=True)
def save_performance_results():
    """Save performance test results after all tests complete."""
    yield
    
    # Save benchmark results
    import os
    results_dir = os.path.join(os.path.dirname(__file__), "performance_results")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"performance_benchmarks_{timestamp}.json")
    
    performance_tester.save_benchmarks(results_file)
    
    # Print summary
    benchmarks = performance_tester.get_benchmarks()
    if benchmarks:
        print(f"\n{'='*80}")
        print(f"PERFORMANCE TEST SUMMARY ({len(benchmarks)} tests)")
        print(f"{'='*80}")
        print(f"{'Test Name':<40} {'Ops/Sec':<12} {'Avg Time':<12} {'Success Rate':<12}")
        print(f"{'-'*80}")
        
        for benchmark in benchmarks:
            print(f"{benchmark.test_name:<40} "
                  f"{benchmark.operations_per_second:<12.1f} "
                  f"{benchmark.avg_time*1000:<12.3f}ms "
                  f"{benchmark.success_rate*100:<12.1f}%")
        
        print(f"{'-'*80}")
        print(f"Results saved to: {results_file}")
        print(f"{'='*80}")


# Performance target constants
PERFORMANCE_TARGETS = {
    'vector2_operations': 10000,  # ops/sec
    'game_entity_operations': 5000,  # ops/sec
    'json_serialization': 1000,  # ops/sec
    'binary_serialization': 1000,  # ops/sec
    'entity_conversion': 2000,  # ops/sec
    'connection_manager_operations': 1000,  # ops/sec
    'concurrent_connection_operations': 500,  # ops/sec
    'event_publishing': 5000,  # ops/sec
    'event_subscription_handling': 2000,  # ops/sec
    'data_pipeline_processing': 100,  # ops/sec
}


def validate_performance_targets():
    """Validate that all performance targets are met."""
    benchmarks = performance_tester.get_benchmarks()
    failed_tests = []
    
    for benchmark in benchmarks:
        target = PERFORMANCE_TARGETS.get(benchmark.test_name)
        if target and benchmark.operations_per_second < target:
            failed_tests.append({
                'test': benchmark.test_name,
                'actual': benchmark.operations_per_second,
                'target': target,
                'ratio': benchmark.operations_per_second / target
            })
    
    if failed_tests:
        print("\nPERFORMANCE TARGET FAILURES:")
        for failure in failed_tests:
            print(f"  {failure['test']}: {failure['actual']:.1f} ops/sec "
                  f"(target: {failure['target']} ops/sec, "
                  f"ratio: {failure['ratio']:.2f})")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "--tb=short"])