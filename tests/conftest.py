"""
Pytest configuration and fixtures for blackholio-python-client tests.
"""
import asyncio
import os
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to easily set environment variables for tests."""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _set_env


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all SERVER_* environment variables."""
    env_vars = ["SERVER_LANGUAGE", "SERVER_IP", "SERVER_PORT", "SERVER_MODULE_NAME"]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest_asyncio.fixture
async def mock_spacetime_connection():
    """Mock SpacetimeDB connection for testing."""
    connection = AsyncMock()
    connection.connect = AsyncMock(return_value=True)
    connection.disconnect = AsyncMock(return_value=None)
    connection.is_connected = AsyncMock(return_value=True)
    connection.send_message = AsyncMock(return_value=None)
    connection.receive_message = AsyncMock(return_value={"type": "test", "data": {}})
    return connection


@pytest.fixture
def sample_game_entity():
    """Sample GameEntity for testing."""
    return {
        "id": "test-entity-123",
        "position": {"x": 100.0, "y": 200.0},
        "velocity": {"x": 1.0, "y": -1.0},
        "radius": 25.0,
        "color": "#FF0000",
        "entity_type": "player"
    }


@pytest.fixture
def sample_game_state():
    """Sample game state for testing."""
    return {
        "timestamp": 1234567890,
        "entities": [
            {
                "id": "player-1",
                "position": {"x": 100.0, "y": 100.0},
                "velocity": {"x": 0.0, "y": 0.0},
                "radius": 30.0,
                "color": "#0000FF",
                "entity_type": "player"
            },
            {
                "id": "enemy-1",
                "position": {"x": 300.0, "y": 300.0},
                "velocity": {"x": -1.0, "y": -1.0},
                "radius": 20.0,
                "color": "#FF0000",
                "entity_type": "enemy"
            }
        ],
        "game_status": "active",
        "score": 1500
    }


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file."""
    config_file = tmp_path / "test_config.json"
    config_file.write_text("""{
        "server": {
            "language": "rust",
            "ip": "127.0.0.1",
            "port": 3000
        },
        "client": {
            "timeout": 30,
            "retry_attempts": 3
        }
    }""")
    return str(config_file)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add any singleton resets here as needed
    yield