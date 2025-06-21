# Version Management Guide

This document describes the comprehensive version management system for blackholio-python-client, including semantic versioning, automated releases, and changelog generation.

## Overview

The blackholio-python-client project uses a sophisticated version management system that includes:

- **Semantic Versioning (SemVer)** - Automated version bumping based on change types
- **Conventional Commits** - Standardized commit messages for automatic version detection
- **Automated Changelog** - Generated from commit messages and manual entries
- **Release Automation** - Complete CI/CD pipeline for releases
- **GitHub Integration** - Automated GitHub releases with artifacts

## Version Format

We follow [Semantic Versioning](https://semver.org/) with the format `MAJOR.MINOR.PATCH`:

- **MAJOR** - Breaking changes or major new features
- **MINOR** - New features that are backward compatible
- **PATCH** - Bug fixes and minor improvements

### Prerelease Versions

Prerelease versions are supported with identifiers:
- `1.0.0-alpha` - Alpha release (early development)
- `1.0.0-beta` - Beta release (feature complete, testing)
- `1.0.0-rc` - Release candidate (production ready, final testing)

## Tools and Scripts

### Version Manager Script

The core version management tool: `scripts/version_manager.py`

```bash
# Check current version
python scripts/version_manager.py current

# See what the next version would be
python scripts/version_manager.py next patch
python scripts/version_manager.py next minor
python scripts/version_manager.py next major
python scripts/version_manager.py next auto  # Auto-detect from commits

# Bump version (updates files but doesn't commit)
python scripts/version_manager.py bump patch
python scripts/version_manager.py bump minor --prerelease=alpha
python scripts/version_manager.py bump auto

# Full release (version bump + changelog + git tag + commit)
python scripts/version_manager.py release patch
python scripts/version_manager.py release auto --dry-run
```

### Release Script

Comprehensive release automation: `scripts/release.sh`

```bash
# Quick patch release
./scripts/release.sh patch

# Minor release with confirmation
./scripts/release.sh minor

# Auto-detect version bump from commits
./scripts/release.sh auto

# Prerelease
./scripts/release.sh minor --prerelease=beta

# Dry run to see what would happen
./scripts/release.sh major --dry-run

# Force release (skip checks)
./scripts/release.sh patch --force
```

## Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic version bump detection:

### Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat:` | New feature | MINOR |
| `fix:` | Bug fix | PATCH |
| `docs:` | Documentation changes | PATCH |
| `style:` | Code style changes | PATCH |
| `refactor:` | Code refactoring | PATCH |
| `test:` | Adding/updating tests | PATCH |
| `chore:` | Maintenance tasks | PATCH |
| `perf:` | Performance improvements | PATCH |
| `ci:` | CI/CD changes | PATCH |
| `build:` | Build system changes | PATCH |

### Breaking Changes

Breaking changes trigger a MAJOR version bump:

```bash
# Method 1: Use exclamation mark
git commit -m "feat!: remove deprecated API methods"

# Method 2: Include BREAKING CHANGE in footer
git commit -m "feat: new authentication system

BREAKING CHANGE: Old auth tokens are no longer valid"
```

### Examples

```bash
# Patch version bump
git commit -m "fix: resolve connection timeout issues"
git commit -m "docs: update installation instructions"

# Minor version bump  
git commit -m "feat: add support for Go server language"
git commit -m "feat(auth): implement Ed25519 authentication"

# Major version bump
git commit -m "feat!: redesign client API for better usability"
git commit -m "refactor: remove legacy connection methods

BREAKING CHANGE: BlackholioClient class has been replaced with GameClient"
```

## Release Process

### Manual Release

1. **Prepare Release**
   ```bash
   # Ensure clean working directory
   git status
   
   # Pull latest changes
   git pull origin main
   
   # Run tests
   make test
   ```

2. **Create Release**
   ```bash
   # Auto-detect version bump
   ./scripts/release.sh auto
   
   # Or specify version type
   ./scripts/release.sh minor
   ```

3. **Verify Release**
   - Check GitHub release page
   - Verify package installation
   - Test with dependent projects

### Automated Release (CI/CD)

Releases are automatically triggered when tags are pushed:

```bash
# Create and push tag (after version bump)
git tag v1.2.3
git push origin main --tags
```

The CI/CD pipeline will:
1. Validate the release
2. Run comprehensive tests
3. Build the package
4. Create GitHub release
5. Upload artifacts
6. Validate installation

### Hotfix Release

For urgent fixes on released versions:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/1.2.1 v1.2.0

# Make fixes
git commit -m "fix: critical security vulnerability"

# Release hotfix
./scripts/release.sh patch

# Merge back to main
git checkout main
git merge hotfix/1.2.1
git push origin main --tags
```

## Changelog Management

The changelog is automatically managed using `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format.

### Structure

```markdown
# Changelog

## [Unreleased]
### Added
- New features not yet released

### Changed  
- Changes to existing functionality

### Fixed
- Bug fixes

### Removed
- Removed features

## [1.2.0] - 2025-06-20
### Added
- New authentication system
- Support for Go servers

### Fixed
- Connection timeout issues
```

### Automatic Updates

The version manager automatically:
- Parses commit messages since last release
- Categorizes changes by type
- Updates changelog with new version section
- Clears unreleased section
- Updates version links

### Manual Changelog Entries

For complex features, add entries manually to the `[Unreleased]` section:

```markdown
## [Unreleased]
### Added
- **Game Statistics**: Comprehensive player performance tracking with ML training data export
- **Load Balancing**: Client-side load balancing across multiple SpacetimeDB servers
```

## Version Configuration

### pyproject.toml

Main version configuration:

```toml
[project]
version = "1.2.3"

[tool.commitizen]
version = "1.2.3"
version_files = [
    "pyproject.toml:version",
    "src/blackholio_client/__init__.py:__version__"
]
```

### Package Files

Version is synchronized across:
- `pyproject.toml` - Package metadata
- `src/blackholio_client/__init__.py` - Python package version
- `CHANGELOG.md` - Release history

## Integration with Development Workflow

### Pre-commit Hooks

Version validation in `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: version-consistency
      name: Check version consistency
      entry: python scripts/version_manager.py current
      language: system
      pass_filenames: false
```

### Makefile Integration

Common version operations in `Makefile`:

```makefile
version:
	@python scripts/version_manager.py current

version-next:
	@python scripts/version_manager.py next auto

release-patch:
	./scripts/release.sh patch

release-minor:
	./scripts/release.sh minor

release-major:
	./scripts/release.sh major

release-auto:
	./scripts/release.sh auto
```

### IDE Integration

For Visual Studio Code, add to `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Check Version",
            "type": "shell",
            "command": "python scripts/version_manager.py current",
            "group": "build"
        },
        {
            "label": "Release Auto",
            "type": "shell",
            "command": "./scripts/release.sh auto --dry-run",
            "group": "build"
        }
    ]
}
```

## Troubleshooting

### Common Issues

1. **Version Mismatch Error**
   ```
   ❌ Version mismatch: package=1.2.3, release=1.2.4
   ```
   **Solution**: Ensure all version files are synchronized
   ```bash
   python scripts/version_manager.py bump patch
   ```

2. **Uncommitted Changes**
   ```
   ❌ Uncommitted changes detected
   ```
   **Solution**: Commit or stash changes before release
   ```bash
   git status
   git add .
   git commit -m "chore: prepare for release"
   ```

3. **Failed GitHub Release**
   ```
   ❌ Failed to create GitHub release
   ```
   **Solution**: Check GitHub CLI authentication
   ```bash
   gh auth status
   gh auth login
   ```

### Debug Mode

Use dry-run mode to debug issues:

```bash
# See what would happen without making changes
./scripts/release.sh auto --dry-run
python scripts/version_manager.py release auto --dry-run
```

### Manual Fixes

If automation fails, manual steps:

1. **Fix Version Files**
   ```bash
   # Edit files manually
   vim pyproject.toml
   vim src/blackholio_client/__init__.py
   
   # Validate consistency
   python scripts/version_manager.py current
   ```

2. **Fix Changelog**
   ```bash
   # Edit changelog manually
   vim CHANGELOG.md
   
   # Validate format
   grep -E "^## \[[0-9]+\.[0-9]+\.[0-9]+\]" CHANGELOG.md
   ```

3. **Manual Git Tag**
   ```bash
   # Create tag manually
   git tag -a v1.2.3 -m "Release 1.2.3"
   git push origin main --tags
   ```

## Best Practices

### Commit Messages

- Use descriptive, clear commit messages
- Follow conventional commit format
- Include scope when relevant: `feat(auth): add token refresh`
- Reference issues: `fix: resolve connection timeout (#123)`

### Release Timing

- **Patch releases**: As needed for bug fixes
- **Minor releases**: Monthly for new features  
- **Major releases**: Quarterly for breaking changes
- **Hotfixes**: Immediately for critical issues

### Testing

Always test before release:
```bash
# Full test suite
make test

# Performance validation  
pytest tests/test_performance.py

# Integration tests
pytest tests/integration/ -m "not slow"

# Security audit
python security_audit.py
```

### Communication

- Update documentation before releases
- Notify dependent projects of breaking changes
- Include migration guides for major releases
- Announce releases to stakeholders

## Version History

| Version | Release Date | Description |
|---------|--------------|-------------|
| 0.1.0 | 2025-06-20 | Initial release with comprehensive SpacetimeDB integration |

---

For questions about version management, see the [troubleshooting guide](TROUBLESHOOTING.md) or create an issue on GitHub.