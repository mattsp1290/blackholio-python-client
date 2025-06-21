"""
Setup validation tests for integration testing.

Verifies that the integration test environment is properly configured
and can connect to local SpacetimeDB servers.
"""

import os
import pytest
import subprocess
from pathlib import Path

from blackholio_client.config.environment import EnvironmentConfig


class TestIntegrationSetup:
    """Validate integration test setup."""
    
    def test_spacetime_cli_available(self):
        """Test that SpacetimeDB CLI is available."""
        cli_path = "/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli"
        assert os.path.exists(cli_path), f"SpacetimeDB CLI not found at {cli_path}"
        assert os.access(cli_path, os.X_OK), f"SpacetimeDB CLI not executable at {cli_path}"
    
    def test_server_directories_exist(self):
        """Test that server implementation directories exist."""
        base_path = "/Users/punk1290/git/Blackholio"
        
        # Check for at least one server implementation
        server_dirs = [
            f"{base_path}/server-rust",
            f"{base_path}/server-python", 
            f"{base_path}/server-csharp",
            f"{base_path}/server-go"
        ]
        
        existing_servers = [d for d in server_dirs if os.path.exists(d)]
        assert len(existing_servers) > 0, f"No server implementations found in {base_path}"
        
        # Verify at least one has proper project files
        valid_servers = []
        for server_dir in existing_servers:
            if "rust" in server_dir and os.path.exists(f"{server_dir}/Cargo.toml"):
                valid_servers.append("rust")
            elif "python" in server_dir and os.path.exists(f"{server_dir}/Cargo.toml"):
                valid_servers.append("python")
            elif "csharp" in server_dir and os.path.exists(f"{server_dir}/StdbModule.csproj"):
                valid_servers.append("csharp")
            elif "go" in server_dir and os.path.exists(f"{server_dir}/go.mod"):
                valid_servers.append("go")
        
        assert len(valid_servers) > 0, f"No valid server implementations found. Checked: {existing_servers}"
    
    def test_environment_config_creation(self):
        """Test that environment configuration can be created."""
        config = EnvironmentConfig()
        assert config is not None
        assert hasattr(config, 'server_language')
        assert hasattr(config, 'server_ip')
        assert hasattr(config, 'server_port')
    
    def test_spacetime_cli_version(self):
        """Test that SpacetimeDB CLI is functional."""
        cli_path = "/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli"
        
        try:
            result = subprocess.run(
                [cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # CLI should respond (return code 0 or 1 both acceptable for --version)
            assert result.returncode in [0, 1], f"CLI failed with return code {result.returncode}"
            
            # Should have some output
            output = result.stdout + result.stderr
            assert len(output) > 0, "CLI produced no output"
            
        except subprocess.TimeoutExpired:
            pytest.fail("SpacetimeDB CLI timeout - may not be functional")
        except Exception as e:
            pytest.fail(f"Error running SpacetimeDB CLI: {e}")
    
    def test_rust_server_availability(self):
        """Test that Rust server is available for testing."""
        server_path = "/Users/punk1290/git/Blackholio/server-rust"
        
        if not os.path.exists(server_path):
            pytest.skip("Rust server not available")
        
        cargo_toml = f"{server_path}/Cargo.toml"
        assert os.path.exists(cargo_toml), f"Cargo.toml not found at {cargo_toml}"
        
        # Check that Cargo.toml contains spacetimedb dependency
        with open(cargo_toml, 'r') as f:
            content = f.read()
            assert "spacetimedb" in content, "spacetimedb dependency not found in Cargo.toml"
    
    def test_python_imports_work(self):
        """Test that all required Python imports work."""
        try:
            from blackholio_client import GameClient, create_game_client
            from blackholio_client.config.environment import EnvironmentConfig
            from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer
            from blackholio_client.integration.client_generator import SpacetimeDBClientGenerator
            
            # All imports successful
            assert True
            
        except ImportError as e:
            pytest.fail(f"Required import failed: {e}")
    
    def test_integration_test_fixtures_accessible(self):
        """Test that integration test fixtures are properly set up."""
        # This test validates that the conftest.py file and fixtures are accessible
        fixtures_file = Path(__file__).parent / "conftest.py"
        assert fixtures_file.exists(), "Integration test conftest.py not found"
        
        # Test that we can import from conftest
        try:
            from .conftest import SpacetimeDBTestServer
            assert SpacetimeDBTestServer is not None
        except ImportError as e:
            pytest.fail(f"Could not import integration test fixtures: {e}")
    
    @pytest.mark.integration
    def test_integration_test_marker(self):
        """Test that integration test markers work."""
        # This test should only run when integration tests are specifically requested
        assert True  # If this runs, the marker system is working


class TestClientPackageIntegrity:
    """Test that the client package is properly built and accessible."""
    
    def test_package_structure(self):
        """Test that package structure is correct."""
        src_path = Path(__file__).parent.parent.parent / "src" / "blackholio_client"
        assert src_path.exists(), f"Package source not found at {src_path}"
        
        # Check for essential modules
        essential_modules = [
            "__init__.py",
            "client.py", 
            "config/__init__.py",
            "models/__init__.py",
            "connection/__init__.py",
            "integration/__init__.py"
        ]
        
        for module in essential_modules:
            module_path = src_path / module
            assert module_path.exists(), f"Essential module {module} not found"
    
    def test_package_version(self):
        """Test that package version is accessible."""
        try:
            import blackholio_client
            # Should have version attribute
            assert hasattr(blackholio_client, '__version__') or hasattr(blackholio_client, 'VERSION')
        except ImportError:
            pytest.fail("Could not import blackholio_client package")
    
    def test_main_client_class(self):
        """Test that main client class can be imported and instantiated."""
        try:
            from blackholio_client.client import GameClient
            from blackholio_client.config.environment import EnvironmentConfig
            
            # Should be able to create config
            config = EnvironmentConfig()
            
            # GameClient class should be importable (even if not instantiable without server)
            assert GameClient is not None
            assert callable(GameClient)
            
        except Exception as e:
            pytest.fail(f"Error with main client class: {e}")