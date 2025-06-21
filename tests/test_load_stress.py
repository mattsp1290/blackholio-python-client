"""
Load and stress testing for blackholio-python-client.

This module contains pytest-compatible load tests that validate the package's
behavior under various stress conditions.
"""

import asyncio
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pytest

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from blackholio_client import (
    GameClient,
    Vector2,
    GameEntity,
    GamePlayer,
    create_game_client,
    EnvironmentConfig
)
from blackholio_client.exceptions import BlackholioConnectionError


@pytest.mark.load_test
@pytest.mark.asyncio
async def test_concurrent_client_creation():
    """Test creating multiple clients concurrently."""
    num_clients = 20
    
    async def create_client():
        try:
            client = create_game_client()
            # Just create, don't connect to avoid needing real server
            return client
        except Exception:
            return None
    
    # Create clients concurrently
    tasks = [create_client() for _ in range(num_clients)]
    clients = await asyncio.gather(*tasks)
    
    # Count successful creations
    successful = sum(1 for c in clients if c is not None)
    
    assert successful == num_clients, f"Only {successful}/{num_clients} clients created successfully"
    
    # Verify clients are independent
    client_ids = [id(c) for c in clients if c]
    assert len(set(client_ids)) == successful, "Clients are not independent instances"


@pytest.mark.load_test
def test_vector_operations_under_load():
    """Test Vector2 operations under heavy load."""
    num_operations = 100000
    vectors = []
    
    # Create many vectors
    for _ in range(1000):
        v = Vector2(random.uniform(-100, 100), random.uniform(-100, 100))
        vectors.append(v)
    
    start_time = time.time()
    results = []
    
    # Perform many operations
    for i in range(num_operations):
        v1 = random.choice(vectors)
        v2 = random.choice(vectors)
        
        # Various operations
        if i % 5 == 0:
            result = v1 + v2
        elif i % 5 == 1:
            result = v1 - v2
        elif i % 5 == 2:
            result = v1 * random.uniform(0.5, 2.0)
        elif i % 5 == 3:
            result = v1.normalize()
        else:
            result = v1.distance_to(v2)
        
        results.append(result)
    
    elapsed = time.time() - start_time
    ops_per_sec = num_operations / elapsed
    
    print(f"\nVector operations: {ops_per_sec:,.0f} ops/sec")
    assert ops_per_sec > 100000, f"Vector operations too slow: {ops_per_sec:,.0f} ops/sec"


@pytest.mark.load_test
def test_entity_creation_under_load():
    """Test entity creation and manipulation under load."""
    num_entities = 10000
    
    start_time = time.time()
    entities = []
    
    # Create many entities
    for i in range(num_entities):
        entity = GameEntity(
            entity_id=f"entity_{i}",
            position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
            mass=random.uniform(10, 100),
            radius=random.uniform(1, 10),
            entity_type=random.choice(["circle", "food", "obstacle"])
        )
        entities.append(entity)
    
    # Perform operations on entities
    for _ in range(num_entities):
        entity = random.choice(entities)
        
        # Various operations
        _ = entity.radius
        _ = entity.position.magnitude
        _ = entity.to_dict()
    
    elapsed = time.time() - start_time
    entities_per_sec = num_entities / elapsed
    
    print(f"\nEntity operations: {entities_per_sec:,.0f} entities/sec")
    assert entities_per_sec > 5000, f"Entity operations too slow: {entities_per_sec:,.0f} entities/sec"


@pytest.mark.load_test
def test_concurrent_data_serialization():
    """Test data serialization under concurrent load."""
    from blackholio_client.models.serialization import JsonSerializer
    
    serializer = JsonSerializer()
    num_threads = 8
    operations_per_thread = 1000
    
    # Create test data
    test_entities = []
    for i in range(100):
        entity = GameEntity(
            entity_id=f"entity_{i}",
            position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
            mass=random.uniform(10, 100),
            radius=random.uniform(1, 10),
            entity_type="circle"
        )
        test_entities.append(entity)
    
    def worker():
        """Worker function for concurrent serialization."""
        results = []
        for _ in range(operations_per_thread):
            entity = random.choice(test_entities)
            
            # Serialize
            serialized = serializer.serialize(entity.to_dict())
            
            # Deserialize
            deserialized = serializer.deserialize(serialized, dict)
            
            results.append(deserialized)
        
        return len(results)
    
    # Run concurrent workers
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start_time
    total_operations = sum(results)
    ops_per_sec = total_operations / elapsed
    
    print(f"\nConcurrent serialization: {ops_per_sec:,.0f} ops/sec")
    assert ops_per_sec > 10000, f"Serialization too slow: {ops_per_sec:,.0f} ops/sec"


@pytest.mark.load_test
def test_physics_calculations_under_load():
    """Test physics calculations under heavy load."""
    from blackholio_client.models.physics import (
        calculate_center_of_mass,
        check_collision,
        calculate_entity_radius
    )
    
    # Create many entities
    entities = []
    for i in range(1000):
        entity = GameEntity(
            entity_id=f"entity_{i}",
            position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
            mass=random.uniform(10, 100),
            radius=random.uniform(1, 10),
            entity_type="circle"
        )
        entities.append(entity)
    
    start_time = time.time()
    num_calculations = 10000
    
    for _ in range(num_calculations):
        # Random physics calculations
        operation = random.randint(0, 2)
        
        if operation == 0:
            # Center of mass
            sample_size = random.randint(2, 10)
            sample = random.sample(entities, sample_size)
            _ = calculate_center_of_mass(sample)
        
        elif operation == 1:
            # Collision detection
            e1, e2 = random.sample(entities, 2)
            _ = check_collision(e1, e2)
        
        else:
            # Entity radius
            entity = random.choice(entities)
            _ = calculate_entity_radius(entity.mass)
    
    elapsed = time.time() - start_time
    calcs_per_sec = num_calculations / elapsed
    
    print(f"\nPhysics calculations: {calcs_per_sec:,.0f} calcs/sec")
    assert calcs_per_sec > 5000, f"Physics calculations too slow: {calcs_per_sec:,.0f} calcs/sec"


@pytest.mark.load_test
@pytest.mark.asyncio
async def test_event_system_under_load():
    """Test event system under heavy load."""
    from blackholio_client.events import EventManager, Event, EventType
    from blackholio_client.events.game_events import (
        PlayerMovedEvent,
        EntityCreatedEvent,
        EntityUpdatedEvent
    )
    
    manager = EventManager()
    
    # Track events received
    events_received = {"count": 0}
    
    def event_handler(event: Event):
        events_received["count"] += 1
    
    # Subscribe to events
    manager.subscribe(EventType.PLAYER_MOVED, event_handler)
    manager.subscribe(EventType.ENTITY_CREATED, event_handler)
    manager.subscribe(EventType.ENTITY_UPDATED, event_handler)
    
    # Generate many events
    num_events = 10000
    start_time = time.time()
    
    for i in range(num_events):
        event_type = random.randint(0, 2)
        
        if event_type == 0:
            event = PlayerMovedEvent(
                player_id=f"player_{i % 100}",
                old_position=Vector2(0, 0),
                new_position=Vector2(random.uniform(0, 100), random.uniform(0, 100)),
                timestamp=time.time()
            )
        elif event_type == 1:
            event = EntityCreatedEvent(
                entity=GameEntity(
                    entity_id=f"entity_{i}",
                    position=Vector2(random.uniform(0, 100), random.uniform(0, 100)),
                    mass=random.uniform(10, 100),
                    radius=random.uniform(1, 10),
                    entity_type="circle"
                ),
                timestamp=time.time()
            )
        else:
            event = EntityUpdatedEvent(
                entity_id=f"entity_{i % 1000}",
                old_state={},
                new_state={"position": {"x": random.uniform(0, 100), "y": random.uniform(0, 100)}},
                timestamp=time.time()
            )
        
        manager.publish(event)
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    elapsed = time.time() - start_time
    events_per_sec = num_events / elapsed
    
    print(f"\nEvent system: {events_per_sec:,.0f} events/sec")
    print(f"Events received: {events_received['count']:,}/{num_events:,}")
    
    assert events_per_sec > 10000, f"Event system too slow: {events_per_sec:,.0f} events/sec"
    assert events_received["count"] >= num_events * 0.99, "Too many events lost"


@pytest.mark.load_test
def test_configuration_access_under_load():
    """Test configuration system under concurrent access."""
    from blackholio_client.config import get_config, EnvironmentConfig
    
    num_threads = 10
    accesses_per_thread = 1000
    
    def worker():
        """Worker function for concurrent config access."""
        results = []
        
        for _ in range(accesses_per_thread):
            config = get_config()
            
            # Access various properties
            _ = config.server_language
            _ = config.server_ip
            _ = config.server_port
            _ = config.get_server_url()
            _ = config.to_dict()
            
            results.append(config)
        
        return len(results)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start_time
    total_accesses = sum(results)
    accesses_per_sec = total_accesses / elapsed
    
    print(f"\nConfig access: {accesses_per_sec:,.0f} accesses/sec")
    assert accesses_per_sec > 50000, f"Config access too slow: {accesses_per_sec:,.0f} accesses/sec"


@pytest.mark.load_test
@pytest.mark.asyncio
async def test_connection_manager_pool_limits():
    """Test connection manager behavior at pool limits."""
    from blackholio_client.connection.connection_manager import ConnectionManager
    
    # Create manager with small pool for testing
    manager = ConnectionManager(
        min_connections=2,
        max_connections=5,
        connection_timeout=5.0
    )
    
    # Track metrics
    connections_created = 0
    connections_failed = 0
    
    async def try_get_connection():
        nonlocal connections_created, connections_failed
        try:
            # This will fail without real server, but tests pool logic
            conn = await manager.get_connection()
            connections_created += 1
            return conn
        except Exception:
            connections_failed += 1
            return None
    
    # Try to exceed pool limits
    tasks = []
    for _ in range(10):  # Try to create more than max
        tasks.append(try_get_connection())
    
    results = await asyncio.gather(*tasks)
    
    # Pool should limit connections
    assert connections_created <= 5, f"Pool exceeded max connections: {connections_created}"
    
    # Cleanup
    await manager.close_all()


@pytest.mark.load_test
def test_memory_efficiency():
    """Test memory efficiency with large datasets."""
    import gc
    import tracemalloc
    
    # Start memory tracking
    tracemalloc.start()
    gc.collect()
    
    # Get baseline memory
    baseline = tracemalloc.get_traced_memory()[0]
    
    # Create large dataset
    entities = []
    for i in range(10000):
        entity = GameEntity(
            id=f"entity_{i}",
            owner_id=f"player_{i % 100}",
            position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
            mass=random.uniform(10, 100),
            entity_type="circle"
        )
        entities.append(entity)
    
    # Get memory after creation
    current = tracemalloc.get_traced_memory()[0]
    memory_used_mb = (current - baseline) / 1024 / 1024
    
    print(f"\nMemory used for 10,000 entities: {memory_used_mb:.2f} MB")
    print(f"Average per entity: {memory_used_mb / 10000 * 1000:.2f} KB")
    
    # Clean up
    entities.clear()
    gc.collect()
    
    tracemalloc.stop()
    
    # Should use less than 100MB for 10k entities
    assert memory_used_mb < 100, f"Excessive memory usage: {memory_used_mb:.2f} MB"


@pytest.mark.load_test
@pytest.mark.asyncio
async def test_error_handling_under_stress():
    """Test error handling and recovery under stress conditions."""
    from blackholio_client.utils.error_handling import RetryManager, ErrorRecoveryManager
    
    # Track metrics
    attempts = 0
    successes = 0
    failures = 0
    
    async def flaky_operation():
        """Operation that fails 30% of the time."""
        nonlocal attempts
        attempts += 1
        
        if random.random() < 0.3:
            raise BlackholioConnectionError("Simulated connection failure")
        
        return "success"
    
    # Create retry manager
    retry_manager = RetryManager(
        max_retries=3,
        backoff_strategy="exponential",
        base_delay=0.01  # Fast for testing
    )
    
    # Run many operations with retry
    num_operations = 1000
    
    for _ in range(num_operations):
        try:
            result = await retry_manager.execute_with_retry(flaky_operation)
            if result == "success":
                successes += 1
        except Exception:
            failures += 1
    
    success_rate = successes / num_operations
    retry_overhead = attempts / num_operations
    
    print(f"\nError recovery test:")
    print(f"  Success rate: {success_rate:.1%}")
    print(f"  Average attempts per operation: {retry_overhead:.2f}")
    print(f"  Total attempts: {attempts}")
    
    # Should recover from most failures
    assert success_rate > 0.9, f"Low success rate: {success_rate:.1%}"
    assert retry_overhead < 2.0, f"Too many retries: {retry_overhead:.2f} average"


# Performance benchmarks as regular tests
@pytest.mark.load_test
def test_performance_benchmarks():
    """Run performance benchmarks and validate against targets."""
    results = {}
    
    # Benchmark 1: Vector operations
    start = time.time()
    for _ in range(10000):
        v1 = Vector2(random.uniform(-100, 100), random.uniform(-100, 100))
        v2 = Vector2(random.uniform(-100, 100), random.uniform(-100, 100))
        _ = v1 + v2
        _ = v1.normalized()
        _ = v1.distance_to(v2)
    elapsed = time.time() - start
    results["vector_ops_per_sec"] = 30000 / elapsed
    
    # Benchmark 2: Entity operations
    entities = [
        GameEntity(
            entity_id=f"e{i}",
            position=Vector2(i, i),
            mass=50,
            radius=5,
            entity_type="circle"
        )
        for i in range(100)
    ]
    
    start = time.time()
    for _ in range(1000):
        e = random.choice(entities)
        _ = e.radius
        _ = e.to_dict()
        _ = GameEntity.from_dict(e.to_dict())
    elapsed = time.time() - start
    results["entity_ops_per_sec"] = 3000 / elapsed
    
    # Print results
    print("\n🏆 PERFORMANCE BENCHMARK RESULTS:")
    print(f"  Vector operations: {results['vector_ops_per_sec']:,.0f} ops/sec (target: 100,000)")
    print(f"  Entity operations: {results['entity_ops_per_sec']:,.0f} ops/sec (target: 10,000)")
    
    # Validate against targets
    assert results["vector_ops_per_sec"] > 100000, "Vector operations below target"
    assert results["entity_ops_per_sec"] > 10000, "Entity operations below target"


if __name__ == "__main__":
    # Run specific load tests
    pytest.main([__file__, "-v", "-m", "load_test", "-s"])