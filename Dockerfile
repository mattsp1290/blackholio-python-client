# Multi-stage Dockerfile for blackholio-python-client
# Supports testing with different Python versions and server languages

# Base stage with common dependencies
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/

# Development stage for testing
FROM base as development

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install package in editable mode
RUN pip install -e .

# Copy test files
COPY tests/ ./tests/
COPY pytest.ini mypy.ini .flake8 .isort.cfg ./

# Set environment variables with defaults
ENV SERVER_LANGUAGE=rust
ENV SERVER_IP=localhost
ENV SERVER_PORT=8080
ENV BLACKHOLIO_DEBUG=false
ENV BLACKHOLIO_LOG_LEVEL=INFO
ENV BLACKHOLIO_CONNECTION_TIMEOUT=30
ENV BLACKHOLIO_MAX_RETRIES=3
ENV PYTHONPATH=/app:$PYTHONPATH

# Create volume for test results
VOLUME ["/app/test-results"]

# Default command runs tests
CMD ["pytest", "-v", "--cov=blackholio_client", "--cov-report=html:/app/test-results/htmlcov", "--cov-report=xml:/app/test-results/coverage.xml"]

# Production stage
FROM base as production

# Install only runtime dependencies
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 blackholio && \
    chown -R blackholio:blackholio /app

USER blackholio

# Set production environment variables
ENV SERVER_LANGUAGE=rust
ENV SERVER_IP=spacetimedb-server
ENV SERVER_PORT=8080
ENV BLACKHOLIO_LOG_LEVEL=WARNING
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose default port (for documentation)
EXPOSE 8080

# Default command for production
CMD ["python", "-c", "from blackholio_client import create_game_client; client = create_game_client(); print('Blackholio client ready')"]

# Test runner stage for CI/CD
FROM development as test-runner

# Install additional CI/CD tools
RUN pip install --no-cache-dir \
    pytest-html \
    pytest-json-report \
    pytest-timeout \
    pytest-xdist

# Add test runner script
COPY <<'EOF' /app/run-tests.sh
#!/bin/bash
set -e

echo "🚀 Running blackholio-python-client tests in Docker container"
echo "Environment Configuration:"
echo "  SERVER_LANGUAGE: $SERVER_LANGUAGE"
echo "  SERVER_IP: $SERVER_IP"
echo "  SERVER_PORT: $SERVER_PORT"
echo "  BLACKHOLIO_LOG_LEVEL: $BLACKHOLIO_LOG_LEVEL"

# Create test results directory
mkdir -p /app/test-results

# Run linting
echo "🔍 Running linting checks..."
flake8 src/ tests/ || true
mypy src/ || true

# Run tests with coverage
echo "🧪 Running tests..."
pytest -v \
    --cov=blackholio_client \
    --cov-report=html:/app/test-results/htmlcov \
    --cov-report=xml:/app/test-results/coverage.xml \
    --cov-report=term \
    --junit-xml=/app/test-results/junit.xml \
    --html=/app/test-results/report.html \
    --self-contained-html \
    tests/

echo "✅ Tests completed!"
EOF

RUN chmod +x /app/run-tests.sh

CMD ["/app/run-tests.sh"]