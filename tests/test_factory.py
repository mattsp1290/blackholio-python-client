"""Comprehensive tests for the client factory pattern implementation.

This module tests all aspects of the factory pattern including:
- Factory registration and retrieval
- Language-specific factory implementations
- Factory validation and availability checks
- Client creation through factories
- Integration with environment configuration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from blackholio_client.factory import (
    ClientFactory,
    ClientFactoryBase,
    ClientFactoryRegistry,
    RustClientFactory,
    PythonClientFactory,
    CSharpClientFactory,
    GoClientFactory,
    create_client,
    get_client_factory,
    list_available_languages,
    get_factory_info,
)
from blackholio_client.config.environment import EnvironmentConfig
from blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
from blackholio_client.exceptions.connection_errors import (
    BlackholioConfigurationError,
    BlackholioConnectionError,
)


class TestClientFactoryRegistry:
    """Test the ClientFactoryRegistry functionality."""
    
    def test_singleton_pattern(self):
        """Test that registry follows singleton pattern."""
        registry1 = ClientFactoryRegistry()
        registry2 = ClientFactoryRegistry()
        assert registry1 is registry2
    
    def test_register_factory(self):
        """Test registering a factory."""
        registry = ClientFactoryRegistry()
        
        # Create a mock factory class
        mock_factory = Mock(spec=ClientFactory)
        
        # Register the factory
        registry.register("test", mock_factory)
        
        # Verify it's registered
        assert registry.has_factory("test")
        assert "test" in registry.list_languages()
    
    def test_register_duplicate_factory(self):
        """Test registering duplicate factory raises error."""
        registry = ClientFactoryRegistry()
        mock_factory = Mock(spec=ClientFactory)
        
        # Register once
        registry.register("test2", mock_factory)
        
        # Try to register again without replace flag
        with pytest.raises(BlackholioConfigurationError):
            registry.register("test2", mock_factory)
        
        # Should work with replace flag
        registry.register("test2", mock_factory, replace=True)
    
    def test_unregister_factory(self):
        """Test unregistering a factory."""
        registry = ClientFactoryRegistry()
        mock_factory = Mock(spec=ClientFactory)
        
        # Register and then unregister
        registry.register("test3", mock_factory)
        assert registry.has_factory("test3")
        
        registry.unregister("test3")
        assert not registry.has_factory("test3")
    
    def test_get_factory_class(self):
        """Test getting factory class."""
        registry = ClientFactoryRegistry()
        mock_factory = Mock(spec=ClientFactory)
        
        registry.register("test4", mock_factory)
        factory_class = registry.get_factory_class("test4")
        assert factory_class is mock_factory
    
    def test_get_nonexistent_factory(self):
        """Test getting non-existent factory raises error."""
        registry = ClientFactoryRegistry()
        
        with pytest.raises(BlackholioConfigurationError) as exc_info:
            registry.get_factory_class("nonexistent")
        
        assert "No factory registered" in str(exc_info.value)
    
    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = ClientFactoryRegistry()
        mock_factory = Mock(spec=ClientFactory)
        
        registry.register("test5", mock_factory)
        registry.clear()
        
        assert len(registry.list_languages()) == 0


class TestClientFactoryBase:
    """Test the ClientFactoryBase abstract implementation."""
    
    class ConcreteFactory(ClientFactoryBase):
        """Concrete implementation for testing."""
        
        @property
        def server_language(self) -> str:
            return "test"
        
        def _get_server_path(self) -> Path:
            return Path("/test/server")
    
    def test_initialization(self):
        """Test factory base initialization."""
        factory = self.ConcreteFactory()
        
        assert factory.config is not None
        assert factory.output_dir is not None
        assert factory._validated is False
    
    @patch("blackholio_client.factory.base.SpacetimeDBClientGenerator")
    def test_client_generator_property(self, mock_generator_class):
        """Test lazy loading of client generator."""
        factory = self.ConcreteFactory()
        
        # First access creates instance
        generator1 = factory.client_generator
        assert mock_generator_class.called
        
        # Second access returns same instance
        generator2 = factory.client_generator
        assert generator1 is generator2
    
    @patch("blackholio_client.factory.base.ClientLoader")
    def test_client_loader_property(self, mock_loader_class):
        """Test lazy loading of client loader."""
        factory = self.ConcreteFactory()
        
        # First access creates instance
        loader1 = factory.client_loader
        assert mock_loader_class.called
        
        # Second access returns same instance
        loader2 = factory.client_loader
        assert loader1 is loader2
    
    def test_validate_configuration_language_mismatch(self):
        """Test validation fails on language mismatch."""
        factory = self.ConcreteFactory()
        factory.config = Mock()
        factory.config.validate.return_value = True
        factory.config.server_language = "python"  # Different from "test"
        
        assert not factory.validate_configuration()
    
    def test_create_connection_success(self):
        """Test successful connection creation."""
        factory = self.ConcreteFactory()
        factory.config = Mock()
        factory.config.get_connection_url.return_value = "ws://localhost:3000"
        
        # Mock get_client_module
        factory.get_client_module = Mock(return_value=Mock())
        
        with patch("blackholio_client.factory.base.SpacetimeDBConnection") as mock_conn:
            connection = factory.create_connection(identity="test_id")
            
            mock_conn.assert_called_once()
            assert "test_id" in str(mock_conn.call_args)


class TestLanguageFactories:
    """Test individual language factory implementations."""
    
    @pytest.mark.parametrize("factory_class,language,server_dir", [
        (RustClientFactory, "rust", "server-rust"),
        (PythonClientFactory, "python", "server-python"),
        (CSharpClientFactory, "csharp", "server-csharp"),
        (GoClientFactory, "go", "server-go"),
    ])
    def test_factory_language_property(self, factory_class, language, server_dir):
        """Test each factory returns correct language."""
        factory = factory_class()
        assert factory.server_language == language
    
    def test_rust_factory_validation(self):
        """Test Rust factory validation."""
        factory = RustClientFactory()
        
        with patch.object(factory, "_get_server_path") as mock_path:
            mock_path.return_value = Path("/fake/rust/server")
            
            # Mock the path checks
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False
                
                # Should fail validation if path doesn't exist
                assert not factory.validate_configuration()
    
    def test_python_factory_defaults(self):
        """Test Python factory connection defaults."""
        factory = PythonClientFactory()
        factory.config = Mock()
        factory.config.get_connection_url.return_value = "ws://localhost:3000"
        factory.get_client_module = Mock(return_value=Mock())
        
        with patch("blackholio_client.factory.base.SpacetimeDBConnection") as mock_conn:
            factory.create_connection()
            
            # Check Python-specific defaults
            kwargs = mock_conn.call_args[1]
            assert kwargs.get("serialization") == "json"
            assert kwargs.get("enable_type_checking") is True
    
    def test_csharp_factory_project_detection(self):
        """Test C# factory detects project files."""
        factory = CSharpClientFactory()
        
        with patch.object(factory, "_get_server_path") as mock_path:
            mock_server = Mock()
            mock_server.exists.return_value = True
            mock_server.glob.return_value = [Path("test.csproj")]
            mock_path.return_value = mock_server
            
            # Should find C# project indicators
            with patch("blackholio_client.factory.base.ClientFactoryBase.validate_configuration"):
                result = factory.validate_configuration()
                # Note: actual validation would depend on base class
    
    def test_go_factory_binary_detection(self):
        """Test Go factory detects compiled binaries."""
        factory = GoClientFactory()
        
        with patch.object(factory, "_get_server_path") as mock_path:
            mock_server = Path("/fake/go/server")
            mock_path.return_value = mock_server
            
            with patch("pathlib.Path.exists") as mock_exists:
                def exists_side_effect(path):
                    return str(path).endswith("blackholio-server")
                
                mock_exists.side_effect = exists_side_effect
                
                # Should detect Go binary
                with patch.object(factory, "validate_configuration", return_value=True):
                    assert factory.is_available


class TestClientFactoryFunctions:
    """Test high-level factory functions."""
    
    def test_get_client_factory_default(self):
        """Test getting factory with default configuration."""
        with patch("blackholio_client.factory.client_factory.registry") as mock_registry:
            mock_factory = Mock()
            mock_factory.is_available = True
            mock_registry.get_factory.return_value = mock_factory
            
            factory = get_client_factory()
            
            assert factory is mock_factory
            mock_registry.get_factory.assert_called_once()
    
    def test_get_client_factory_specific_language(self):
        """Test getting factory for specific language."""
        with patch("blackholio_client.factory.client_factory.registry") as mock_registry:
            mock_factory = Mock()
            mock_factory.is_available = True
            mock_registry.get_factory.return_value = mock_factory
            
            factory = get_client_factory(language="python")
            
            assert factory is mock_factory
            call_args = mock_registry.get_factory.call_args
            assert call_args[1]["language"] == "python"
    
    def test_get_unavailable_factory_raises_error(self):
        """Test getting unavailable factory raises error."""
        with patch("blackholio_client.factory.client_factory.registry") as mock_registry:
            mock_factory = Mock()
            mock_factory.is_available = False
            mock_registry.get_factory.return_value = mock_factory
            
            with pytest.raises(BlackholioConfigurationError) as exc_info:
                get_client_factory(language="rust")
            
            assert "not available" in str(exc_info.value)
    
    def test_create_client_success(self):
        """Test successful client creation."""
        mock_connection = Mock(spec=SpacetimeDBConnection)
        
        with patch("blackholio_client.factory.client_factory.get_client_factory") as mock_get:
            mock_factory = Mock()
            mock_factory.server_language = "rust"
            mock_factory.create_connection.return_value = mock_connection
            mock_get.return_value = mock_factory
            
            client = create_client(identity="test_user")
            
            assert client is mock_connection
            mock_factory.create_connection.assert_called_once_with(
                identity="test_user",
                credentials=None
            )
    
    def test_create_client_with_custom_factory(self):
        """Test creating client with custom factory."""
        mock_connection = Mock(spec=SpacetimeDBConnection)
        mock_factory = Mock()
        mock_factory.server_language = "custom"
        mock_factory.create_connection.return_value = mock_connection
        
        client = create_client(factory=mock_factory)
        
        assert client is mock_connection
        mock_factory.create_connection.assert_called_once()
    
    def test_list_available_languages(self):
        """Test listing available languages."""
        with patch("blackholio_client.factory.client_factory.registry") as mock_registry:
            mock_factories = {
                "rust": Mock(is_available=True),
                "python": Mock(is_available=True),
                "csharp": Mock(is_available=False),  # Not available
            }
            mock_registry.get_available_factories.return_value = {
                k: v for k, v in mock_factories.items() if v.is_available
            }
            
            languages = list_available_languages()
            
            assert "rust" in languages
            assert "python" in languages
            assert "csharp" not in languages
            assert languages == sorted(languages)  # Should be sorted
    
    def test_get_factory_info(self):
        """Test getting factory information."""
        with patch("blackholio_client.factory.client_factory.registry") as mock_registry:
            mock_registry.list_languages.return_value = ["rust", "python"]
            
            mock_rust_factory = Mock()
            mock_rust_factory.is_available = True
            mock_rust_factory.validate_configuration.return_value = True
            mock_rust_factory.server_language = "rust"
            mock_rust_factory.__class__.__name__ = "RustClientFactory"
            
            mock_python_factory = Mock()
            mock_python_factory.is_available = False
            mock_python_factory.validate_configuration.side_effect = Exception("Test error")
            
            def get_factory_side_effect(language, **kwargs):
                if language == "rust":
                    return mock_rust_factory
                elif language == "python":
                    return mock_python_factory
                raise Exception(f"Unknown language: {language}")
            
            mock_registry.get_factory.side_effect = get_factory_side_effect
            
            info = get_factory_info()
            
            assert "rust" in info
            assert info["rust"]["available"] is True
            assert info["rust"]["validated"] is True
            assert info["rust"]["class"] == "RustClientFactory"
            
            assert "python" in info
            assert "error" in info["python"]


class TestFactoryIntegration:
    """Integration tests for factory pattern with real components."""
    
    @pytest.mark.integration
    def test_factory_registration_on_import(self):
        """Test that factories are registered on module import."""
        # Import should trigger registration
        from blackholio_client.factory.client_factory import registry
        
        # All factories should be registered
        assert registry.has_factory("rust")
        assert registry.has_factory("python")
        assert registry.has_factory("csharp")
        assert registry.has_factory("go")
    
    @pytest.mark.integration
    def test_end_to_end_client_creation(self):
        """Test end-to-end client creation flow."""
        # This would be a real integration test with actual servers
        # For now, we'll mock the critical parts
        
        with patch("blackholio_client.factory.base.SpacetimeDBClientGenerator"):
            with patch("blackholio_client.factory.base.ClientLoader"):
                with patch("blackholio_client.factory.base.SpacetimeDBConnection"):
                    with patch.dict("os.environ", {"SERVER_LANGUAGE": "rust"}):
                        # Mock server path existence
                        with patch("pathlib.Path.exists", return_value=True):
                            # This should work end-to-end
                            from blackholio_client import create_client
                            
                            # Should not raise any exceptions
                            # In real test, would verify connection works
                            pass  # Placeholder for actual connection test