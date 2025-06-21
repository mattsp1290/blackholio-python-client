# Development Setup Guide

Welcome to the blackholio-python-client development environment! This guide will help you set up a professional development environment with all the tools and configurations needed for high-quality Python development.

## Prerequisites

- Python 3.8 or higher
- Git
- Make (optional but recommended)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/blackholio/blackholio-python-client.git
cd blackholio-python-client

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development environment
make dev  # Or manually: pip install -e . && pip install -r requirements-dev.txt
```

## Development Workflow

### 1. Setting Up Your Environment

#### Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

#### Install Dependencies
```bash
# Install package in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Or use Make (recommended)
make install-dev
```

#### Configure Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks on all files (first time)
pre-commit run --all-files

# Or use Make
make setup-dev
```

### 2. Development Tools

#### Available Make Commands

```bash
make help          # Show all available commands
make dev           # Complete development setup
make test          # Run all tests
make lint          # Run linting checks
make format        # Format code with black and isort
make type-check    # Run type checking with mypy
make coverage      # Generate test coverage report
make clean         # Clean build artifacts
make build         # Build distribution packages
```

#### Code Formatting

We use Black for code formatting and isort for import sorting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Or use Make
make format

# Check formatting without changes
make format-check
```

#### Linting

Multiple linters ensure code quality:

```bash
# Run flake8
flake8 src/ tests/

# Run all linting checks
make lint
```

#### Type Checking

We use mypy for static type checking:

```bash
# Run type checks
mypy src/blackholio_client

# Or use Make
make type-check
```

### 3. Testing

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=blackholio_client

# Run specific test file
pytest tests/test_connection.py

# Run tests matching pattern
pytest -k "test_connect"

# Use Make commands
make test          # All tests
make test-unit     # Unit tests only
make test-integration  # Integration tests only
make coverage      # With coverage report
```

#### Test Markers

Tests are organized with markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.server_rust` - Tests requiring Rust server
- `@pytest.mark.server_python` - Tests requiring Python server

```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### 4. Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

- **trailing-whitespace** - Remove trailing whitespace
- **end-of-file-fixer** - Ensure files end with newline
- **check-yaml** - Validate YAML files
- **check-json** - Validate JSON files
- **black** - Format Python code
- **isort** - Sort imports
- **flake8** - Lint Python code
- **mypy** - Type check Python code
- **bandit** - Security checks
- **detect-secrets** - Scan for secrets

#### Manual Pre-commit Usage

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

### 5. Project Structure

```
blackholio-python-client/
├── src/
│   └── blackholio_client/
│       ├── __init__.py
│       ├── config/           # Configuration management
│       ├── connection/       # SpacetimeDB connections
│       ├── models/          # Data models
│       ├── utils/           # Utility functions
│       └── exceptions/      # Custom exceptions
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test fixtures
├── docs/                   # Documentation
├── .github/                # GitHub Actions workflows
├── pyproject.toml         # Project configuration
├── setup.py               # Backward compatibility
├── requirements-dev.txt   # Development dependencies
├── Makefile              # Development commands
├── pytest.ini            # Pytest configuration
├── .flake8               # Flake8 configuration
├── .isort.cfg            # isort configuration
├── mypy.ini              # MyPy configuration
└── .pre-commit-config.yaml  # Pre-commit hooks
```

### 6. Code Style Guidelines

#### Python Style
- Follow PEP 8 with 100-character line limit
- Use Black for formatting (automatically enforced)
- Use Google-style docstrings
- Type hints for all functions and methods

#### Import Order (enforced by isort)
1. Standard library imports
2. Third-party imports
3. Local application imports

#### Docstring Example
```python
def calculate_distance(point_a: Vector2, point_b: Vector2) -> float:
    """Calculate Euclidean distance between two points.
    
    Args:
        point_a: First point with x and y coordinates.
        point_b: Second point with x and y coordinates.
        
    Returns:
        The Euclidean distance between the points.
        
    Raises:
        ValueError: If either point has invalid coordinates.
    """
```

### 7. Security Considerations

#### Security Scanning
```bash
# Run security checks with bandit
bandit -r src/

# Check for secrets
detect-secrets scan

# Or use Make
make security-check
```

#### Environment Variables
- Never commit secrets or API keys
- Use environment variables for sensitive configuration
- Document required environment variables in README

### 8. Continuous Integration

GitHub Actions runs on every push and pull request:

- **Tests** - All test suites with coverage
- **Linting** - Code quality checks
- **Type Checking** - Static type analysis
- **Security** - Vulnerability scanning
- **Build** - Package building validation

### 9. Troubleshooting

#### Common Issues

**Import Errors**
```bash
# Ensure package is installed in development mode
pip install -e .
```

**Pre-commit Failures**
```bash
# Format code before committing
make format

# Or manually fix and stage changes
git add -u
```

**Type Checking Errors**
```bash
# Install type stubs
pip install types-requests types-setuptools
```

#### Getting Help

1. Check existing issues on GitHub
2. Run tests with verbose output: `pytest -vvv`
3. Check tool-specific documentation
4. Ask in project discussions

### 10. Making Contributions

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**
   ```bash
   make test
   make lint
   ```

3. **Commit with conventional commits**
   ```bash
   git commit -m "feat: add new connection retry logic"
   ```

4. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Best Practices

1. **Always work in a virtual environment**
2. **Run tests before committing**
3. **Keep commits focused and atomic**
4. **Write descriptive commit messages**
5. **Update documentation with code changes**
6. **Add tests for new functionality**
7. **Check coverage remains above 80%**
8. **Review pre-commit output**

## Next Steps

Now that your development environment is set up:

1. Run `make test` to ensure everything works
2. Check out open issues on GitHub
3. Read the architecture documentation
4. Start contributing!

Happy coding! 🚀