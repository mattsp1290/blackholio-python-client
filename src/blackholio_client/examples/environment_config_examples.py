"""
Environment Configuration Examples for Blackholio Python Client.

Demonstrates comprehensive environment variable configuration patterns
for all supported SpacetimeDB server languages (Rust, Python, C#, Go)
and deployment scenarios including Docker containers.
"""

import asyncio
import os
import logging
from typing import Dict, Any, List

from ..client import create_game_client, GameClient
from ..config.environment import EnvironmentConfig
from ..models.game_entities import Vector2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rust_server_configuration():
    """
    Configure client for Rust SpacetimeDB server.
    
    Rust servers are the default and most optimized implementation.
    """
    print("\n=== Rust Server Configuration ===")
    
    # Environment variables for Rust server
    rust_config = {
        'SERVER_LANGUAGE': 'rust',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '3000',
        'SERVER_USE_SSL': 'false',
        'SPACETIME_DB_IDENTITY': 'blackholio_rust',
        'SPACETIME_PROTOCOL': 'v1.binary.spacetimedb',  # Rust prefers binary
        'CONNECTION_TIMEOUT': '30.0',
        'RECONNECT_ATTEMPTS': '5',
        'RECONNECT_DELAY': '2.0',
        'LOG_LEVEL': 'INFO'
    }
    
    print("Environment variables for Rust server:")
    for key, value in rust_config.items():
        print(f"  export {key}={value}")
        os.environ[key] = value
    
    print("\nDocker compose configuration:")
    print("""
    version: '3.8'
    services:
      blackholio-client:
        image: blackholio-python-client:latest
        environment:
          - SERVER_LANGUAGE=rust
          - SERVER_IP=rust-server
          - SERVER_PORT=3000
          - SERVER_USE_SSL=false
          - SPACETIME_DB_IDENTITY=blackholio_rust
          - SPACETIME_PROTOCOL=v1.binary.spacetimedb
        depends_on:
          - rust-server
    """)
    
    # Create client using environment configuration
    client = create_game_client()  # Uses environment variables automatically
    
    print(f"\n✅ Rust client configured:")
    print(f"  Connection info: {client.get_connection_info()}")
    
    return client


def python_server_configuration():
    """
    Configure client for Python SpacetimeDB server.
    
    Python servers offer good performance with easy debugging.
    """
    print("\n=== Python Server Configuration ===")
    
    # Environment variables for Python server
    python_config = {
        'SERVER_LANGUAGE': 'python',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '3001',
        'SERVER_USE_SSL': 'false',
        'SPACETIME_DB_IDENTITY': 'blackholio_python',
        'SPACETIME_PROTOCOL': 'v1.json.spacetimedb',  # Python prefers JSON
        'CONNECTION_TIMEOUT': '45.0',  # Python may need more time
        'RECONNECT_ATTEMPTS': '3',
        'RECONNECT_DELAY': '3.0',
        'PYTHON_VENV_PATH': '/opt/venv',  # Python-specific setting
        'LOG_LEVEL': 'DEBUG'  # Python debugging
    }
    
    print("Environment variables for Python server:")
    for key, value in python_config.items():
        print(f"  export {key}={value}")
        os.environ[key] = value
    
    print("\nKubernetes deployment configuration:")
    print("""
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: blackholio-client-python
    spec:
      template:
        spec:
          containers:
          - name: client
            image: blackholio-python-client:latest
            env:
            - name: SERVER_LANGUAGE
              value: "python"
            - name: SERVER_IP
              valueFrom:
                configMapKeyRef:
                  name: server-config
                  key: python-server-ip
            - name: SERVER_PORT
              value: "3001"
            - name: SPACETIME_DB_IDENTITY
              value: "blackholio_python"
    """)
    
    client = create_game_client()
    
    print(f"\n✅ Python client configured:")
    print(f"  Connection info: {client.get_connection_info()}")
    
    return client


def csharp_server_configuration():
    """
    Configure client for C# SpacetimeDB server.
    
    C# servers provide excellent performance and .NET integration.
    """
    print("\n=== C# Server Configuration ===")
    
    # Environment variables for C# server
    csharp_config = {
        'SERVER_LANGUAGE': 'csharp',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '3002',
        'SERVER_USE_SSL': 'true',  # C# often uses SSL
        'SPACETIME_DB_IDENTITY': 'blackholio_csharp',
        'SPACETIME_PROTOCOL': 'v1.json.spacetimedb',
        'CONNECTION_TIMEOUT': '25.0',
        'RECONNECT_ATTEMPTS': '7',
        'RECONNECT_DELAY': '1.5',
        'DOTNET_RUNTIME_VERSION': '6.0',  # C#-specific setting
        'SSL_CERT_PATH': '/certs/server.crt',
        'LOG_LEVEL': 'INFO'
    }
    
    print("Environment variables for C# server:")
    for key, value in csharp_config.items():
        print(f"  export {key}={value}")
        os.environ[key] = value
    
    print("\nAWS ECS task definition configuration:")
    print("""
    {
      "family": "blackholio-client-csharp",
      "containerDefinitions": [
        {
          "name": "client",
          "image": "blackholio-python-client:latest",
          "environment": [
            {"name": "SERVER_LANGUAGE", "value": "csharp"},
            {"name": "SERVER_IP", "value": "csharp-server.internal"},
            {"name": "SERVER_PORT", "value": "3002"},
            {"name": "SERVER_USE_SSL", "value": "true"},
            {"name": "SPACETIME_DB_IDENTITY", "value": "blackholio_csharp"},
            {"name": "SSL_CERT_PATH", "value": "/certs/server.crt"}
          ]
        }
      ]
    }
    """)
    
    client = create_game_client()
    
    print(f"\n✅ C# client configured:")
    print(f"  Connection info: {client.get_connection_info()}")
    
    return client


def go_server_configuration():
    """
    Configure client for Go SpacetimeDB server.
    
    Go servers offer excellent concurrency and performance.
    """
    print("\n=== Go Server Configuration ===")
    
    # Environment variables for Go server
    go_config = {
        'SERVER_LANGUAGE': 'go',
        'SERVER_IP': 'localhost',
        'SERVER_PORT': '3003',
        'SERVER_USE_SSL': 'false',
        'SPACETIME_DB_IDENTITY': 'blackholio_go',
        'SPACETIME_PROTOCOL': 'v1.binary.spacetimedb',  # Go prefers binary
        'CONNECTION_TIMEOUT': '20.0',  # Go is fast
        'RECONNECT_ATTEMPTS': '10',  # Go handles connections well
        'RECONNECT_DELAY': '1.0',
        'GO_MAX_PROCS': '4',  # Go-specific setting
        'GO_GC_PERCENT': '100',
        'LOG_LEVEL': 'WARN'
    }
    
    print("Environment variables for Go server:")
    for key, value in go_config.items():
        print(f"  export {key}={value}")
        os.environ[key] = value
    
    print("\nHelm chart values.yaml configuration:")
    print("""
    blackholio-client:
      image:
        repository: blackholio-python-client
        tag: latest
      config:
        serverLanguage: go
        serverIp: go-server-service
        serverPort: 3003
        serverUseSSL: false
        spacetimeDbIdentity: blackholio_go
        spacetimeProtocol: v1.binary.spacetimedb
        connectionTimeout: 20.0
        reconnectAttempts: 10
        logLevel: WARN
      resources:
        limits:
          memory: "256Mi"
          cpu: "200m"
    """)
    
    client = create_game_client()
    
    print(f"\n✅ Go client configured:")
    print(f"  Connection info: {client.get_connection_info()}")
    
    return client


def multi_environment_configuration():
    """
    Demonstrate configuration for multiple environments (dev, staging, prod).
    """
    print("\n=== Multi-Environment Configuration ===")
    
    environments = {
        'development': {
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'localhost',
            'SERVER_PORT': '3000',
            'SERVER_USE_SSL': 'false',
            'LOG_LEVEL': 'DEBUG',
            'DEBUG_MODE': 'true',
            'CONNECTION_TIMEOUT': '60.0',  # Longer timeout for debugging
            'RECONNECT_ATTEMPTS': '1'  # Don't retry during development
        },
        'staging': {
            'SERVER_LANGUAGE': 'python',
            'SERVER_IP': 'staging-server.company.com',
            'SERVER_PORT': '443',
            'SERVER_USE_SSL': 'true',
            'LOG_LEVEL': 'INFO',
            'DEBUG_MODE': 'false',
            'CONNECTION_TIMEOUT': '30.0',
            'RECONNECT_ATTEMPTS': '5',
            'SSL_VERIFY': 'true'
        },
        'production': {
            'SERVER_LANGUAGE': 'rust',
            'SERVER_IP': 'prod-server.company.com',
            'SERVER_PORT': '443',
            'SERVER_USE_SSL': 'true',
            'LOG_LEVEL': 'WARN',
            'DEBUG_MODE': 'false',
            'CONNECTION_TIMEOUT': '15.0',
            'RECONNECT_ATTEMPTS': '10',
            'SSL_VERIFY': 'true',
            'METRICS_ENABLED': 'true',
            'HEALTH_CHECK_INTERVAL': '30'
        }
    }
    
    # Demonstrate environment-specific configuration
    current_env = os.getenv('ENVIRONMENT', 'development')
    print(f"Configuring for environment: {current_env}")
    
    if current_env in environments:
        config = environments[current_env]
        print(f"\nConfiguration for {current_env}:")
        for key, value in config.items():
            print(f"  {key}={value}")
            os.environ[key] = value
    
    print(f"\n.env file example for {current_env}:")
    print("# Blackholio Client Configuration")
    print(f"ENVIRONMENT={current_env}")
    for key, value in environments[current_env].items():
        print(f"{key}={value}")
    
    client = create_game_client()
    
    print(f"\n✅ {current_env.title()} client configured:")
    print(f"  Connection info: {client.get_connection_info()}")
    
    return client


def docker_compose_full_configuration():
    """
    Provide complete Docker Compose configuration for all server languages.
    """
    print("\n=== Complete Docker Compose Configuration ===")
    
    docker_compose = """
version: '3.8'

services:
  # Rust server and client
  rust-server:
    image: blackholio-rust-server:latest
    ports:
      - "3000:3000"
    environment:
      - RUST_LOG=info
    volumes:
      - ./server-data:/data

  rust-client:
    image: blackholio-python-client:latest
    environment:
      - SERVER_LANGUAGE=rust
      - SERVER_IP=rust-server
      - SERVER_PORT=3000
      - SPACETIME_DB_IDENTITY=blackholio_rust
      - SPACETIME_PROTOCOL=v1.binary.spacetimedb
      - LOG_LEVEL=INFO
    depends_on:
      - rust-server

  # Python server and client
  python-server:
    image: blackholio-python-server:latest
    ports:
      - "3001:3001"
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
    volumes:
      - ./server-data:/data

  python-client:
    image: blackholio-python-client:latest
    environment:
      - SERVER_LANGUAGE=python
      - SERVER_IP=python-server
      - SERVER_PORT=3001
      - SPACETIME_DB_IDENTITY=blackholio_python
      - SPACETIME_PROTOCOL=v1.json.spacetimedb
      - LOG_LEVEL=DEBUG
    depends_on:
      - python-server

  # C# server and client
  csharp-server:
    image: blackholio-csharp-server:latest
    ports:
      - "3002:3002"
      - "443:443"
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - ASPNETCORE_URLS=https://+:443;http://+:3002
    volumes:
      - ./certs:/certs
      - ./server-data:/data

  csharp-client:
    image: blackholio-python-client:latest
    environment:
      - SERVER_LANGUAGE=csharp
      - SERVER_IP=csharp-server
      - SERVER_PORT=443
      - SERVER_USE_SSL=true
      - SPACETIME_DB_IDENTITY=blackholio_csharp
      - SSL_CERT_PATH=/certs/server.crt
      - LOG_LEVEL=INFO
    volumes:
      - ./certs:/certs
    depends_on:
      - csharp-server

  # Go server and client
  go-server:
    image: blackholio-go-server:latest
    ports:
      - "3003:3003"
    environment:
      - GO_ENV=production
      - GOMAXPROCS=4
    volumes:
      - ./server-data:/data

  go-client:
    image: blackholio-python-client:latest
    environment:
      - SERVER_LANGUAGE=go
      - SERVER_IP=go-server
      - SERVER_PORT=3003
      - SPACETIME_DB_IDENTITY=blackholio_go
      - SPACETIME_PROTOCOL=v1.binary.spacetimedb
      - GO_MAX_PROCS=2
      - LOG_LEVEL=WARN
    depends_on:
      - go-server

  # Load balancer for multi-server setup
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/certs
    depends_on:
      - rust-server
      - python-server
      - csharp-server
      - go-server

volumes:
  server-data:
  certs:

networks:
  default:
    driver: bridge
"""
    
    print("Complete docker-compose.yml:")
    print(docker_compose)
    
    print("\nTo run specific server/client combinations:")
    print("  docker-compose up rust-server rust-client")
    print("  docker-compose up python-server python-client")
    print("  docker-compose up csharp-server csharp-client")
    print("  docker-compose up go-server go-client")
    print("\nTo run all servers:")
    print("  docker-compose up")


async def test_configuration_switching():
    """
    Demonstrate dynamic configuration switching between server languages.
    """
    print("\n=== Dynamic Configuration Switching Test ===")
    
    server_configs = [
        {'name': 'Rust', 'language': 'rust', 'port': 3000},
        {'name': 'Python', 'language': 'python', 'port': 3001},
        {'name': 'C#', 'language': 'csharp', 'port': 3002},
        {'name': 'Go', 'language': 'go', 'port': 3003}
    ]
    
    successful_connections = []
    
    for config in server_configs:
        print(f"\n--- Testing {config['name']} Server Configuration ---")
        
        # Set environment for this server
        os.environ['SERVER_LANGUAGE'] = config['language']
        os.environ['SERVER_IP'] = 'localhost'
        os.environ['SERVER_PORT'] = str(config['port'])
        os.environ['SPACETIME_DB_IDENTITY'] = f"blackholio"
        
        # Create client with new configuration
        client = create_game_client()
        
        try:
            # Test connection (with short timeout for demo)
            print(f"Attempting connection to {config['name']} server...")
            
            # Note: In a real test, you would actually connect
            # For this example, we'll simulate the connection test
            connection_info = client.get_connection_info()
            print(f"✅ {config['name']} configuration valid:")
            print(f"  Server: {connection_info['host']}")
            print(f"  Language: {connection_info['server_language']}")
            print(f"  Protocol: {connection_info.get('protocol', 'default')}")
            
            successful_connections.append(config['name'])
            
        except Exception as e:
            print(f"❌ {config['name']} configuration error: {e}")
        
        finally:
            await client.shutdown()
    
    print(f"\n📊 Configuration Test Results:")
    print(f"  Successful configurations: {len(successful_connections)}/{len(server_configs)}")
    if successful_connections:
        print(f"  Working servers: {', '.join(successful_connections)}")


def environment_validation_example():
    """
    Demonstrate environment variable validation and error handling.
    """
    print("\n=== Environment Variable Validation ===")
    
    # Test with invalid configuration
    invalid_configs = [
        {
            'name': 'Invalid Server Language',
            'config': {'SERVER_LANGUAGE': 'invalid_language'},
            'expected_error': 'Unsupported server language'
        },
        {
            'name': 'Invalid Port',
            'config': {'SERVER_PORT': 'not_a_number'},
            'expected_error': 'Invalid port number'
        },
        {
            'name': 'Invalid Timeout',
            'config': {'CONNECTION_TIMEOUT': '-5.0'},
            'expected_error': 'Timeout must be positive'
        },
        {
            'name': 'Missing Required Config',
            'config': {'SERVER_IP': ''},
            'expected_error': 'Server IP is required'
        }
    ]
    
    for test_case in invalid_configs:
        print(f"\n--- Testing {test_case['name']} ---")
        
        # Set invalid configuration
        original_values = {}
        for key, value in test_case['config'].items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # This should raise validation errors
            config = EnvironmentConfig()
            print(f"❌ Expected validation error for {test_case['name']}")
            
        except Exception as e:
            print(f"✅ Caught expected error: {e}")
        
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is not None:
                    os.environ[key] = original_value
                elif key in os.environ:
                    del os.environ[key]
    
    print("\n✅ Environment validation working correctly!")


async def run_all_configuration_examples():
    """Run all configuration examples."""
    print("🚀 Running all environment configuration examples...")
    
    # Server-specific configurations
    rust_client = rust_server_configuration()
    await rust_client.shutdown()
    
    python_client = python_server_configuration()
    await python_client.shutdown()
    
    csharp_client = csharp_server_configuration()
    await csharp_client.shutdown()
    
    go_client = go_server_configuration()
    await go_client.shutdown()
    
    # Multi-environment configuration
    multi_env_client = multi_environment_configuration()
    await multi_env_client.shutdown()
    
    # Docker configuration
    docker_compose_full_configuration()
    
    # Dynamic switching test
    await test_configuration_switching()
    
    # Validation examples
    environment_validation_example()
    
    print("\n✅ All environment configuration examples completed!")


if __name__ == "__main__":
    # Run examples when script is executed directly
    asyncio.run(run_all_configuration_examples())