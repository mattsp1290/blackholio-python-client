"""Factory pattern implementation for SpacetimeDB client instantiation.

This module provides a factory pattern implementation that enables dynamic
instantiation of SpacetimeDB clients based on the configured server language.
The factory pattern abstracts away the complexity of client generation and
loading, providing a simple interface for creating clients that work with
any supported SpacetimeDB server implementation.

Key components:
- ClientFactory: Abstract base class defining the factory interface
- Language-specific factories: Concrete implementations for each server language
- ClientFactoryRegistry: Registry for managing available factories
- create_client: High-level function for creating clients based on configuration
"""

from .base import ClientFactory, ClientFactoryBase
from .registry import ClientFactoryRegistry
from .rust_factory import RustClientFactory
from .python_factory import PythonClientFactory
from .csharp_factory import CSharpClientFactory
from .go_factory import GoClientFactory
from .client_factory import (
    create_client, 
    get_client_factory,
    list_available_languages,
    get_factory_info,
    create_all_available_clients
)

__all__ = [
    "ClientFactory",
    "ClientFactoryBase",
    "ClientFactoryRegistry",
    "RustClientFactory",
    "PythonClientFactory",
    "CSharpClientFactory",
    "GoClientFactory",
    "create_client",
    "get_client_factory",
    "list_available_languages",
    "get_factory_info",
    "create_all_available_clients",
]