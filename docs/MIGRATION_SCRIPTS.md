# Migration Scripts Documentation

Comprehensive guide to the automated migration scripts for migrating blackholio-agent and client-pygame projects to use the unified blackholio-python-client package.

## Table of Contents

- [Overview](#overview)
- [Available Scripts](#available-scripts)
- [Quick Start Guide](#quick-start-guide)
- [Script Details](#script-details)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The migration scripts provide automated assistance for migrating existing blackholio projects to use the unified blackholio-python-client package. These scripts eliminate manual migration errors, reduce migration time, and provide comprehensive validation and reporting.

### Migration Benefits

- ✅ **Automated Code Updates**: Automatic replacement of imports and code patterns
- ✅ **Dependency Management**: Automatic requirements.txt updates
- ✅ **Backup Creation**: Safe backup of original code before migration
- ✅ **Validation Testing**: Automated validation of migration success
- ✅ **Comprehensive Reporting**: Detailed migration reports and summaries
- ✅ **Error Recovery**: Rollback capabilities if migration fails

## Available Scripts

### 1. `migrate_blackholio_agent.py`
**Purpose**: Migrate blackholio-agent ML training projects
**Target**: Projects with ML agents, training scripts, and neural networks

### 2. `migrate_client_pygame.py`
**Purpose**: Migrate client-pygame game client projects  
**Target**: Projects with pygame rendering, game loops, and client interfaces

### 3. `migrate_project.py` (Universal)
**Purpose**: Universal migration script with automatic project detection
**Target**: Any blackholio project (automatically detects type)

### 4. `batch_migrate.py`
**Purpose**: Batch migration of multiple projects
**Target**: Multiple projects in directory trees

## Quick Start Guide

### Single Project Migration (Recommended)

```bash
# Navigate to blackholio-python-client directory
cd /path/to/blackholio-python-client

# Migrate a single project (auto-detection)
python scripts/migrate_project.py --project-path ~/git/blackholio-agent

# Dry run first (recommended)
python scripts/migrate_project.py --project-path ~/git/blackholio-agent --dry-run
```

### Batch Migration (Multiple Projects)

```bash
# Migrate all blackholio projects in ~/git directory
python scripts/batch_migrate.py --search-paths ~/git

# Dry run for batch migration
python scripts/batch_migrate.py --search-paths ~/git --dry-run
```

### Project-Specific Migration

```bash
# Blackholio-agent specific
python scripts/migrate_blackholio_agent.py --project-path ~/git/blackholio-agent

# Client-pygame specific  
python scripts/migrate_client_pygame.py --project-path ~/git/Blackholio/client-pygame
```

## Script Details

### Universal Migration Script (`migrate_project.py`)

**Features:**
- Automatic project type detection
- Calls appropriate project-specific migration script
- Unified reporting and validation
- Error handling and recovery

**Usage:**
```bash
python scripts/migrate_project.py --project-path PROJECT_PATH [--dry-run]
```

**Options:**
- `--project-path`: Path to project directory (required)
- `--dry-run`: Preview changes without making modifications
- `--no-auto-detect`: Disable automatic project type detection

### Blackholio-Agent Migration (`migrate_blackholio_agent.py`)

**Automated Changes:**
- SpacetimeDB connection imports → `from blackholio_client import GameClient, create_game_client`
- Data model imports → `from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle`
- Statistics imports → `from blackholio_client.models.game_statistics import PlayerStatistics, SessionStatistics`
- Physics imports → `from blackholio_client.models.physics import calculate_center_of_mass, check_collision`
- Client instantiation → `create_game_client()`
- Environment variables → SERVER_IP, SERVER_PORT, SERVER_LANGUAGE patterns

**Generated Files:**
- `.env.example` - Environment configuration template
- `validate_migration.py` - Migration validation script
- `migration_report.json` - Detailed migration report
- `MIGRATION_SUMMARY.md` - Human-readable summary

### Client-Pygame Migration (`migrate_client_pygame.py`)

**Automated Changes:**
- SpacetimeDB connection imports → blackholio_client imports
- Entity model imports → unified data models
- Physics calculations → blackholio_client physics functions
- Pygame-specific patterns → `.pos.x` → `.position.x`
- Data access patterns → `.get_position()` → `.position`
- Event handling → unified event system

**Generated Files:**
- `.env.example` - Environment configuration with pygame settings
- `pygame_integration_helper.py` - Pygame integration utilities
- `validate_migration.py` - Migration validation with pygame tests
- Migration reports and summaries

### Batch Migration (`batch_migrate.py`)

**Features:**
- Automatic project discovery in directory trees
- Parallel or sequential migration processing
- Consolidated reporting across all projects
- Error handling and recovery for multiple projects

**Usage:**
```bash
python scripts/batch_migrate.py [OPTIONS]
```

**Options:**
- `--search-paths PATH1 PATH2`: Directories to search for projects
- `--dry-run`: Preview all migrations without changes
- `--sequential`: Process projects one by one (default: parallel)
- `--max-workers N`: Number of parallel workers (default: 2)
- `--output-dir DIR`: Directory for batch reports

## Usage Examples

### Example 1: Single Project Migration with Validation

```bash
# Step 1: Dry run to preview changes
python scripts/migrate_project.py \
    --project-path ~/git/blackholio-agent \
    --dry-run

# Step 2: Review the preview, then run actual migration
python scripts/migrate_project.py \
    --project-path ~/git/blackholio-agent

# Step 3: Install new dependencies
cd ~/git/blackholio-agent
pip install -r requirements.txt

# Step 4: Run validation (automatically created)
python validate_migration.py

# Step 5: Test your application
python main.py  # or your normal startup command
```

### Example 2: Batch Migration with Custom Settings

```bash
# Migrate all projects in multiple directories
python scripts/batch_migrate.py \
    --search-paths ~/git ~/projects ~/work \
    --max-workers 3 \
    --output-dir ~/migration_reports

# Review batch results
cat ~/migration_reports/BATCH_MIGRATION_SUMMARY.md
```

### Example 3: Project-Specific Migration

```bash
# Blackholio-agent with custom path
python scripts/migrate_blackholio_agent.py \
    --project-path /custom/path/to/agent

# Client-pygame with dry run
python scripts/migrate_client_pygame.py \
    --project-path ~/projects/game-client \
    --dry-run
```

## Generated Files and Reports

### Migration Reports

Each migration generates comprehensive reports:

1. **`migration_report.json`** - Machine-readable detailed report
2. **`MIGRATION_SUMMARY.md`** - Human-readable summary
3. **`UNIVERSAL_MIGRATION_SUMMARY.md`** - Universal script summary

### Validation Scripts

- **`validate_migration.py`** - Automated validation testing
- Import testing, functionality testing, integration testing

### Configuration Files

- **`.env.example`** - Environment variable templates
- Project-specific configuration examples

### Helper Files

- **`pygame_integration_helper.py`** (pygame projects) - Pygame integration utilities
- **`backup_pre_migration/`** - Complete backup of original code

## Troubleshooting

### Common Issues

#### 1. Import Errors After Migration

**Problem**: Import errors when running migrated code
**Solution**: 
```bash
# Ensure blackholio-client is installed
pip install git+https://github.com/punk1290/blackholio-python-client.git

# Run validation script
python validate_migration.py
```

#### 2. Environment Configuration Issues

**Problem**: Server connection failures
**Solution**:
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings:
# SERVER_LANGUAGE=rust
# SERVER_IP=localhost  
# SERVER_PORT=3000
```

#### 3. Migration Script Fails

**Problem**: Migration script encounters errors
**Solution**:
```bash
# Check backup exists
ls backup_pre_migration/

# Restore from backup if needed
rm -rf original_files/
cp -r backup_pre_migration/* ./

# Run with dry-run to diagnose
python scripts/migrate_project.py --project-path . --dry-run
```

#### 4. Validation Failures

**Problem**: validate_migration.py reports failures
**Solution**:
1. Check detailed error messages
2. Ensure all dependencies are installed
3. Verify environment configuration
4. Run individual test components

### Error Recovery

#### Automatic Backup

All migration scripts create automatic backups:
```bash
# Backup location
backup_pre_migration/

# Restore if needed
rm -rf ./*  # BE CAREFUL!
cp -r backup_pre_migration/* ./
```

#### Manual Rollback

```bash
# If backup is corrupted, use git
git checkout HEAD -- .  # Restore from git
git clean -fd          # Remove new files

# Or restore from version control
git reset --hard HEAD
```

## Advanced Usage

### Custom Migration Patterns

For advanced users, migration scripts can be extended:

1. **Add Custom Patterns**: Edit pattern dictionaries in migration scripts
2. **Custom Validation**: Extend validation scripts with project-specific tests
3. **Configuration Templates**: Customize environment templates

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
name: Migrate to blackholio-client
on: [workflow_dispatch]
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Migration
        run: |
          cd blackholio-python-client
          python scripts/migrate_project.py --project-path ../project
          python ../project/validate_migration.py
```

### Batch Processing with Filtering

```bash
# Only migrate specific project types
python scripts/batch_migrate.py \
    --search-paths ~/git \
    --filter-type blackholio-agent

# Exclude certain directories
python scripts/batch_migrate.py \
    --search-paths ~/git \
    --exclude-patterns "*backup*" "*old*"
```

## Performance Optimization

### Parallel Processing

- Batch migration uses ThreadPoolExecutor for parallel processing
- Default: 2 workers (safe for most systems)
- Increase for powerful systems: `--max-workers 4`

### Large Project Handling

- Scripts handle large codebases efficiently
- Memory usage optimized for file-by-file processing
- Timeout protection prevents hanging

## Support and Feedback

### Getting Help

1. **Check Migration Reports**: Always review generated reports first
2. **Run Validation Scripts**: Use automated validation for diagnostics
3. **Check Documentation**: Review project-specific migration guides
4. **Report Issues**: Submit issues with migration reports attached

### Support Resources

- **Migration Documentation**: `docs/MIGRATION_*.md`
- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **GitHub Issues**: https://github.com/punk1290/blackholio-python-client/issues

### Contributing

To improve migration scripts:

1. **Test on Different Projects**: Help validate migration patterns
2. **Report Issues**: Submit detailed issue reports
3. **Suggest Improvements**: Propose new migration patterns
4. **Contribute Code**: Submit pull requests with enhancements

---

*These migration scripts are part of the blackholio-python-client package and are designed to make migration as smooth and error-free as possible. For the best results, always run dry-run mode first and review the generated reports.*