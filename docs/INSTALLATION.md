# Installation and Deployment Guide

Complete guide for installing, configuring, and deploying the Blackholio Python Client in various environments.

## Table of Contents

- [Quick Installation](#quick-installation)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Migration Guide](#migration-guide)
- [Troubleshooting](#troubleshooting)

## Quick Installation

### Install from GitHub

```bash
# Install latest stable version
pip install git+https://github.com/blackholio/blackholio-python-client.git

# Install specific version
pip install git+https://github.com/blackholio/blackholio-python-client.git@v0.1.0

# Install with optional dependencies
pip install "git+https://github.com/blackholio/blackholio-python-client.git[dev,performance]"
```

### Verify Installation

```python
import blackholio_client

# Check version
print(f"Blackholio Client version: {blackholio_client.__version__}")

# Test basic import
from blackholio_client import create_game_client
client = create_game_client()
print("✅ Installation successful!")
```

### System Requirements

- **Python**: 3.8+ (3.10+ recommended for best performance)
- **Operating System**: Linux, macOS, Windows
- **Memory**: 256MB minimum, 512MB recommended
- **Network**: Internet connection for SpacetimeDB servers

## Development Setup

### Clone and Install

```bash
# Clone repository
git clone https://github.com/blackholio/blackholio-python-client.git
cd blackholio-python-client

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Development Dependencies

The development installation includes:

- **Testing**: pytest, pytest-asyncio, pytest-cov, pytest-mock
- **Code Quality**: black, flake8, isort, mypy, pylint, bandit
- **Performance**: memory-profiler, py-spy
- **Documentation**: sphinx, mkdocs
- **Security**: safety, detect-secrets

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test categories
pytest -m "not integration"  # Unit tests only
pytest -m integration        # Integration tests only
pytest -m performance        # Performance tests only
```

### Development Commands

```bash
# Code formatting
make format

# Linting
make lint

# Type checking
make typecheck

# Security scan
make security

# Full quality check
make quality

# Build package
make build

# Clean build artifacts
make clean
```

## Production Deployment

### Production Installation

```bash
# Install production dependencies only
pip install git+https://github.com/blackholio/blackholio-python-client.git

# For high-performance production
pip install "git+https://github.com/blackholio/blackholio-python-client.git[performance]"
```

### Production Configuration

Create a production configuration file:

```bash
# /etc/blackholio/production.env
SERVER_LANGUAGE=rust
SERVER_IP=production-server.company.com
SERVER_PORT=443
SERVER_USE_SSL=true
SPACETIME_DB_IDENTITY=blackholio_production

# Connection settings
CONNECTION_TIMEOUT=15.0
RECONNECT_ATTEMPTS=10
RECONNECT_DELAY=2.0
ENABLE_AUTO_RECONNECT=true

# Performance settings
CONNECTION_POOL_SIZE=10
MAX_CONCURRENT_OPERATIONS=20
OPERATION_TIMEOUT=5.0

# Logging
LOG_LEVEL=WARN
LOG_FILE=/var/log/blackholio/client.log

# Security
SSL_VERIFY=true
SSL_CERT_PATH=/etc/ssl/certs/blackholio.crt
AUTH_TOKEN_PATH=/var/lib/blackholio/tokens
```

### Systemd Service

Create a systemd service for production deployment:

```ini
# /etc/systemd/system/blackholio-client.service
[Unit]
Description=Blackholio Python Client
After=network.target
Wants=network.target

[Service]
Type=simple
User=blackholio
Group=blackholio
WorkingDirectory=/opt/blackholio
EnvironmentFile=/etc/blackholio/production.env
ExecStart=/opt/blackholio/venv/bin/python -m blackholio_client.production
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/blackholio /var/lib/blackholio

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable blackholio-client
sudo systemctl start blackholio-client

# Check status
sudo systemctl status blackholio-client

# View logs
sudo journalctl -u blackholio-client -f
```

### Load Balancer Configuration

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/blackholio
upstream blackholio_clients {
    least_conn;
    server client1.internal:8080 max_fails=3 fail_timeout=30s;
    server client2.internal:8080 max_fails=3 fail_timeout=30s;
    server client3.internal:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name blackholio-client.company.com;

    location / {
        proxy_pass http://blackholio_clients;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

## Docker Deployment

### Dockerfile

```dockerfile
# Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create user
RUN groupadd -r blackholio && useradd -r -g blackholio blackholio

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install blackholio client
RUN pip install --no-cache-dir git+https://github.com/blackholio/blackholio-python-client.git

# Copy application code
COPY --chown=blackholio:blackholio . .

# Create required directories
RUN mkdir -p /var/log/blackholio /var/lib/blackholio && \
    chown -R blackholio:blackholio /var/log/blackholio /var/lib/blackholio

# Switch to non-root user
USER blackholio

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import blackholio_client; print('healthy')" || exit 1

# Default command
CMD ["python", "-m", "blackholio_client.production"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  blackholio-client:
    build: .
    container_name: blackholio-client
    restart: unless-stopped
    environment:
      - SERVER_LANGUAGE=rust
      - SERVER_IP=rust-server
      - SERVER_PORT=3000
      - SERVER_USE_SSL=false
      - SPACETIME_DB_IDENTITY=blackholio_docker
      - LOG_LEVEL=INFO
    volumes:
      - logs:/var/log/blackholio
      - data:/var/lib/blackholio
    networks:
      - blackholio-network
    depends_on:
      - rust-server
    healthcheck:
      test: ["CMD", "python", "-c", "import blackholio_client; print('healthy')"]
      interval: 30s
      timeout: 10s
      retries: 3

  rust-server:
    image: blackholio-rust-server:latest
    container_name: rust-server
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - RUST_LOG=info
    networks:
      - blackholio-network

  # Multi-server setup
  python-server:
    image: blackholio-python-server:latest
    container_name: python-server
    restart: unless-stopped
    ports:
      - "3001:3001"
    networks:
      - blackholio-network

  python-client:
    build: .
    container_name: python-client
    restart: unless-stopped
    environment:
      - SERVER_LANGUAGE=python
      - SERVER_IP=python-server
      - SERVER_PORT=3001
    volumes:
      - logs:/var/log/blackholio
    networks:
      - blackholio-network
    depends_on:
      - python-server

volumes:
  logs:
  data:

networks:
  blackholio-network:
    driver: bridge
```

### Build and Deploy

```bash
# Build image
docker build -t blackholio-python-client:latest .

# Run with docker-compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f blackholio-client

# Scale clients
docker-compose up -d --scale blackholio-client=3
```

## Kubernetes Deployment

### ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: blackholio-config
  namespace: blackholio
data:
  SERVER_LANGUAGE: "rust"
  SERVER_IP: "rust-server-service"
  SERVER_PORT: "3000"
  SERVER_USE_SSL: "false"
  SPACETIME_DB_IDENTITY: "blackholio_k8s"
  CONNECTION_TIMEOUT: "30.0"
  RECONNECT_ATTEMPTS: "10"
  LOG_LEVEL: "INFO"
```

### Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: blackholio-secret
  namespace: blackholio
type: Opaque
data:
  # Base64 encoded values
  auth-token: <base64-encoded-token>
  ssl-cert: <base64-encoded-cert>
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blackholio-client
  namespace: blackholio
  labels:
    app: blackholio-client
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
        image: blackholio-python-client:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: blackholio-config
        - secretRef:
            name: blackholio-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import blackholio_client; print('healthy')"
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import blackholio_client; print('ready')"
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: logs
          mountPath: /var/log/blackholio
        - name: data
          mountPath: /var/lib/blackholio
      volumes:
      - name: logs
        emptyDir: {}
      - name: data
        persistentVolumeClaim:
          claimName: blackholio-data-pvc
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: blackholio-client-service
  namespace: blackholio
spec:
  selector:
    app: blackholio-client
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### HorizontalPodAutoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: blackholio-client-hpa
  namespace: blackholio
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: blackholio-client
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace blackholio

# Apply configurations
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n blackholio
kubectl get services -n blackholio

# View logs
kubectl logs -f deployment/blackholio-client -n blackholio

# Scale deployment
kubectl scale deployment/blackholio-client --replicas=5 -n blackholio
```

## Environment Configuration

### Environment Files

#### Development (.env.development)

```bash
# Development environment
ENVIRONMENT=development
SERVER_LANGUAGE=rust
SERVER_IP=localhost
SERVER_PORT=3000
SERVER_USE_SSL=false
SPACETIME_DB_IDENTITY=blackholio_dev
CONNECTION_TIMEOUT=60.0
RECONNECT_ATTEMPTS=3
LOG_LEVEL=DEBUG
DEBUG_MODE=true
DEVELOPMENT_MODE=true
MOCK_SERVERS=true
```

#### Staging (.env.staging)

```bash
# Staging environment
ENVIRONMENT=staging
SERVER_LANGUAGE=python
SERVER_IP=staging-server.company.com
SERVER_PORT=443
SERVER_USE_SSL=true
SPACETIME_DB_IDENTITY=blackholio_staging
CONNECTION_TIMEOUT=30.0
RECONNECT_ATTEMPTS=5
LOG_LEVEL=INFO
DEBUG_MODE=false
SSL_VERIFY=true
METRICS_ENABLED=true
```

#### Production (.env.production)

```bash
# Production environment
ENVIRONMENT=production
SERVER_LANGUAGE=rust
SERVER_IP=prod-server.company.com
SERVER_PORT=443
SERVER_USE_SSL=true
SPACETIME_DB_IDENTITY=blackholio_production
CONNECTION_TIMEOUT=15.0
RECONNECT_ATTEMPTS=10
LOG_LEVEL=WARN
DEBUG_MODE=false
SSL_VERIFY=true
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=60
CONNECTION_POOL_SIZE=20
```

### Loading Environment Files

```python
from dotenv import load_dotenv
import os

# Load environment-specific configuration
env = os.getenv('ENVIRONMENT', 'development')
load_dotenv(f'.env.{env}')

# Create client with environment configuration
from blackholio_client import create_game_client
client = create_game_client()
```

## Migration Guide

### From blackholio-agent

1. **Replace Connection Class**
   ```python
   # OLD
   from blackholio_connection_v112 import BlackholioConnectionV112
   connection = BlackholioConnectionV112(host="localhost:3000")
   
   # NEW
   from blackholio_client import create_game_client
   client = create_game_client(host="localhost:3000")
   ```

2. **Update Game Operations**
   ```python
   # OLD
   await connection.connect()
   await connection._subscribe_to_tables()
   await connection.call_reducer("enter_game", {"name": "Player"})
   
   # NEW
   await client.join_game("Player")  # Handles connection + subscription + enter
   ```

3. **Update Data Access**
   ```python
   # OLD
   entities = connection._entities
   my_player = connection._local_player_id
   
   # NEW
   entities = client.get_all_entities()
   my_player = client.get_local_player()
   ```

### From client-pygame

1. **Replace Client Initialization**
   ```python
   # OLD
   class GameClient:
       def __init__(self):
           self.connection = SpacetimeConnection("ws://localhost:3000")
   
   # NEW
   class GameClient:
       def __init__(self):
           self.client = create_game_client(host="localhost:3000")
   ```

2. **Update Event Handling**
   ```python
   # OLD
   # Manual polling for changes
   
   # NEW
   self.client.on_entity_created(self.on_entity_created)
   self.client.on_entity_updated(self.on_entity_updated)
   ```

### Migration Script

```python
# migration_helper.py
import os
import re

def migrate_blackholio_agent_imports(file_path):
    """Migrate blackholio-agent imports to unified client."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace imports
    content = re.sub(
        r'from blackholio_connection_v112 import BlackholioConnectionV112',
        'from blackholio_client import create_game_client',
        content
    )
    
    # Replace connection creation
    content = re.sub(
        r'BlackholioConnectionV112\((.*?)\)',
        r'create_game_client(\1)',
        content
    )
    
    # Replace common patterns
    replacements = {
        'connection.connect()': 'client.connect()',
        'connection._entities': 'client.get_all_entities()',
        'connection._players': 'client.get_all_players()',
        'connection._local_player_id': 'client.get_local_player().player_id',
        'connection.call_reducer("enter_game"': 'client.join_game(',
        'connection.call_reducer("update_player_input"': 'client.move_player(',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Migrated {file_path}")

# Usage
# migrate_blackholio_agent_imports('my_agent.py')
```

## Troubleshooting

### Common Installation Issues

1. **pip install fails**
   ```bash
   # Update pip
   python -m pip install --upgrade pip
   
   # Install with verbose output
   pip install -v git+https://github.com/blackholio/blackholio-python-client.git
   ```

2. **Permission denied errors**
   ```bash
   # Use user installation
   pip install --user git+https://github.com/blackholio/blackholio-python-client.git
   
   # Or use virtual environment
   python -m venv venv && source venv/bin/activate
   ```

3. **SSL certificate errors**
   ```bash
   # Disable SSL verification for pip
   pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org git+https://github.com/blackholio/blackholio-python-client.git
   ```

### Deployment Issues

1. **Container startup failures**
   ```bash
   # Check container logs
   docker logs blackholio-client
   
   # Debug container
   docker run -it --rm blackholio-python-client:latest /bin/bash
   ```

2. **Kubernetes pod failures**
   ```bash
   # Check pod events
   kubectl describe pod <pod-name> -n blackholio
   
   # Check logs
   kubectl logs <pod-name> -n blackholio
   ```

3. **Network connectivity issues**
   ```bash
   # Test from container
   docker exec -it blackholio-client nc -zv rust-server 3000
   
   # Test from Kubernetes
   kubectl exec -it <pod-name> -- nc -zv rust-server-service 3000
   ```

### Performance Issues

1. **High memory usage**
   - Increase memory limits in container/pod configuration
   - Enable connection pooling
   - Monitor for memory leaks

2. **Slow connections**
   - Adjust timeout values
   - Use binary protocol for better performance
   - Check network latency

3. **High CPU usage**
   - Reduce operation frequency
   - Enable performance optimizations
   - Scale horizontally

For more detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).