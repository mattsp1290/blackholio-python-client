"""
Enhanced Connection Manager - SDK-Powered Connection Management

This module provides enhanced connection management by using the modernized
spacetimedb-python-sdk's advanced connection pooling and management features
while maintaining compatibility with the existing blackholio-client API.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, AsyncGenerator

# Import from the modernized SDK
from spacetimedb_sdk.connection import (
    EnhancedConnectionManager as SDKConnectionManager,
    ServerConfig as SDKServerConfig,
    PoolConfiguration as SDKPoolConfiguration,
    get_connection_manager as get_sdk_connection_manager,
    get_connection as get_sdk_connection
)
from spacetimedb_sdk.factory.base import ServerLanguage, OptimizationProfile
from spacetimedb_sdk import ModernSpacetimeDBClient

from .server_config import ServerConfig
from ..exceptions.connection_errors import (
    BlackholioConnectionError,
    ServerUnavailableError,
    BlackholioTimeoutError,
    ConnectionLostError
)


logger = logging.getLogger(__name__)


class EnhancedConnectionManager:
    """
    Enhanced connection manager that leverages the modernized SDK's
    advanced connection management while providing backward compatibility
    with the existing blackholio-client API.
    """
    
    def __init__(self, env_config = None):
        """
        Initialize enhanced connection manager.
        
        Args:
            env_config: Environment configuration (for compatibility)
        """
        self.env_config = env_config
        self._sdk_manager = get_sdk_connection_manager()
        
        logger.info("Initialized enhanced connection manager using modernized SDK")
    
    def _convert_config(self, server_config: ServerConfig) -> SDKServerConfig:
        """Convert blackholio ServerConfig to SDK ServerConfig."""
        language_map = {
            'rust': ServerLanguage.RUST,
            'python': ServerLanguage.PYTHON,
            'csharp': ServerLanguage.CSHARP,
            'go': ServerLanguage.GO
        }
        
        sdk_language = language_map.get(server_config.language.lower(), ServerLanguage.RUST)
        
        return SDKServerConfig(
            language=sdk_language,
            host=server_config.host,
            port=server_config.port,
            database=server_config.db_identity,
            auth_token=getattr(server_config, 'auth_token', None),
            optimization_profile=OptimizationProfile.BALANCED,
            additional_config={
                'original_config': server_config.__dict__
            }
        )
    
    async def get_pool(self, server_config: ServerConfig, pool_config = None):
        """
        Get or create connection pool for specified server configuration.
        
        Args:
            server_config: Server configuration
            pool_config: Pool configuration (optional)
            
        Returns:
            Connection pool (SDK-powered)
        """
        sdk_server_config = self._convert_config(server_config)
        
        # Convert pool config if provided
        sdk_pool_config = None
        if pool_config:
            sdk_pool_config = SDKPoolConfiguration(
                min_connections=getattr(pool_config, 'min_connections', 1),
                max_connections=getattr(pool_config, 'max_connections', 10),
                max_idle_time=getattr(pool_config, 'max_idle_time', 300.0),
                health_check_interval=getattr(pool_config, 'health_check_interval', 30.0),
                connection_timeout=getattr(pool_config, 'connection_timeout', 30.0)
            )
        
        return await self._sdk_manager.get_pool(sdk_server_config, sdk_pool_config)
    
    @asynccontextmanager
    async def get_connection(self, 
                           server_config: Optional[ServerConfig] = None,
                           server_language: Optional[str] = None,
                           timeout: Optional[float] = None) -> AsyncGenerator[ModernSpacetimeDBClient, None]:
        """
        Get a connection from the enhanced pool.
        
        Args:
            server_config: Server configuration (if provided)
            server_language: Server language (fallback)
            timeout: Connection timeout
            
        Yields:
            ModernSpacetimeDBClient instance (SDK-powered)
        """
        try:
            if server_config:
                sdk_server_config = self._convert_config(server_config)
            elif server_language:
                # Create a default config for the language
                from .server_config import ServerConfig as BlackholioServerConfig
                temp_config = BlackholioServerConfig.for_language(server_language)
                sdk_server_config = self._convert_config(temp_config)
            else:
                # Default to Rust
                temp_config = ServerConfig.for_language('rust')
                sdk_server_config = self._convert_config(temp_config)
            
            async with self._sdk_manager.get_connection(
                server_config=sdk_server_config,
                timeout=timeout
            ) as connection:
                yield connection
                
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            # Convert SDK exceptions to blackholio exceptions for compatibility
            if "timeout" in str(e).lower():
                raise BlackholioTimeoutError(f"Connection timeout: {e}")
            elif "unavailable" in str(e).lower():
                raise ServerUnavailableError(f"Server unavailable: {e}")
            else:
                raise BlackholioConnectionError(f"Connection failed: {e}")
    
    async def shutdown_all(self) -> None:
        """Shutdown all connection pools."""
        await self._sdk_manager.shutdown_all()
        logger.info("All connection pools shutdown via enhanced manager")
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global metrics across all pools."""
        sdk_metrics = self._sdk_manager.get_global_metrics()
        
        # Convert SDK metrics to blackholio format for compatibility
        return {
            'total_pools': sdk_metrics.get('total_pools', 0),
            'enhanced_sdk_powered': True,
            'sdk_metrics': sdk_metrics,
            'pools': sdk_metrics.get('pools', {}),
            'aggregate': sdk_metrics.get('aggregate', {})
        }


# Global enhanced connection manager instance
_enhanced_manager: Optional[EnhancedConnectionManager] = None
_manager_lock = asyncio.Lock()


async def get_connection_manager(env_config = None) -> EnhancedConnectionManager:
    """
    Get global enhanced connection manager instance.
    
    Args:
        env_config: Environment configuration (for compatibility)
        
    Returns:
        EnhancedConnectionManager instance
    """
    global _enhanced_manager
    
    async with _manager_lock:
        if _enhanced_manager is None:
            _enhanced_manager = EnhancedConnectionManager(env_config)
        return _enhanced_manager


@asynccontextmanager
async def get_connection(server_language: Optional[str] = None, 
                        timeout: Optional[float] = None) -> AsyncGenerator[ModernSpacetimeDBClient, None]:
    """
    Convenience function to get a connection.
    
    Args:
        server_language: Server language (rust, python, csharp, go)
        timeout: Connection timeout
        
    Yields:
        ModernSpacetimeDBClient instance (SDK-powered)
    """
    manager = await get_connection_manager()
    async with manager.get_connection(
        server_language=server_language,
        timeout=timeout
    ) as connection:
        yield connection


__all__ = [
    'EnhancedConnectionManager',
    'get_connection_manager',
    'get_connection'
]