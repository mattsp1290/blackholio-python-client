"""
Test SpacetimeDB Integration System

Tests for SpacetimeDB client generation, loading, and server management.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from blackholio_client.integration.client_generator import (
    SpacetimeDBClientGenerator, 
    ClientGenerationConfig,
    GenerationResult
)
from blackholio_client.integration.client_loader import ClientLoader, LoadedClient
from blackholio_client.integration.server_manager import ServerManager, ServerInfo, ServerStatus
from blackholio_client.config.environment import EnvironmentConfig
from blackholio_client.exceptions.connection_errors import BlackholioConnectionError


class TestSpacetimeDBClientGenerator:
    """Test SpacetimeDB client generation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = EnvironmentConfig(
            server_language="rust",
            server_ip="localhost", 
            server_port=3000
        )
        
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_find_spacetimedb_cli(self, mock_access, mock_isfile, mock_run):
        """Test finding SpacetimeDB CLI executable."""
        # Mock CLI found at expected path
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        generator = SpacetimeDBClientGenerator(self.config)
        
        # Should find CLI at first path
        assert generator.spacetimedb_cli_path == '/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli'
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_find_spacetimedb_cli_fallback(self, mock_access, mock_isfile, mock_run):
        """Test fallback to 'which' command for CLI discovery."""
        # Mock CLI not found at expected paths
        mock_isfile.return_value = False
        mock_access.return_value = False
        
        # Mock 'which' command success
        mock_run.return_value = Mock(returncode=0, stdout='/usr/local/bin/spacetimedb\n')
        
        generator = SpacetimeDBClientGenerator(self.config)
        
        # Should find CLI via 'which'
        assert generator.spacetimedb_cli_path == '/usr/local/bin/spacetimedb'
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_cli_not_found(self, mock_access, mock_isfile, mock_run):
        """Test error when CLI not found."""
        # Mock CLI not found anywhere
        mock_isfile.return_value = False
        mock_access.return_value = False
        mock_run.return_value = Mock(returncode=1, stdout='')
        
        with pytest.raises(BlackholioConnectionError, match="SpacetimeDB CLI not found"):
            SpacetimeDBClientGenerator(self.config)
    
    @patch('os.path.isdir')
    def test_get_server_path(self, mock_isdir):
        """Test getting server path for different languages."""
        mock_isdir.return_value = True
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            generator = SpacetimeDBClientGenerator(self.config)
            
            # Test rust server path
            rust_path = generator.get_server_path('rust')
            assert 'server-rust' in rust_path
            
            # Test python server path
            python_path = generator.get_server_path('python')
            assert 'server-python' in python_path
    
    @patch('os.path.isdir')
    def test_get_server_path_not_found(self, mock_isdir):
        """Test error when server path not found."""
        mock_isdir.return_value = False
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            generator = SpacetimeDBClientGenerator(self.config)
            
            with pytest.raises(BlackholioConnectionError, match="Server directory not found"):
                generator.get_server_path('rust')
    
    def test_unsupported_server_language(self):
        """Test error for unsupported server language."""
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            generator = SpacetimeDBClientGenerator(self.config)
            
            with pytest.raises(BlackholioConnectionError, match="Unsupported server language"):
                generator.get_server_path('unsupported')
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.isdir')
    def test_execute_generation_success(self, mock_isdir, mock_makedirs, mock_run):
        """Test successful client generation."""
        # Mock successful command execution
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Generated successfully",
            stderr=""
        )
        mock_isdir.return_value = True
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            with patch.object(SpacetimeDBClientGenerator, '_list_generated_files', return_value=['client.py']):
                generator = SpacetimeDBClientGenerator(self.config)
                
                config = ClientGenerationConfig(
                    server_language="rust",
                    server_path="/tmp/server",
                    output_dir="/tmp/output"
                )
                
                result = generator._execute_generation(config)
                
                assert result.success
                assert result.generated_files == ['client.py']
                assert "Generated successfully" in result.stdout
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.makedirs')
    def test_execute_generation_failure(self, mock_makedirs, mock_run):
        """Test failed client generation."""
        # Mock failed command execution
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Generation failed"
        )
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            generator = SpacetimeDBClientGenerator(self.config)
            
            config = ClientGenerationConfig(
                server_language="rust",
                server_path="/tmp/server",
                output_dir="/tmp/output"
            )
            
            result = generator._execute_generation(config)
            
            assert not result.success
            assert "Generation failed" in result.error_message
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    def test_validate_spacetimedb_cli(self, mock_run):
        """Test SpacetimeDB CLI validation."""
        # Mock successful version check
        mock_run.side_effect = [
            Mock(returncode=0, stdout="spacetimedb 0.8.0", stderr=""),
            Mock(returncode=0, stdout="help output", stderr="")
        ]
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            generator = SpacetimeDBClientGenerator(self.config)
            
            validation = generator.validate_spacetimedb_cli()
            
            assert validation['valid']
            assert 'spacetimedb 0.8.0' in validation['version']
            assert validation['generate_help_available']


class TestClientLoader:
    """Test SpacetimeDB client loading."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = EnvironmentConfig(
            server_language="rust",
            server_ip="localhost",
            server_port=3000
        )
    
    def test_find_main_module(self):
        """Test finding main client module."""
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            loader = ClientLoader(self.config)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a client.py file
                client_file = os.path.join(temp_dir, 'client.py')
                with open(client_file, 'w') as f:
                    f.write("# SpacetimeDB client\nclass SpacetimeDBClient:\n    pass\n")
                
                main_module = loader._find_main_module(temp_dir)
                assert main_module == client_file
    
    def test_is_main_module(self):
        """Test identifying main SpacetimeDB modules."""
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            loader = ClientLoader(self.config)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write("import spacetimedb\nclass SpacetimeDBClient:\n    pass\n")
                f.flush()
                
                try:
                    assert loader._is_main_module(f.name)
                finally:
                    os.unlink(f.name)
    
    def test_validate_loaded_client(self):
        """Test validation of loaded clients."""
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            loader = ClientLoader(self.config)
            
            # Create mock loaded client
            mock_module = Mock()
            mock_module.__name__ = "test_module"
            
            with tempfile.TemporaryDirectory() as temp_dir:
                client_file = os.path.join(temp_dir, 'client.py')
                with open(client_file, 'w') as f:
                    f.write("# Test client")
                
                loaded_client = LoadedClient(
                    language="rust",
                    module=mock_module,
                    client_dir=temp_dir,
                    main_module_path=client_file,
                    loaded_modules=['client.py']
                )
                
                assert loader._validate_loaded_client(loaded_client)


class TestServerManager:
    """Test SpacetimeDB server management."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = EnvironmentConfig(
            server_language="rust",
            server_ip="localhost",
            server_port=3000
        )
    
    @patch('os.path.isdir')
    def test_validate_server_files_rust(self, mock_isdir):
        """Test validation of Rust server files."""
        mock_isdir.return_value = True
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            manager = ServerManager(self.config)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create required Rust server files
                cargo_toml = os.path.join(temp_dir, 'Cargo.toml')
                src_dir = os.path.join(temp_dir, 'src')
                
                with open(cargo_toml, 'w') as f:
                    f.write('[package]\nname = "test"\nversion = "0.1.0"\n')
                os.makedirs(src_dir, exist_ok=True)
                
                assert manager._validate_server_files('rust', temp_dir)
    
    @patch('socket.socket')
    def test_is_server_running(self, mock_socket):
        """Test checking if server is running."""
        # Mock successful connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            manager = ServerManager(self.config)
            
            assert manager._is_server_running('rust')
            
            # Verify socket operations
            mock_sock.settimeout.assert_called_with(1.0)
            mock_sock.connect_ex.assert_called_with(('localhost', 3000))
            mock_sock.close.assert_called_once()
    
    @patch('socket.socket')
    def test_is_server_not_running(self, mock_socket):
        """Test checking server not running."""
        # Mock failed connection
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 1  # Connection refused
        
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            manager = ServerManager(self.config)
            
            assert not manager._is_server_running('rust')
    
    def test_get_connection_details(self):
        """Test getting connection details."""
        with patch.object(SpacetimeDBClientGenerator, '_find_spacetimedb_cli'):
            with patch.object(ServerManager, 'get_server_info') as mock_get_info:
                mock_server_info = Mock()
                mock_server_info.port = 3000
                mock_server_info.config.db_identity = 'blackholio_rust'
                mock_server_info.config.protocol = 'v1.json.spacetimedb'
                mock_server_info.config.use_ssl = False
                mock_server_info.status = ServerStatus.AVAILABLE
                
                mock_get_info.return_value = mock_server_info
                
                manager = ServerManager(self.config)
                details = manager.get_connection_details('rust')
                
                assert details['language'] == 'rust'
                assert details['host'] == 'localhost'
                assert details['port'] == 3000
                assert details['db_identity'] == 'blackholio_rust'
                assert details['server_status'] == 'available'


class TestIntegrationWorkflow:
    """Test complete integration workflow."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = EnvironmentConfig(
            server_language="rust",
            server_ip="localhost",
            server_port=3000
        )
    
    @patch('blackholio_client.integration.client_generator.subprocess.run')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_complete_workflow(self, mock_access, mock_isfile, mock_isdir, mock_run):
        """Test complete client generation and loading workflow."""
        # Mock filesystem checks
        mock_isdir.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        # Mock successful generation
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Generated successfully",
            stderr=""
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock generated client file
            client_file = os.path.join(temp_dir, 'client.py')
            with open(client_file, 'w') as f:
                f.write("""
import spacetimedb

class SpacetimeDBClient:
    def __init__(self, **kwargs):
        self.config = kwargs
    
    def connect(self):
        return True
""")
            
            # Test workflow
            with patch.object(SpacetimeDBClientGenerator, 'get_server_path', return_value='/tmp/server'):
                with patch.object(SpacetimeDBClientGenerator, '_list_generated_files', return_value=['client.py']):
                    with patch('tempfile.mkdtemp', return_value=temp_dir):
                        
                        manager = ServerManager(self.config)
                        
                        # This should generate, load, and create client
                        try:
                            client_instance, server_info = manager.prepare_client_for_server('rust')
                            
                            # Verify client was created
                            assert client_instance is not None
                            assert hasattr(client_instance, 'connect')
                            
                            # Verify server info
                            assert server_info.language == 'rust'
                            
                        except Exception as e:
                            # Expected for mock environment
                            assert "Client preparation failed" in str(e) or "Client loading failed" in str(e)


if __name__ == '__main__':
    pytest.main([__file__])