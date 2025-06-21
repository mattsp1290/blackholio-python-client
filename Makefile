# Makefile for blackholio-python-client development
# Professional development workflow automation

.PHONY: help install install-dev clean test lint format type-check security-check coverage docs build publish pre-commit setup-dev run-all-checks version version-next release-patch release-minor release-major release-auto

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy
BANDIT := $(PYTHON) -m bandit
COVERAGE := $(PYTHON) -m coverage
SPHINX := $(PYTHON) -m sphinx

# Project directories
SRC_DIR := src/blackholio_client
TEST_DIR := tests
DOCS_DIR := docs

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)Blackholio Python Client - Development Commands$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install package in production mode
	@echo "$(CYAN)Installing blackholio-client...$(NC)"
	$(PIP) install -e .
	@echo "$(GREEN)✓ Package installed successfully$(NC)"

install-dev: ## Install package with development dependencies
	@echo "$(CYAN)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✓ Development environment ready$(NC)"

setup-dev: install-dev ## Complete development environment setup
	@echo "$(CYAN)Setting up pre-commit hooks...$(NC)"
	pre-commit install
	pre-commit autoupdate
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"
	@echo "$(CYAN)Creating .secrets.baseline for detect-secrets...$(NC)"
	detect-secrets scan > .secrets.baseline || true
	@echo "$(GREEN)✓ Development setup complete!$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Run '$(GREEN)make test$(NC)' to run tests"
	@echo "  2. Run '$(GREEN)make lint$(NC)' to check code quality"
	@echo "  3. Run '$(GREEN)make format$(NC)' to format code"

clean: ## Clean build artifacts and cache files
	@echo "$(CYAN)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .coverage coverage.xml htmlcov/
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf .tox/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

test: ## Run all tests with pytest
	@echo "$(CYAN)Running tests...$(NC)"
	$(PYTEST) -v

test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(NC)"
	$(PYTEST) -v -m unit

test-integration: ## Run integration tests only
	@echo "$(CYAN)Running integration tests...$(NC)"
	$(PYTEST) -v -m integration

test-fast: ## Run fast tests (exclude slow tests)
	@echo "$(CYAN)Running fast tests...$(NC)"
	$(PYTEST) -v -m "not slow"

test-watch: ## Run tests in watch mode
	@echo "$(CYAN)Running tests in watch mode...$(NC)"
	$(PYTEST) -v --looponfail

coverage: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	$(COVERAGE) run -m pytest
	$(COVERAGE) report
	$(COVERAGE) html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

lint: ## Run all linting checks
	@echo "$(CYAN)Running linting checks...$(NC)"
	@echo "$(YELLOW)Running flake8...$(NC)"
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) || (echo "$(RED)✗ Flake8 found issues$(NC)" && false)
	@echo "$(GREEN)✓ Flake8 passed$(NC)"
	@echo "$(YELLOW)Running pylint...$(NC)"
	$(PYTHON) -m pylint $(SRC_DIR) || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and isort
	@echo "$(CYAN)Formatting code...$(NC)"
	@echo "$(YELLOW)Running isort...$(NC)"
	$(ISORT) $(SRC_DIR) $(TEST_DIR)
	@echo "$(YELLOW)Running black...$(NC)"
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting without making changes
	@echo "$(CYAN)Checking code format...$(NC)"
	$(ISORT) --check-only --diff $(SRC_DIR) $(TEST_DIR)
	$(BLACK) --check --diff $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)✓ Code format check passed$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(CYAN)Running type checks...$(NC)"
	$(MYPY) $(SRC_DIR)
	@echo "$(GREEN)✓ Type checking passed$(NC)"

security-check: ## Run security checks with bandit
	@echo "$(CYAN)Running security checks...$(NC)"
	$(BANDIT) -r $(SRC_DIR) -f json -o bandit-report.json || true
	$(BANDIT) -r $(SRC_DIR)
	@echo "$(GREEN)✓ Security check complete$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(CYAN)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

docs: ## Build documentation with Sphinx
	@echo "$(CYAN)Building documentation...$(NC)"
	@mkdir -p docs
	cd docs && $(SPHINX) -b html . _build/html
	@echo "$(GREEN)✓ Documentation built in docs/_build/html$(NC)"

build: clean ## Build distribution packages
	@echo "$(CYAN)Building distribution packages...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Build complete$(NC)"
	@ls -la dist/

check-publish: ## Check package before publishing
	@echo "$(CYAN)Checking package...$(NC)"
	$(PYTHON) -m twine check dist/*
	@echo "$(GREEN)✓ Package checks passed$(NC)"

run-all-checks: format-check lint type-check security-check test ## Run all code quality checks
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ All checks passed! Code is ready for commit.$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

dev: install-dev setup-dev ## Full development setup (alias for common setup)
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ Development environment is ready!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# Environment info
info: ## Show environment information
	@echo "$(CYAN)Environment Information$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip:    $$($(PIP) --version)"
	@echo "Path:   $$(which $(PYTHON))"
	@echo ""
	@echo "$(CYAN)Project Structure$(NC)"
	@echo "Source:  $(SRC_DIR)"
	@echo "Tests:   $(TEST_DIR)"
	@echo "Docs:    $(DOCS_DIR)"

# Watch for changes and run tests
watch: ## Watch for file changes and run tests
	@echo "$(CYAN)Watching for changes...$(NC)"
	$(PYTHON) -m pytest_watch

# Version Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

version: ## Show current version
	@echo "$(CYAN)Current Version$(NC)"
	@$(PYTHON) scripts/version_manager.py current

version-next: ## Show next version (auto-detected from commits)
	@echo "$(CYAN)Next Version$(NC)"
	@$(PYTHON) scripts/version_manager.py next auto

version-bump-patch: ## Bump patch version
	@echo "$(CYAN)Bumping patch version...$(NC)"
	$(PYTHON) scripts/version_manager.py bump patch
	@echo "$(GREEN)✓ Version bumped$(NC)"

version-bump-minor: ## Bump minor version
	@echo "$(CYAN)Bumping minor version...$(NC)"
	$(PYTHON) scripts/version_manager.py bump minor
	@echo "$(GREEN)✓ Version bumped$(NC)"

version-bump-major: ## Bump major version
	@echo "$(CYAN)Bumping major version...$(NC)"
	$(PYTHON) scripts/version_manager.py bump major
	@echo "$(GREEN)✓ Version bumped$(NC)"

version-bump-auto: ## Auto-bump version based on commits
	@echo "$(CYAN)Auto-bumping version...$(NC)"
	$(PYTHON) scripts/version_manager.py bump auto
	@echo "$(GREEN)✓ Version bumped$(NC)"

release-patch: ## Create patch release
	@echo "$(CYAN)Creating patch release...$(NC)"
	./scripts/release.sh patch

release-minor: ## Create minor release
	@echo "$(CYAN)Creating minor release...$(NC)"
	./scripts/release.sh minor

release-major: ## Create major release
	@echo "$(CYAN)Creating major release...$(NC)"
	./scripts/release.sh major

release-auto: ## Create release with auto-detected version
	@echo "$(CYAN)Creating auto-detected release...$(NC)"
	./scripts/release.sh auto

release-dry-run: ## Show what release would do (dry run)
	@echo "$(CYAN)Release dry run...$(NC)"
	./scripts/release.sh auto --dry-run

changelog-update: ## Update changelog for unreleased changes
	@echo "$(CYAN)Updating changelog...$(NC)"
	@commits=$$(git log --oneline $$(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD")..HEAD 2>/dev/null | wc -l); \
	if [ $$commits -gt 0 ]; then \
		echo "Found $$commits commits since last release"; \
		$(PYTHON) scripts/version_manager.py release auto --dry-run; \
	else \
		echo "No commits since last release"; \
	fi