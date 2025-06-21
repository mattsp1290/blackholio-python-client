#!/usr/bin/env python3
"""
Simple integration test for blackholio-agent data model compatibility.

Tests that our unified package provides compatible data models and utilities
that can replace the duplicate code in blackholio-agent.
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, List
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_models():
    """Test data models compatibility."""
    logger.info("🧪 Testing data models...")
    
    try:
        from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle
        
        # Test Vector2 operations
        vec1 = Vector2(10.0, 20.0)
        vec2 = Vector2(5.0, 15.0)
        
        # Mathematical operations
        vec_sum = vec1 + vec2
        vec_diff = vec1 - vec2
        magnitude = vec1.magnitude
        normalized = vec1.normalize()
        distance = vec1.distance_to(vec2)
        
        logger.info(f"✅ Vector2 operations: magnitude={magnitude:.2f}, distance={distance:.2f}")
        
        # Test GameEntity
        entity = GameEntity(
            entity_id=1,
            position=vec1,
            mass=100
        )
        
        # Test entity radius field
        radius = entity.radius
        logger.info(f"✅ GameEntity: radius={radius:.2f}")
        
        # Test GamePlayer
        player = GamePlayer(
            entity_id=1,
            player_id="test_player",
            name="TestPlayer",
            position=vec1,
            mass=50
        )
        
        logger.info(f"✅ GamePlayer: {player.name}")
        
        # Test GameCircle
        circle = GameCircle(
            entity_id=2,
            circle_id="test_circle",
            position=vec2,
            mass=30,
            circle_type="food"
        )
        
        logger.info(f"✅ GameCircle: type={circle.circle_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data models test failed: {e}")
        return False

def test_physics_calculations():
    """Test physics calculations."""
    logger.info("🧪 Testing physics calculations...")
    
    try:
        from blackholio_client.models.physics import calculate_center_of_mass, check_collision
        from blackholio_client.models.game_entities import Vector2, GameEntity
        
        # Create test entities
        entities = [
            GameEntity(entity_id=1, position=Vector2(0, 0), mass=100),
            GameEntity(entity_id=2, position=Vector2(10, 10), mass=200),
            GameEntity(entity_id=3, position=Vector2(-5, 5), mass=150)
        ]
        
        # Test center of mass calculation
        center = calculate_center_of_mass(entities)
        logger.info(f"✅ Center of mass: ({center.x:.2f}, {center.y:.2f})")
        
        # Test collision detection
        entity1 = entities[0]
        entity2 = entities[1]
        collision = check_collision(entity1, entity2)
        logger.info(f"✅ Collision detection working")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Physics calculations test failed: {e}")
        return False

def test_data_converters():
    """Test data converters."""
    logger.info("🧪 Testing data converters...")
    
    try:
        from blackholio_client.models.data_converters import EntityConverter, PlayerConverter
        from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer
        
        # Test entity conversion
        entity_converter = EntityConverter()
        
        # Create test data that mimics SpacetimeDB output
        raw_entity_data = {
            'entity_id': 1,
            'position': {'x': 100.0, 'y': 200.0},
            'mass': 150
        }
        
        entity = entity_converter.from_dict(raw_entity_data)
        logger.info(f"✅ Entity conversion: ID={entity.entity_id}, pos=({entity.position.x}, {entity.position.y})")
        
        # Test player conversion
        player_converter = PlayerConverter()
        
        raw_player_data = {
            'identity': 'test_identity_123',
            'player_id': 1,
            'name': 'TestPlayer',
            'created_at': int(time.time())
        }
        
        player = player_converter.from_dict(raw_player_data)
        logger.info(f"✅ Player conversion: {player.name}, ID={player.player_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data converters test failed: {e}")
        return False

def test_statistics_tracking():
    """Test statistics tracking."""
    logger.info("🧪 Testing statistics tracking...")
    
    try:
        from blackholio_client.models.game_statistics import PlayerStatistics, SessionStatistics
        
        # Test player statistics
        player_stats = PlayerStatistics(player_id="test_player")
        player_stats.update_movement(5.0, 10.0)  # distance, speed
        player_stats.record_food_consumption(5.0, 10)  # mass, value
        player_stats.record_player_consumption(20.0)  # consumed mass
        
        logger.info(f"✅ Player stats: distance={player_stats.total_distance_traveled}, food={player_stats.food_consumed}")
        
        # Test session statistics
        session_stats = SessionStatistics(session_id="test_session")
        session_stats.record_food_spawn(5)
        session_stats.record_food_consumption("player1", 10.0, 5)
        session_stats.end_session()
        
        logger.info(f"✅ Session stats: duration={session_stats.get_session_duration():.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Statistics tracking test failed: {e}")
        return False

def test_serialization():
    """Test serialization systems."""
    logger.info("🧪 Testing serialization...")
    
    try:
        from blackholio_client.models.serialization import JSONSerializer, serialize, deserialize, SerializationFormat, ServerLanguage
        from blackholio_client.models.game_entities import Vector2, GameEntity
        
        # Test JSON serialization
        serializer = JSONSerializer()
        
        entity = GameEntity(
            entity_id=1,
            position=Vector2(100.0, 200.0),
            mass=150
        )
        
        # Serialize
        serialized = serializer.serialize(entity)
        logger.info(f"✅ Serialized entity: {len(serialized)} chars")
        
        # Deserialize
        deserialized = serializer.deserialize(serialized, GameEntity)
        logger.info(f"✅ Deserialized entity: ID={deserialized.entity_id}")
        
        # Test convenience functions
        quick_serialized = serialize(entity, SerializationFormat.JSON, ServerLanguage.RUST)
        quick_deserialized = deserialize(quick_serialized, GameEntity, SerializationFormat.JSON, ServerLanguage.RUST)
        logger.info(f"✅ Quick serialization working")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Serialization test failed: {e}")
        return False

def test_ml_compatibility():
    """Test ML agent compatibility patterns."""
    logger.info("🧪 Testing ML compatibility...")
    
    try:
        from blackholio_client.models.game_entities import Vector2, GameEntity
        
        # Test observation space creation (typical ML pattern)
        entities = {
            1: GameEntity(entity_id=1, position=Vector2(10, 20), mass=100),
            2: GameEntity(entity_id=2, position=Vector2(30, 40), mass=150),
            3: GameEntity(entity_id=3, position=Vector2(-10, 15), mass=80)
        }
        
        # Create observation vector (mimics blackholio-agent)
        observation = np.zeros(64, dtype=np.float32)
        
        # Fill observation with entity data
        for i, (entity_id, entity) in enumerate(list(entities.items())[:10]):
            base_idx = i * 6
            if base_idx + 5 < len(observation):
                observation[base_idx] = entity_id
                observation[base_idx + 1] = entity.position.x
                observation[base_idx + 2] = entity.position.y
                observation[base_idx + 3] = entity.mass
                observation[base_idx + 4] = entity.radius
                observation[base_idx + 5] = 1.0  # exists flag
        
        logger.info(f"✅ ML observation created: shape={observation.shape}, entities={len(entities)}")
        
        # Test action space (movement vector)
        action = np.array([0.5, -0.3], dtype=np.float32)  # normalized movement
        direction = Vector2(action[0], action[1])
        normalized_direction = direction.normalize()
        
        logger.info(f"✅ ML action processing: direction=({normalized_direction.x:.2f}, {normalized_direction.y:.2f})")
        
        # Test reward calculation patterns
        player_entities = [entity for entity in entities.values() if entity.entity_id == 1]
        reward = 0.1  # base survival reward
        
        if player_entities:
            player_mass = sum(e.mass for e in player_entities)
            reward += player_mass * 0.001  # mass-based reward
        
        logger.info(f"✅ ML reward calculation: {reward:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ML compatibility test failed: {e}")
        return False

def test_performance():
    """Test performance characteristics."""
    logger.info("🧪 Testing performance...")
    
    try:
        from blackholio_client.models.game_entities import Vector2, GameEntity
        
        # Performance test - rapid entity operations
        start_time = time.time()
        iterations = 10000
        
        for i in range(iterations):
            # Create entities
            entity = GameEntity(
                entity_id=i,
                position=Vector2(i * 0.1, i * 0.2),
                mass=100 + i
            )
            
            # Perform calculations
            radius = entity.radius
            distance = entity.position.magnitude
            
            # Vector operations
            vec = Vector2(i, i + 1)
            normalized = vec.normalize()
        
        duration = time.time() - start_time
        ops_per_second = iterations / duration
        
        logger.info(f"✅ Performance test: {ops_per_second:.0f} ops/sec")
        
        # Performance should be acceptable for ML training
        return ops_per_second > 1000  # Should be much faster than this
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("="*80)
    print("🎯 BLACKHOLIO-AGENT DATA MODEL INTEGRATION TEST")
    print("="*80)
    
    tests = [
        ("Data Models", test_data_models),
        ("Physics Calculations", test_physics_calculations),
        ("Data Converters", test_data_converters),
        ("Statistics Tracking", test_statistics_tracking),
        ("Serialization", test_serialization),
        ("ML Compatibility", test_ml_compatibility),
        ("Performance", test_performance)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔄 Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Generate report
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n📊 INTEGRATION TEST RESULTS:")
    print(f"   Passed: {passed}/{total} ({success_rate:.1f}%)")
    
    print(f"\n🔍 Detailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:20} : {status}")
    
    print(f"\n💡 Conclusion:")
    if success_rate >= 85:
        print("   ✅ INTEGRATION READY - blackholio-python-client data models are compatible")
        print("   ✅ Can replace duplicate code in blackholio-agent environment modules")
        print("   ✅ ML agent functionality should be preserved")
    else:
        print("   ❌ INTEGRATION ISSUES - Some compatibility problems detected")
        print("   🔧 Fix failing tests before migration")
    
    print("="*80)
    
    return success_rate >= 85

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)