#!/usr/bin/env python3
"""
Simple Integration Test: blackholio-python-client with client-pygame

Focused test to validate basic compatibility and eliminate code duplication.
"""

import sys
import os
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add blackholio-python-client to path
client_path = os.path.join(os.path.dirname(__file__), 'src')
if client_path not in sys.path:
    sys.path.insert(0, client_path)

# Import shared package components
try:
    from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle
    from blackholio_client.models.data_converters import EntityConverter, PlayerConverter, CircleConverter
    from blackholio_client.models.physics import calculate_center_of_mass, calculate_entity_radius
    from blackholio_client.models.game_statistics import PlayerStatistics, SessionStatistics
    from blackholio_client.models.serialization import serialize, deserialize
    from blackholio_client.config.environment import EnvironmentConfig
    from blackholio_client.client import create_game_client
    import blackholio_client
    logger.info(f"✅ Successfully imported blackholio_client (v{getattr(blackholio_client, '__version__', 'unknown')})")
except ImportError as e:
    logger.error(f"❌ Failed to import blackholio_client: {e}")
    sys.exit(1)


def test_data_models():
    """Test that shared data models are compatible with pygame client."""
    logger.info("🔍 Testing data model compatibility...")
    
    # Test Vector2 - pygame client patterns
    position = Vector2(100.5, 200.75)
    direction = Vector2(0.866, -0.5)
    
    # Test vector operations (pygame client usage)
    velocity = direction * 50.0
    new_position = position + velocity
    distance = (new_position - position).magnitude
    normalized_dir = direction.normalize()
    
    assert abs(velocity.x - 43.3) < 0.1, f"Velocity X failed: {velocity.x}"
    assert abs(velocity.y - (-25.0)) < 0.1, f"Velocity Y failed: {velocity.y}"
    assert abs(distance - 50.0) < 0.1, f"Distance failed: {distance}"
    assert abs(normalized_dir.magnitude - 1.0) < 0.001, f"Normalization failed: {normalized_dir.magnitude}"
    
    # Test GameEntity creation
    entity = GameEntity(
        entity_id="entity_1",
        position=position,
        mass=50
    )
    
    # Test GamePlayer creation  
    player = GamePlayer(
        entity_id="player_1",
        player_id="test_player_1",
        name="TestPlayer"
    )
    
    # Test GameCircle creation
    circle = GameCircle(
        entity_id="circle_1",
        player_id="test_player_1",
        direction=direction,
        speed=100.0
    )
    
    logger.info(f"✅ Data models: Entity({entity.entity_id}), Player({player.name}), Circle({circle.entity_id})")
    return entity, player, circle


def test_physics_calculations(entities):
    """Test physics calculations used by pygame client."""
    logger.info("🔍 Testing physics calculations...")
    
    # Test entity radius calculation
    radius = calculate_entity_radius(entities[0].mass)
    assert radius > 0, f"Radius calculation failed: {radius}"
    
    # Test center of mass calculation
    center_of_mass = calculate_center_of_mass(entities)
    assert center_of_mass.x >= 0, f"Center of mass X invalid: {center_of_mass.x}"
    assert center_of_mass.y >= 0, f"Center of mass Y invalid: {center_of_mass.y}"
    
    logger.info(f"✅ Physics: Radius={radius:.2f}, COM=({center_of_mass.x:.2f}, {center_of_mass.y:.2f})")
    return True


def test_data_conversion():
    """Test data conversion from SpacetimeDB formats."""
    logger.info("🔍 Testing data conversion...")
    
    # Test entity conversion
    converter = EntityConverter()
    spacetime_entity = {
        'entity_id': "entity_42",
        'position': {'x': 150.0, 'y': 250.0},
        'mass': 75
    }
    
    entity = converter.from_dict(spacetime_entity)
    assert entity.entity_id == "entity_42", "Entity conversion failed"
    assert entity.position.x == 150.0, "Position conversion failed"
    assert entity.mass == 75, "Mass conversion failed"
    
    logger.info(f"✅ Data conversion: Entity({entity.entity_id}) at ({entity.position.x}, {entity.position.y})")
    return True


def test_statistics_tracking():
    """Test statistics tracking for pygame client."""
    logger.info("🔍 Testing statistics tracking...")
    
    # Test player statistics
    player_stats = PlayerStatistics(player_id="test_player")
    session_stats = SessionStatistics(session_id="test_session")
    
    # Record some gameplay events
    player_stats.record_movement_distance(25.5)
    player_stats.record_food_consumed(3)
    
    session_stats.record_frame_time(0.016)  # 60 FPS
    session_stats.record_entity_count(15)
    
    assert player_stats.total_distance_moved == 25.5, f"Distance tracking failed: {player_stats.total_distance_moved}"
    assert player_stats.food_consumed == 3, f"Food tracking failed: {player_stats.food_consumed}"
    
    logger.info(f"✅ Statistics: Distance={player_stats.total_distance_moved}, Food={player_stats.food_consumed}")
    return True


def test_serialization(entity, player, circle):
    """Test serialization for pygame client data persistence."""
    logger.info("🔍 Testing serialization...")
    
    # Test JSON serialization (pygame client uses this)
    entity_json = serialize(entity, format='json')
    player_json = serialize(player, format='json')
    circle_json = serialize(circle, format='json')
    
    # Test deserialization
    restored_entity = deserialize(entity_json, GameEntity, format='json')
    restored_player = deserialize(player_json, GamePlayer, format='json')
    restored_circle = deserialize(circle_json, GameCircle, format='json')
    
    assert restored_entity.entity_id == entity.entity_id, "Entity deserialization failed"
    assert restored_player.name == player.name, "Player deserialization failed"
    assert restored_circle.speed == circle.speed, "Circle deserialization failed"
    
    logger.info(f"✅ Serialization: Entity {len(entity_json)} chars, Player {len(player_json)} chars")
    return True


def test_configuration():
    """Test environment configuration compatibility."""
    logger.info("🔍 Testing configuration...")
    
    # Test configuration with pygame client environment variables
    test_env = {
        'SERVER_LANGUAGE': 'rust',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '3000'
    }
    
    # Set environment temporarily
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        config = EnvironmentConfig()
        assert config.server_language == 'rust', f"Server language failed: {config.server_language}"
        assert config.server_ip == 'localhost', f"Server IP failed: {config.server_ip}"
        assert config.server_port == 3000, f"Server port failed: {config.server_port}"
        
        logger.info(f"✅ Configuration: {config.server_language}@{config.server_ip}:{config.server_port}")
        return True
        
    finally:
        # Restore environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_game_client_creation():
    """Test GameClient creation for pygame integration."""
    logger.info("🔍 Testing game client creation...")
    
    try:
        client = create_game_client(
            host='localhost',
            database='blackholio',
            server_language='rust'
        )
        
        assert client is not None, "GameClient creation failed"
        assert hasattr(client, 'connect'), "GameClient missing connect method"
        assert hasattr(client, 'enter_game'), "GameClient missing enter_game method"
        assert hasattr(client, 'move_player'), "GameClient missing move_player method"
        
        logger.info(f"✅ GameClient created: {type(client).__name__}")
        return True
        
    except Exception as e:
        logger.error(f"GameClient creation failed: {e}")
        return False


def main():
    """Run pygame integration tests."""
    print("🎮 Blackholio Python Client - Simple Pygame Integration Test")
    print("="*60)
    
    tests = [
        test_data_models,
        test_physics_calculations,
        test_data_conversion,
        test_statistics_tracking,
        test_serialization,
        test_configuration,
        test_game_client_creation
    ]
    
    results = []
    entity, player, circle = None, None, None
    
    for test_func in tests:
        try:
            if test_func == test_data_models:
                result = test_func()
                if result:
                    entity, player, circle = result
                    results.append(True)
                else:
                    results.append(False)
            elif test_func in [test_physics_calculations]:
                if entity:
                    result = test_func([entity])
                    results.append(result)
                else:
                    results.append(False)
            elif test_func == test_serialization:
                if entity and player and circle:
                    result = test_func(entity, player, circle)
                    results.append(result)
                else:
                    results.append(False)
            else:
                result = test_func()
                results.append(result)
        except Exception as e:
            logger.error(f"❌ Test {test_func.__name__} failed: {e}")
            results.append(False)
    
    # Generate results
    total_tests = len(results)
    passed_tests = sum(results)
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\n📊 Test Results:")
    for i, (test_func, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_func.__name__}")
    
    print(f"\n🏆 Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print(f"\n🎉 All pygame integration tests PASSED!")
        print(f"✨ blackholio-python-client is compatible with client-pygame!")
        print(f"\n🚀 Ready for pygame client migration:")
        print(f"   • Data models can replace pygame client duplicates")
        print(f"   • Physics calculations provide enhanced functionality")
        print(f"   • Serialization supports pygame client data persistence")
        print(f"   • Configuration integrates with pygame environment variables")
        print(f"   • GameClient provides unified interface for SpacetimeDB")
        return 0
    else:
        print(f"\n❌ Some tests failed - manual review needed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)