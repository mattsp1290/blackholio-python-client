# Docker Deployment Guide for blackholio-python-client

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Docker Configuration](#docker-configuration)
- [Environment Variables](#environment-variables)
- [Multi-Server Language Support](#multi-server-language-support)
- [Production Deployment](#production-deployment)
- [Development with Docker](#development-with-docker)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Overview

The blackholio-python-client package is fully containerized and supports deployment in Docker environments with comprehensive environment variable configuration for all four SpacetimeDB server languages (Rust, Python, C#, Go).

### Key Features
- 🐳 Multi-stage Dockerfile for optimized images
- 🔧 Environment variable configuration for all settings
- 🌍 Support for all SpacetimeDB server languages
- 🚀 Production-ready container configuration
- 🧪 Integrated testing in containers
- 📊 Health checks and monitoring support

## Quick Start

### 1. Build the Docker Image
```bash
# Build development image
docker build -t blackholio-python-client:dev --target development .

# Build production image
docker build -t blackholio-python-client:latest --target production .
```

### 2. Run with Docker Compose
```bash
# Run tests for all server languages
docker-compose up

# Run specific server language tests
docker-compose run test-rust
docker-compose run test-python
docker-compose run test-csharp
docker-compose run test-go
```

### 3. Run Standalone Container
```bash
# Run with Rust server (default)
docker run --rm \
  -e SERVER_LANGUAGE=rust \
  -e SERVER_IP=spacetimedb.example.com \
  -e SERVER_PORT=8080 \
  blackholio-python-client:latest

# Run with Python server
docker run --rm \
  -e SERVER_LANGUAGE=python \
  -e SERVER_IP=spacetimedb-python.example.com \
  -e SERVER_PORT=8081 \
  blackholio-python-client:latest
```

## Docker Configuration

### Multi-Stage Dockerfile

The Dockerfile includes four stages:

1. **base** - Common dependencies and package installation
2. **development** - Development tools and testing
3. **production** - Minimal runtime environment
4. **test-runner** - CI/CD testing environment

### Docker Compose Services

- `test-rust` - Test with Rust server configuration
- `test-python` - Test with Python server configuration
- `test-csharp` - Test with C# server configuration
- `test-go` - Test with Go server configuration
- `test-production` - Production environment validation
- `dev` - Interactive development environment

## Environment Variables

### Core Configuration

| Variable | Description | Default | Values |
|----------|-------------|---------|---------|
| `SERVER_LANGUAGE` | SpacetimeDB server language | `rust` | `rust`, `python`, `csharp`, `go` |
| `SERVER_IP` | Server hostname/IP | `localhost` | Any valid hostname/IP |
| `SERVER_PORT` | Server port | `8080` | Any valid port |

### Advanced Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BLACKHOLIO_LOG_LEVEL` | Logging level | `INFO` |
| `BLACKHOLIO_CONNECTION_TIMEOUT` | Connection timeout (seconds) | `30` |
| `BLACKHOLIO_MAX_RETRIES` | Maximum retry attempts | `3` |
| `BLACKHOLIO_SSL_ENABLED` | Enable SSL/TLS | `false` |
| `BLACKHOLIO_POOL_MIN_SIZE` | Min connection pool size | `1` |
| `BLACKHOLIO_POOL_MAX_SIZE` | Max connection pool size | `10` |
| `BLACKHOLIO_DEBUG` | Enable debug mode | `false` |

## Multi-Server Language Support

### Rust Server Configuration
```yaml
environment:
  - SERVER_LANGUAGE=rust
  - SERVER_IP=spacetimedb-rust
  - SERVER_PORT=8080
  - BLACKHOLIO_USE_BINARY_PROTOCOL=true
```

### Python Server Configuration
```yaml
environment:
  - SERVER_LANGUAGE=python
  - SERVER_IP=spacetimedb-python
  - SERVER_PORT=8081
  - BLACKHOLIO_PREFER_JSON=true
```

### C# Server Configuration
```yaml
environment:
  - SERVER_LANGUAGE=csharp
  - SERVER_IP=spacetimedb-csharp
  - SERVER_PORT=8082
  - BLACKHOLIO_USE_PASCAL_CASE=true
```

### Go Server Configuration
```yaml
environment:
  - SERVER_LANGUAGE=go
  - SERVER_IP=spacetimedb-go
  - SERVER_PORT=8083
  - BLACKHOLIO_USE_CAMEL_CASE=true
```

## Production Deployment

### Docker Compose Production
```bash
# Deploy with production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale the service
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale blackholio-client=3
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blackholio-client
spec:
  replicas: 3
  selector:
    matchLabels:
      app: blackholio-client
  template:
    metadata:
      labels:
        app: blackholio-client
    spec:
      containers:
      - name: blackholio-client
        image: blackholio/python-client:latest
        env:
        - name: SERVER_LANGUAGE
          value: "rust"
        - name: SERVER_IP
          value: "spacetimedb-service"
        - name: SERVER_PORT
          value: "443"
        - name: BLACKHOLIO_SSL_ENABLED
          value: "true"
        resources:
          limits:
            memory: "512Mi"
            cpu: "1000m"
          requests:
            memory: "128Mi"
            cpu: "250m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "from blackholio_client import create_game_client; print('healthy')"
          initialDelaySeconds: 30
          periodSeconds: 30
```

### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml blackholio

# Scale service
docker service scale blackholio_blackholio-client=5
```

## Development with Docker

### Interactive Development Container
```bash
# Launch interactive shell
docker-compose run --rm dev

# Or use the helper script
./docker-test.sh shell
```

### Live Code Reload
```yaml
# docker-compose.override.yml enables live reload
services:
  dev:
    volumes:
      - .:/app  # Mount entire project
      - /app/.venv  # Exclude virtual environment
```

### Running Tests in Container
```bash
# Run all tests
docker-compose run --rm dev pytest

# Run specific test
docker-compose run --rm dev pytest tests/test_config.py

# Run with coverage
docker-compose run --rm dev pytest --cov=blackholio_client
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Docker Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        server-language: [rust, python, csharp, go]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t blackholio-test --target test-runner .
    
    - name: Run tests
      run: |
        docker run --rm \
          -e SERVER_LANGUAGE=${{ matrix.server-language }} \
          -v $PWD/test-results:/app/test-results \
          blackholio-test
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results-${{ matrix.server-language }}
        path: test-results/
```

### GitLab CI
```yaml
stages:
  - build
  - test
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

build:
  stage: build
  script:
    - docker build -t $DOCKER_IMAGE .
    - docker push $DOCKER_IMAGE

test:
  stage: test
  parallel:
    matrix:
      - SERVER_LANGUAGE: [rust, python, csharp, go]
  script:
    - docker run --rm -e SERVER_LANGUAGE=$SERVER_LANGUAGE $DOCKER_IMAGE pytest

deploy:
  stage: deploy
  script:
    - docker tag $DOCKER_IMAGE $CI_REGISTRY_IMAGE:latest
    - docker push $CI_REGISTRY_IMAGE:latest
  only:
    - main
```

## Troubleshooting

### Common Issues

#### 1. Container fails to start
```bash
# Check logs
docker logs <container-id>

# Verify environment variables
docker exec <container-id> env | grep -E "(SERVER_|BLACKHOLIO_)"
```

#### 2. Connection errors
```bash
# Test connectivity from container
docker run --rm --network container:<container-id> nicolaka/netshoot \
  nc -zv $SERVER_IP $SERVER_PORT
```

#### 3. Package import errors
```bash
# Verify package installation
docker run --rm blackholio-python-client:latest \
  python -c "import blackholio_client; print(blackholio_client.__version__)"
```

### Debugging Commands

```bash
# Run validation script
docker run --rm \
  -e DOCKER_CONTAINER=true \
  -v $(pwd)/test-results:/app/test-results \
  blackholio-python-client:latest \
  python tests/test_docker_validation.py

# Check container health
docker inspect <container-id> --format='{{.State.Health.Status}}'

# View resource usage
docker stats <container-id>
```

### Performance Optimization

1. **Use multi-stage builds** to minimize image size
2. **Cache dependencies** in separate layers
3. **Set resource limits** to prevent container sprawl
4. **Use health checks** for automatic recovery
5. **Enable connection pooling** for better performance

## Best Practices

1. **Always specify SERVER_LANGUAGE** explicitly in production
2. **Use secrets management** for sensitive configuration
3. **Enable SSL/TLS** for production deployments
4. **Set appropriate resource limits** based on load
5. **Implement proper logging** with centralized collection
6. **Use health checks** for container orchestration
7. **Version your images** with semantic versioning
8. **Test all server languages** in CI/CD pipeline

## Conclusion

The blackholio-python-client is fully Docker-compatible and production-ready for containerized deployments. With support for all SpacetimeDB server languages and comprehensive environment variable configuration, it can be deployed in any container orchestration platform.

For more information, see:
- [Installation Guide](INSTALLATION.md)
- [API Reference](API_REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)