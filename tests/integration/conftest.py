"""
Integration test fixtures and configuration for real SpacetimeDB server testing.
"""

import asyncio
import os
import pytest
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from unittest.mock import patch

from blackholio_client.config.environment import EnvironmentConfig
from blackholio_client.connection.server_config import ServerConfig
from blackholio_client.integration.client_generator import SpacetimeDBClientGenerator
from blackholio_client.client import GameClient, create_game_client


# Test configuration
SPACETIME_CLI_PATH = "/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli"
SERVER_BASE_PATH = "/Users/punk1290/git/Blackholio"
TEST_TIMEOUT = 60  # seconds
SERVER_START_DELAY = 5  # seconds to wait for server startup


class SpacetimeDBTestServer:
    """Manages connection to an existing SpacetimeDB server instance."""
    
    def __init__(self, language: str, server_path: str, port: int):
        self.language = language
        self.server_path = server_path
        self.port = port
        self.temp_dir: Optional[str] = None
        self.client_path: Optional[str] = None
        self.module_name = f"blackholio-test-{language}"
        
    async def setup(self) -> bool:
        """Setup for testing - generate client and verify server connection."""
        try:
            # Create temporary directory for generated clients
            self.temp_dir = tempfile.mkdtemp(prefix=f"spacetime_test_{self.language}_")
            
            # Check if server is responsive
            if not self._check_server_connection():
                print(f"SpacetimeDB server not responsive on port {self.port}")
                return False
            
            # Generate client code
            cmd = [
                SPACETIME_CLI_PATH,
                "generate",
                "--lang", "python",
                "--out-dir", self.temp_dir,
                "--project-path", self.server_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"Client generation failed for {self.language}: {result.stderr}")
                return False
            
            self.client_path = self.temp_dir
            return True
            
        except Exception as e:
            print(f"Error setting up test environment for {self.language}: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources."""
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def _check_server_connection(self) -> bool:
        """Check if SpacetimeDB server is responsive."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=5):
                return True
        except (socket.error, ConnectionRefusedError):
            return False
    
    def is_available(self) -> bool:
        """Check if the server is available for testing."""
        return self._check_server_connection()


@pytest.fixture(scope="session")
def available_servers() -> Dict[str, str]:
    """Get available SpacetimeDB server implementations."""
    servers = {}
    
    # Check for Rust server
    rust_path = f"{SERVER_BASE_PATH}/server-rust"
    if os.path.exists(rust_path) and os.path.exists(f"{rust_path}/Cargo.toml"):
        servers["rust"] = rust_path
    
    # Check for Python server
    python_path = f"{SERVER_BASE_PATH}/server-python"
    if os.path.exists(python_path) and os.path.exists(f"{python_path}/Cargo.toml"):
        servers["python"] = python_path
    
    # Check for C# server
    csharp_path = f"{SERVER_BASE_PATH}/server-csharp"
    if os.path.exists(csharp_path) and os.path.exists(f"{csharp_path}/StdbModule.csproj"):
        servers["csharp"] = csharp_path
    
    # Check for Go server
    go_path = f"{SERVER_BASE_PATH}/server-go"
    if os.path.exists(go_path) and os.path.exists(f"{go_path}/go.mod"):
        servers["go"] = go_path
    
    return servers


@pytest.fixture(scope="session")
def spacetime_cli_available() -> bool:
    """Check if SpacetimeDB CLI is available."""
    return os.path.exists(SPACETIME_CLI_PATH) and os.access(SPACETIME_CLI_PATH, os.X_OK)


@pytest.fixture(params=["rust"])  # Start with Rust server for initial testing
async def test_server(request, available_servers, spacetime_cli_available) -> SpacetimeDBTestServer:
    """Provide connection to an existing SpacetimeDB server for testing."""
    if not spacetime_cli_available:
        pytest.skip("SpacetimeDB CLI not available")
    
    language = request.param
    if language not in available_servers:
        pytest.skip(f"{language} server not available")
    
    # Use default port for SpacetimeDB server (assumed to be running)
    port = 3000
    
    server = SpacetimeDBTestServer(
        language=language,
        server_path=available_servers[language],
        port=port
    )
    
    # Setup test environment
    setup_ok = await server.setup()
    if not setup_ok:
        pytest.skip(f"Failed to setup test environment for {language} server - ensure SpacetimeDB server is running on port {port}")
    
    yield server
    
    # Cleanup
    server.cleanup()


@pytest.fixture
def test_environment_config(test_server) -> EnvironmentConfig:
    """Create test environment configuration."""
    with patch.dict(os.environ, {
        "SERVER_LANGUAGE": test_server.language,
        "SERVER_IP": "127.0.0.1",
        "SERVER_PORT": str(test_server.port),
        "SERVER_MODULE_NAME": "blackholio"
    }):
        config = EnvironmentConfig()
        # Override client path for testing
        config._spacetime_cli_path = SPACETIME_CLI_PATH
        return config


@pytest.fixture
async def test_game_client(test_environment_config, test_server) -> GameClient:
    """Create a test game client connected to the test server."""
    client = create_game_client(
        host=f"{test_environment_config.server_ip}:{test_environment_config.server_port}",
        database="blackholio-test",
        server_language=test_environment_config.server_language
    )
    yield client
    
    # Cleanup - disconnect if connected
    try:
        if hasattr(client, 'disconnect'):
            await client.disconnect()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return {
        "username": "test_player",
        "position": {"x": 100.0, "y": 100.0},
        "velocity": {"x": 0.0, "y": 0.0},
        "radius": 30.0,
        "color": "#0000FF"
    }


@pytest.fixture
def sample_game_actions():
    """Sample game actions for testing."""
    return [
        {"action": "enter_game", "username": "test_player"},
        {"action": "move_player", "direction": {"x": 1.0, "y": 0.0}},
        {"action": "player_split"},
        {"action": "leave_game"}
    ]


# Utility functions for integration tests
def wait_for_server_ready(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for server to be ready to accept connections."""
    import socket
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    
    return False


def get_server_status(language: str, port: int) -> Dict[str, any]:
    """Get server status information."""
    try:
        # Try to connect to see if server is responsive
        import socket
        with socket.create_connection(("127.0.0.1", port), timeout=5):
            return {
                "language": language,
                "port": port,
                "status": "running",
                "responsive": True
            }
    except Exception as e:
        return {
            "language": language,
            "port": port,
            "status": "error",
            "responsive": False,
            "error": str(e)
        }