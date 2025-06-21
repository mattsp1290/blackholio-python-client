# Blackholio Python Client

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A unified Python client for SpacetimeDB integration across multiple server languages. This package consolidates the duplicate connection logic from `blackholio-agent` and `client-pygame` projects, eliminating ~2,300 lines of duplicate code while providing a robust, production-ready client library.

**🎉 NOW POWERED BY MODERNIZED SPACETIMEDB-PYTHON-SDK** - This client has been successfully migrated to use the enhanced spacetimedb-python-sdk under the hood, providing advanced connection pooling, sophisticated event handling, and production-ready patterns while maintaining full backward compatibility.

## 🚀 Features

### Core Features
- **Multi-Server Language Support**: Seamlessly connect to Rust, Python, C#, and Go SpacetimeDB servers
- **Environment Variable Configuration**: Easy server switching via environment variables
- **Unified Data Models**: Consistent game entity representations across all implementations
- **Async/Await Support**: Modern Python async programming patterns
- **Docker Compatible**: Designed for containerized deployments
- **Type Safety**: Full type hints and mypy compatibility

### Enhanced SDK Features ✨
- **Advanced Connection Pooling**: Production-ready connection management with health monitoring
- **Sophisticated Event System**: Priority-based event handling with filtering and middleware
- **Circuit Breaker Pattern**: Automatic failure protection and recovery
- **Comprehensive Monitoring**: Built-in metrics, performance tracking, and diagnostics
- **Optimization Profiles**: Configurable performance tuning for different use cases
- **Backward Compatibility**: All existing APIs preserved while adding new capabilities

## 📦 Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/blackholio/blackholio-python-client.git
```

### Development Installation

```bash
git clone https://github.com/blackholio/blackholio-python-client.git
cd blackholio-python-client
pip install -e ".[dev]"
```

## 🏃 Quick Start

### Basic Usage

```python
import asyncio
from blackholio_client import create_game_client, Vector2

async def main():
    # Create client (automatically configures from environment variables)
    client = create_game_client()
    
    # Join game (handles connection + subscription + entry)
    await client.join_game("MyPlayer")
    
    # Update player movement
    direction = Vector2(1.0, 0.0)  # Move right
    await client.move_player(direction)
    
    # Get game state
    entities = client.get_all_entities()
    players = client.get_all_players()
    my_player = client.get_local_player()
    
    print(f"Connected! Found {len(entities)} entities and {len(players)} players")
    
    # Graceful shutdown
    await client.shutdown()

# Run the example
asyncio.run(main())
```

### Environment Configuration

Configure the client using environment variables:

```bash
# Server configuration
export SERVER_LANGUAGE=rust          # rust, python, csharp, go
export SERVER_IP=localhost           # Server IP address
export SERVER_PORT=3000             # Server port
export SERVER_USE_SSL=false         # Use SSL/TLS

# SpacetimeDB configuration
export SPACETIME_DB_IDENTITY=blackholio_rust
export SPACETIME_PROTOCOL=v1.json.spacetimedb

# Connection settings
export CONNECTION_TIMEOUT=30.0
export RECONNECT_ATTEMPTS=5
export RECONNECT_DELAY=2.0

# Logging
export LOG_LEVEL=INFO
export DEBUG_MODE=false
```

### Server Language Switching

```python
# Modern unified API (recommended)
from blackholio_client import create_game_client

# Connect to different server languages
rust_client = create_game_client(server_language="rust")
python_client = create_game_client(server_language="python")
csharp_client = create_game_client(server_language="csharp")
go_client = create_game_client(server_language="go")

# Legacy API (still supported)
from blackholio_client import BlackholioClient
legacy_client = BlackholioClient(server_language="rust")
```

## 🏗️ Architecture

### Package Structure

```
blackholio_client/
├── connection/          # SpacetimeDB connection management
│   ├── spacetimedb_connection.py
│   ├── server_config.py
│   └── protocol_handlers.py
├── models/             # Unified data models
│   ├── game_entities.py
│   └── data_converters.py
├── config/             # Configuration management
│   ├── environment.py
│   └── server_profiles.py
├── utils/              # Utility functions
│   ├── async_helpers.py
│   └── logging_config.py
└── exceptions/         # Custom exceptions
    └── connection_errors.py
```

### Key Components

- **BlackholioClient**: High-level client interface
- **SpacetimeDBConnection**: Low-level connection management
- **ServerConfig**: Server configuration and validation
- **GameEntity/GamePlayer/GameCircle**: Unified data models
- **EnvironmentConfig**: Environment variable management

## 🔧 Advanced Usage

### Event Handling

```python
async def on_player_update(data):
    print(f"Player updated: {data}")

async def on_entity_update(data):
    print(f"Entity updated: {data}")

client = BlackholioClient()
client.on('player_update', on_player_update)
client.on('entity_update', on_entity_update)

await client.connect()
```

### Custom Configuration

```python
from blackholio_client import BlackholioClient, ServerConfig

# Custom server configuration
config = ServerConfig(
    language="rust",
    host="game-server.example.com:3000",
    db_identity="production_game",
    protocol="v1.json.spacetimedb",
    use_ssl=True
)

client = BlackholioClient()
client.connection.config = config
```

### Error Handling

```python
from blackholio_client import BlackholioClient
from blackholio_client.exceptions import (
    BlackholioConnectionError,
    ServerConfigurationError,
    TimeoutError
)

try:
    client = BlackholioClient()
    await client.connect()
except ServerConfigurationError as e:
    print(f"Configuration error: {e}")
except TimeoutError as e:
    print(f"Connection timeout: {e}")
except BlackholioConnectionError as e:
    print(f"Connection error: {e}")
```

## 🐳 Docker Usage

### Environment Variables in Docker

```dockerfile
FROM python:3.11-slim

# Install the package
RUN pip install git+https://github.com/blackholio/blackholio-python-client.git

# Set environment variables
ENV SERVER_LANGUAGE=rust
ENV SERVER_IP=blackholio-server
ENV SERVER_PORT=3000
ENV SPACETIME_DB_IDENTITY=blackholio_production

COPY your_app.py .
CMD ["python", "your_app.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  game-client:
    build: .
    environment:
      - SERVER_LANGUAGE=rust
      - SERVER_IP=blackholio-server
      - SERVER_PORT=3000
      - LOG_LEVEL=INFO
    depends_on:
      - blackholio-server
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=blackholio_client --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

## 🔍 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/blackholio/blackholio-python-client.git
cd blackholio-python-client

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src tests
isort src tests

# Run type checking
mypy src

# Run linting
flake8 src tests
```

### Project Structure

The project follows modern Python packaging best practices:

- **src/ layout**: Package code in `src/blackholio_client/`
- **pyproject.toml**: Modern Python packaging configuration
- **Type hints**: Full type annotation coverage
- **Async/await**: Modern async programming patterns
- **Comprehensive testing**: Unit, integration, and end-to-end tests

## 📚 Migration Guide

### From blackholio-agent

```python
# Old code
from blackholio_agent.environment.blackholio_connection_v112 import BlackholioConnectionV112
from blackholio_agent.environment.data_converter import DataConverter

connection = BlackholioConnectionV112()
await connection.connect()

# New code
from blackholio_client import BlackholioClient

client = BlackholioClient()
await client.connect()
```

### From client-pygame

```python
# Old code
from spacetimedb_adapter import SpacetimeDBAdapter
from spacetimedb_data_converter import extract_entity_data

adapter = SpacetimeDBAdapter()
await adapter.connect()

# New code
from blackholio_client import BlackholioClient

client = BlackholioClient()
await client.connect()
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- **blackholio-agent**: ML agent implementation using this client
- **client-pygame**: Pygame client implementation using this client
- **SpacetimeDB**: The database platform this client connects to

## 📚 Documentation

### Complete Documentation

- **[📖 API Reference](docs/API_REFERENCE.md)** - Complete API documentation with examples
- **[🚀 Installation Guide](docs/INSTALLATION.md)** - Installation and deployment for all environments
- **[🔧 Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[🏗️ Development Guide](DEVELOPMENT.md)** - Contributing and development setup

### Usage Examples

- **[🏃 Basic Usage](src/blackholio_client/examples/basic_usage.py)** - Getting started examples
- **[🔄 Migration Examples](src/blackholio_client/examples/migration_examples.py)** - Migrate from legacy implementations
- **[⚙️ Environment Configuration](src/blackholio_client/examples/environment_config_examples.py)** - All server languages and Docker
- **[🎯 Event System](src/blackholio_client/examples/event_system_examples.py)** - Event-driven programming patterns
- **[📊 Data Models](src/blackholio_client/examples/data_models_examples.py)** - Working with game entities and serialization
- **[🚀 Advanced Usage](src/blackholio_client/examples/advanced_usage_examples.py)** - Production patterns, monitoring, performance

### Architecture Documentation

- **[🏗️ Architecture Decisions](proompts/docs/architecture-decisions.md)** - Technical design decisions and patterns
- **[📊 Codebase Analysis](proompts/docs/codebase-analysis.md)** - Analysis of original implementations and consolidation strategy

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/blackholio/blackholio-python-client/issues)
- **Documentation**: Complete guides available in the `docs/` directory
- **Examples**: Comprehensive examples in `src/blackholio_client/examples/`

## 🎯 Roadmap

- [ ] WebRTC support for peer-to-peer connections
- [ ] GraphQL subscription support
- [ ] Built-in metrics and monitoring
- [ ] Plugin system for custom protocols
- [ ] CLI tools for debugging and testing

---

**Built with ❤️ by the Elite Engineering Team**

*Eliminating code duplication, one package at a time.* 🚀
