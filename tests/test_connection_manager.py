"""
Tests for Connection Manager - Advanced Connection Management

Comprehensive test suite for connection pooling, health checks,
circuit breaker, and connection management functionality.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any

from src.blackholio_client.connection.connection_manager import (
    ConnectionManager,
    ConnectionPool,
    PoolConfiguration,
    PooledConnection,
    CircuitBreaker,
    PoolState,
    HealthStatus,
    get_connection_manager,
    get_connection
)
from src.blackholio_client.connection.spacetimedb_connection import SpacetimeDBConnection
from src.blackholio_client.config.environment import EnvironmentConfig
from src.blackholio_client.connection.server_config import ServerConfig
from src.blackholio_client.exceptions.connection_errors import (
    BlackholioConnectionError,
    ServerUnavailableError,
    BlackholioTimeoutError,
    ConnectionLostError
)


@pytest.fixture
def server_config():
    """Create test server configuration."""
    return ServerConfig(
        language="rust",
        host="localhost",
        port=8080,
        db_identity="test_db",
        protocol="v1.json.spacetimedb",
        use_ssl=False
    )


@pytest.fixture
def pool_config():
    """Create test pool configuration."""
    return PoolConfiguration(
        min_connections=1,
        max_connections=3,
        max_idle_time=60.0,
        health_check_interval=5.0,
        connection_timeout=10.0,
        request_timeout=10.0,
        retry_attempts=2,
        enable_health_checks=True,
        enable_metrics=True
    )


@pytest.fixture
def env_config():
    """Create test environment configuration."""
    with patch.dict('os.environ', {
        'SERVER_LANGUAGE': 'rust',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '8080'
    }):
        return EnvironmentConfig()


class TestPoolConfiguration:
    """Test pool configuration validation."""
    
    def test_valid_configuration(self):
        """Test valid configuration passes validation."""
        config = PoolConfiguration()
        config.validate()  # Should not raise
    
    def test_invalid_min_connections(self):
        """Test invalid min_connections raises error."""
        config = PoolConfiguration(min_connections=-1)
        with pytest.raises(ValueError, match="min_connections must be >= 0"):
            config.validate()
    
    def test_invalid_max_connections(self):
        """Test invalid max_connections raises error."""
        config = PoolConfiguration(max_connections=0)
        with pytest.raises(ValueError, match="max_connections must be >= 1"):
            config.validate()
    
    def test_min_exceeds_max(self):
        """Test min_connections exceeding max_connections raises error."""
        config = PoolConfiguration(min_connections=5, max_connections=3)
        with pytest.raises(ValueError, match="min_connections cannot exceed max_connections"):
            config.validate()
    
    def test_invalid_idle_time(self):
        """Test invalid max_idle_time raises error."""
        config = PoolConfiguration(max_idle_time=0)
        with pytest.raises(ValueError, match="max_idle_time must be > 0"):
            config.validate()


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker starts in closed state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)
        assert breaker.state == "closed"
        assert not breaker.is_open
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=60.0)
        
        # First failure - should remain closed
        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("test error")))
        except:
            pass
        assert breaker.state == "closed"
        
        # Second failure - should open
        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("test error")))
        except:
            pass
        assert breaker.state == "open"
        assert breaker.is_open
    
    def test_circuit_breaker_success_resets_count(self):
        """Test successful call resets failure count."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)
        
        # Cause some failures
        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("test error")))
        except:
            pass
        
        # Success should reset count
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=0.1)
        
        # Cause failure to open circuit
        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("test error")))
        except:
            pass
        assert breaker.state == "open"
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Next call should transition to half-open
        try:
            breaker.call(lambda: "success")
        except:
            pass
        
        # Should now be closed after success
        assert breaker.state == "closed"


class TestPooledConnection:
    """Test pooled connection wrapper."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create mock SpacetimeDB connection."""
        conn = Mock(spec=SpacetimeDBConnection)
        conn.is_connected = True
        return conn
    
    def test_pooled_connection_initialization(self, mock_connection):
        """Test pooled connection initialization."""
        pooled = PooledConnection(connection=mock_connection)
        
        assert pooled.connection == mock_connection
        assert pooled.in_use is False
        assert pooled.use_count == 0
        assert pooled.error_count == 0
        assert pooled.last_error is None
        assert pooled.is_idle is True
        assert pooled.age >= 0
        assert pooled.idle_time >= 0
    
    def test_mark_used(self, mock_connection):
        """Test marking connection as used."""
        pooled = PooledConnection(connection=mock_connection)
        
        pooled.mark_used()
        
        assert pooled.in_use is True
        assert pooled.use_count == 1
        assert pooled.is_idle is False
        assert pooled.idle_time == 0.0
    
    def test_mark_idle(self, mock_connection):
        """Test marking connection as idle."""
        pooled = PooledConnection(connection=mock_connection)
        pooled.in_use = True
        
        pooled.mark_idle()
        
        assert pooled.in_use is False
        assert pooled.is_idle is True
    
    def test_mark_error(self, mock_connection):
        """Test marking connection error."""
        pooled = PooledConnection(connection=mock_connection)
        error = Exception("test error")
        
        pooled.mark_error(error)
        
        assert pooled.error_count == 1
        assert pooled.last_error == error


@pytest.mark.asyncio
class TestConnectionPool:
    """Test connection pool functionality."""
    
    @pytest.fixture
    async def mock_connection(self):
        """Create mock SpacetimeDB connection."""
        conn = AsyncMock(spec=SpacetimeDBConnection)
        conn.is_connected = True
        conn.connect.return_value = True
        conn.disconnect.return_value = None
        return conn
    
    async def test_pool_initialization(self, server_config, pool_config):
        """Test pool initialization."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            await pool.initialize()
            
            assert pool.state == PoolState.ACTIVE
            assert len(pool.connections) == pool_config.min_connections
            assert pool.metrics.health_status == HealthStatus.HEALTHY
            
            await pool.shutdown()
    
    async def test_pool_shutdown(self, server_config, pool_config):
        """Test pool shutdown."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            await pool.initialize()
            
            await pool.shutdown()
            
            assert pool.state == PoolState.SHUTDOWN
            assert len(pool.connections) == 0
    
    async def test_get_connection_success(self, server_config, pool_config):
        """Test successful connection acquisition."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            await pool.initialize()
            
            async with pool.get_connection() as connection:
                assert connection == mock_conn
                assert pool.metrics.active_connections == 1
            
            # Connection should be returned to pool
            assert pool.metrics.active_connections == 0
            
            await pool.shutdown()
    
    async def test_get_connection_timeout(self, server_config):
        """Test connection acquisition timeout."""
        config = PoolConfiguration(max_connections=1, connection_timeout=0.1)
        
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, config)
            await pool.initialize()
            
            # Hold one connection
            async with pool.get_connection():
                # Try to get another - should timeout
                with pytest.raises(BlackholioTimeoutError):
                    async with pool.get_connection(timeout=0.1):
                        pass
            
            await pool.shutdown()
    
    async def test_connection_creation_limit(self, server_config):
        """Test connection creation respects maximum limit."""
        config = PoolConfiguration(min_connections=1, max_connections=2)
        
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, config)
            await pool.initialize()
            
            # Should start with min_connections
            assert len(pool.connections) == 1
            
            # Get both connections
            async with pool.get_connection():
                # This should create a second connection
                async with pool.get_connection():
                    assert len(pool.connections) == 2
            
            await pool.shutdown()
    
    async def test_circuit_breaker_integration(self, server_config, pool_config):
        """Test circuit breaker integration with pool."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            pool.circuit_breaker.state = "open"  # Force circuit open
            
            await pool.initialize()
            
            # Should raise ServerUnavailableError when circuit is open
            with pytest.raises(ServerUnavailableError, match="Circuit breaker is open"):
                async with pool.get_connection():
                    pass
            
            await pool.shutdown()
    
    async def test_health_checks(self, server_config):
        """Test health check functionality."""
        config = PoolConfiguration(health_check_interval=0.1, enable_health_checks=True)
        
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, config)
            await pool.initialize()
            
            # Wait for at least one health check
            await asyncio.sleep(0.2)
            
            assert pool.metrics.last_health_check is not None
            assert pool.metrics.health_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            
            await pool.shutdown()
    
    async def test_pool_metrics(self, server_config, pool_config):
        """Test pool metrics collection."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            await pool.initialize()
            
            metrics = pool.get_metrics()
            
            assert 'state' in metrics
            assert 'total_connections' in metrics
            assert 'active_connections' in metrics
            assert 'idle_connections' in metrics
            assert 'health_status' in metrics
            assert 'config' in metrics
            
            assert metrics['state'] == PoolState.ACTIVE.value
            assert metrics['total_connections'] >= pool_config.min_connections
            
            await pool.shutdown()


@pytest.mark.asyncio
class TestConnectionManager:
    """Test connection manager functionality."""
    
    async def test_connection_manager_initialization(self, env_config):
        """Test connection manager initialization."""
        manager = ConnectionManager(env_config)
        
        assert manager.env_config == env_config
        assert len(manager.pools) == 0
        assert manager.default_pool_config is not None
    
    async def test_get_pool_creates_new(self, env_config):
        """Test get_pool creates new pool when needed."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            manager = ConnectionManager(env_config)
            
            pool = await manager.get_pool("rust")
            
            assert len(manager.pools) == 1
            assert pool.state == PoolState.ACTIVE
            
            await manager.shutdown_all()
    
    async def test_get_pool_reuses_existing(self, env_config):
        """Test get_pool reuses existing pool."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            manager = ConnectionManager(env_config)
            
            pool1 = await manager.get_pool("rust")
            pool2 = await manager.get_pool("rust")
            
            assert pool1 is pool2
            assert len(manager.pools) == 1
            
            await manager.shutdown_all()
    
    async def test_get_connection_context_manager(self, env_config):
        """Test get_connection context manager."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            manager = ConnectionManager(env_config)
            
            async with manager.get_connection("rust") as connection:
                assert connection == mock_conn
            
            await manager.shutdown_all()
    
    async def test_shutdown_all(self, env_config):
        """Test shutdown_all functionality."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            manager = ConnectionManager(env_config)
            
            # Create pools for different languages
            await manager.get_pool("rust")
            await manager.get_pool("python")
            
            assert len(manager.pools) == 2
            
            await manager.shutdown_all()
            
            assert len(manager.pools) == 0
    
    async def test_global_metrics(self, env_config):
        """Test global metrics aggregation."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            manager = ConnectionManager(env_config)
            
            # Create multiple pools
            await manager.get_pool("rust")
            await manager.get_pool("python")
            
            metrics = manager.get_global_metrics()
            
            assert 'total_pools' in metrics
            assert 'pools' in metrics
            assert 'aggregate' in metrics
            
            assert metrics['total_pools'] == 2
            assert len(metrics['pools']) == 2
            assert 'total_connections' in metrics['aggregate']
            assert 'success_rate' in metrics['aggregate']
            
            await manager.shutdown_all()


@pytest.mark.asyncio
class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_connection_manager_singleton(self):
        """Test get_connection_manager returns singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()
        
        assert manager1 is manager2
    
    async def test_get_connection_function(self):
        """Test global get_connection function."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.return_value = None
            mock_conn_class.return_value = mock_conn
            
            async with get_connection("rust") as connection:
                assert connection == mock_conn
            
            # Clean up
            manager = get_connection_manager()
            await manager.shutdown_all()


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling scenarios."""
    
    async def test_connection_creation_failure(self, server_config, pool_config):
        """Test handling of connection creation failures."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn_class.side_effect = Exception("Connection failed")
            
            pool = ConnectionPool(server_config, pool_config)
            
            with pytest.raises(Exception, match="Connection failed"):
                await pool.initialize()
    
    async def test_pool_not_active_error(self, server_config, pool_config):
        """Test error when pool is not active."""
        pool = ConnectionPool(server_config, pool_config)
        # Don't initialize pool
        
        with pytest.raises(BlackholioConnectionError, match="Connection pool is not active"):
            async with pool.get_connection():
                pass
    
    async def test_connection_disconnect_failure(self, server_config, pool_config):
        """Test handling of connection disconnect failures."""
        with patch('src.blackholio_client.connection.connection_manager.SpacetimeDBConnection') as mock_conn_class:
            mock_conn = AsyncMock()
            mock_conn.is_connected = True
            mock_conn.connect.return_value = True
            mock_conn.disconnect.side_effect = Exception("Disconnect failed")
            mock_conn_class.return_value = mock_conn
            
            pool = ConnectionPool(server_config, pool_config)
            await pool.initialize()
            
            # Shutdown should handle disconnect failures gracefully
            await pool.shutdown()
            
            assert pool.state == PoolState.SHUTDOWN


if __name__ == "__main__":
    pytest.main([__file__])