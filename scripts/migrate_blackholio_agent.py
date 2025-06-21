#!/usr/bin/env python3
"""
Migration Script: blackholio-agent to blackholio-python-client
==============================================================

Automated migration script to help blackholio-agent project migrate to the
unified blackholio-python-client package with minimal manual intervention.

This script performs:
1. Backup creation
2. Dependency analysis and updates
3. Code pattern replacement
4. Import statement updates
5. Configuration migration
6. Validation and testing

Usage:
    python migrate_blackholio_agent.py [--dry-run] [--project-path PATH]
"""

import os
import sys
import re
import shutil
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_blackholio_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BlackholioAgentMigrator:
    """Automated migration utility for blackholio-agent project."""
    
    def __init__(self, project_path: str, dry_run: bool = False):
        self.project_path = Path(project_path).resolve()
        self.dry_run = dry_run
        self.backup_path = self.project_path / "backup_pre_migration"
        self.migration_report = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "dry_run": dry_run,
            "files_modified": [],
            "patterns_replaced": {},
            "errors": [],
            "warnings": []
        }
        
        # Migration patterns for blackholio-agent
        self.import_replacements = {
            # SpacetimeDB connection imports
            r'from\s+spacetimedb.*import.*': 'from blackholio_client import GameClient, create_game_client',
            r'import\s+spacetimedb.*': 'from blackholio_client import GameClient, create_game_client',
            
            # Local data model imports
            r'from\s+\.?.*vector2.*import.*Vector2': 'from blackholio_client.models.game_entities import Vector2',
            r'from\s+\.?.*game_entity.*import.*GameEntity': 'from blackholio_client.models.game_entities import GameEntity',
            r'from\s+\.?.*game_player.*import.*GamePlayer': 'from blackholio_client.models.game_entities import GamePlayer',
            r'from\s+\.?.*game_circle.*import.*GameCircle': 'from blackholio_client.models.game_entities import GameCircle',
            
            # Statistics imports
            r'from\s+\.?.*statistics.*import.*': 'from blackholio_client.models.game_statistics import PlayerStatistics, SessionStatistics',
            
            # Physics imports
            r'from\s+\.?.*physics.*import.*': 'from blackholio_client.models.physics import calculate_center_of_mass, check_collision, calculate_entity_radius',
            
            # Data conversion imports
            r'from\s+\.?.*data_converter.*import.*': 'from blackholio_client.models.data_converters import EntityConverter, PlayerConverter, CircleConverter',
        }
        
        self.code_replacements = {
            # SpacetimeDB client instantiation
            r'SpacetimeDBClient\s*\([^)]*\)': 'create_game_client()',
            r'spacetimedb\.connect\s*\([^)]*\)': 'create_game_client()',
            
            # Environment variable patterns
            r'os\.environ\.get\s*\(\s*[\'"]SERVER_URL[\'"]': 'os.environ.get("SERVER_IP", "localhost")',
            r'os\.environ\.get\s*\(\s*[\'"]SPACETIMEDB_URL[\'"]': 'os.environ.get("SERVER_IP", "localhost")',
            
            # Connection method calls
            r'\.connect\s*\(\s*[^)]*\)': '.connect()',
            r'\.subscribe\s*\(\s*[^)]*\)': '.subscribe_to_tables()',
            
            # Data model instantiation patterns
            r'Vector2\s*\(\s*([^,]+),\s*([^)]+)\)': r'Vector2(\1, \2)',
            r'GameEntity\s*\(\s*([^)]+)\)': r'GameEntity(\1)',
            r'GamePlayer\s*\(\s*([^)]+)\)': r'GamePlayer(\1)',
            r'GameCircle\s*\(\s*([^)]+)\)': r'GameCircle(\1)',
            
            # Physics calculation updates
            r'calculate_center_of_mass\s*\(\s*([^)]+)\)': r'calculate_center_of_mass(\1)',
            r'check_collision\s*\(\s*([^)]+)\)': r'check_collision(\1)',
            
            # Statistics tracking updates
            r'PlayerStats\s*\(\s*([^)]+)\)': r'PlayerStatistics(\1)',
            r'SessionStats\s*\(\s*([^)]+)\)': r'SessionStatistics(\1)',
        }
        
        # Files to modify (common ML agent patterns)
        self.target_files = [
            "**/*.py",  # All Python files
        ]
        
        # Files to exclude from migration
        self.exclude_patterns = [
            "**/__pycache__/**",
            "**/.*/**",
            "**/venv/**",
            "**/env/**",
            "**/migrations/**",
            "**/backup_pre_migration/**",
            "**/*.pyc",
            "**/*.pyo",
        ]

    def validate_project_structure(self) -> bool:
        """Validate that this is a blackholio-agent project."""
        logger.info(f"Validating project structure at: {self.project_path}")
        
        # Check for key blackholio-agent files/directories
        required_indicators = [
            "requirements.txt",
            "scripts/train_agent.py",
            "src/blackholio_agent/",
            "src/blackholio_agent/environment/",
            "src/blackholio_agent/models/",
            "src/blackholio_agent/training/",
        ]
        
        found_indicators = []
        for indicator in required_indicators:
            if (self.project_path / indicator).exists():
                found_indicators.append(indicator)
        
        if len(found_indicators) < 3:
            logger.error(f"Project doesn't appear to be blackholio-agent. Found only {found_indicators}")
            return False
        
        logger.info(f"Project validation passed. Found indicators: {found_indicators}")
        return True

    def create_backup(self) -> bool:
        """Create a backup of the project before migration."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create backup at: {self.backup_path}")
            return True
        
        try:
            if self.backup_path.exists():
                shutil.rmtree(self.backup_path)
            
            logger.info(f"Creating backup at: {self.backup_path}")
            shutil.copytree(
                self.project_path,
                self.backup_path,
                ignore=shutil.ignore_patterns(
                    '__pycache__', '*.pyc', '.git', 'venv', 'env', '*.log'
                )
            )
            logger.info("Backup created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            self.migration_report["errors"].append(f"Backup creation failed: {e}")
            return False

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze current dependencies and suggest updates."""
        logger.info("Analyzing project dependencies...")
        
        analysis = {
            "requirements_files": [],
            "current_dependencies": [],
            "suggested_additions": [],
            "suggested_removals": []
        }
        
        # Check for requirements files
        req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py"]
        for req_file in req_files:
            req_path = self.project_path / req_file
            if req_path.exists():
                analysis["requirements_files"].append(req_file)
                
                if req_file == "requirements.txt":
                    with open(req_path, 'r') as f:
                        content = f.read()
                        analysis["current_dependencies"].extend(
                            [line.strip() for line in content.split('\n') 
                             if line.strip() and not line.startswith('#')]
                        )
        
        # Suggest blackholio-client dependency
        analysis["suggested_additions"] = [
            "# blackholio-python-client - Unified SpacetimeDB client",
            "git+https://github.com/punk1290/blackholio-python-client.git"
        ]
        
        # Suggest removals of duplicate dependencies
        analysis["suggested_removals"] = [
            "spacetimedb",
            "websockets",  # Now handled by blackholio-client
            "aiohttp",     # Now handled by blackholio-client
        ]
        
        logger.info(f"Dependency analysis complete. Found {len(analysis['current_dependencies'])} dependencies")
        return analysis

    def update_requirements(self, analysis: Dict[str, Any]) -> bool:
        """Update requirements.txt with blackholio-client dependency."""
        req_path = self.project_path / "requirements.txt"
        
        if not req_path.exists():
            logger.warning("requirements.txt not found, creating new one")
            if self.dry_run:
                logger.info("[DRY RUN] Would create requirements.txt")
                return True
        
        try:
            # Read current requirements
            current_content = ""
            if req_path.exists():
                with open(req_path, 'r') as f:
                    current_content = f.read()
            
            # Parse current requirements
            lines = current_content.split('\n')
            updated_lines = []
            blackholio_added = False
            
            for line in lines:
                line_stripped = line.strip()
                
                # Skip lines that contain dependencies we want to remove
                if any(dep in line_stripped.lower() for dep in analysis["suggested_removals"]):
                    logger.info(f"Removing dependency: {line_stripped}")
                    self.migration_report["patterns_replaced"][f"removed_dependency_{line_stripped}"] = 1
                    continue
                
                # Add blackholio-client before first dependency
                if line_stripped and not line_stripped.startswith('#') and not blackholio_added:
                    updated_lines.extend(analysis["suggested_additions"])
                    updated_lines.append("")  # Empty line for readability
                    blackholio_added = True
                
                updated_lines.append(line)
            
            # If no dependencies found, just add blackholio-client
            if not blackholio_added:
                if updated_lines and updated_lines[-1].strip():
                    updated_lines.append("")
                updated_lines.extend(analysis["suggested_additions"])
            
            new_content = '\n'.join(updated_lines)
            
            if self.dry_run:
                logger.info("[DRY RUN] Would update requirements.txt:")
                logger.info(new_content)
                return True
            
            with open(req_path, 'w') as f:
                f.write(new_content)
            
            self.migration_report["files_modified"].append("requirements.txt")
            logger.info("requirements.txt updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update requirements.txt: {e}")
            self.migration_report["errors"].append(f"Requirements update failed: {e}")
            return False

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        for pattern in self.target_files:
            for file_path in self.project_path.glob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    # Check if file should be excluded
                    relative_path = file_path.relative_to(self.project_path)
                    should_exclude = any(
                        relative_path.match(exclude_pattern) 
                        for exclude_pattern in self.exclude_patterns
                    )
                    
                    if not should_exclude:
                        python_files.append(file_path)
        
        logger.info(f"Found {len(python_files)} Python files to process")
        return python_files

    def migrate_file(self, file_path: Path) -> Dict[str, int]:
        """Migrate a single Python file."""
        logger.debug(f"Processing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            replacements_made = {}
            
            # Apply import replacements
            for pattern, replacement in self.import_replacements.items():
                matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
                    replacements_made[f"import_{pattern}"] = len(matches)
                    logger.debug(f"Replaced {len(matches)} import patterns in {file_path}")
            
            # Apply code replacements
            for pattern, replacement in self.code_replacements.items():
                matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
                    replacements_made[f"code_{pattern}"] = len(matches)
                    logger.debug(f"Replaced {len(matches)} code patterns in {file_path}")
            
            # Only write if changes were made
            if content != original_content:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would modify {file_path}")
                    logger.debug(f"[DRY RUN] Replacements: {replacements_made}")
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.migration_report["files_modified"].append(str(file_path.relative_to(self.project_path)))
                    logger.info(f"Modified {file_path}")
                
                return replacements_made
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            self.migration_report["errors"].append(f"File processing failed {file_path}: {e}")
            return {}

    def create_environment_config(self) -> bool:
        """Create or update environment configuration files."""
        logger.info("Creating environment configuration...")
        
        # Create .env.example file
        env_example_content = """# blackholio-agent Environment Configuration
# Copy this file to .env and customize for your environment

# SpacetimeDB Server Configuration
SERVER_LANGUAGE=rust
SERVER_IP=localhost
SERVER_PORT=3000

# blackholio-python-client Configuration
BLACKHOLIO_CLIENT_TIMEOUT=30
BLACKHOLIO_CLIENT_RETRY_ATTEMPTS=3
BLACKHOLIO_CLIENT_LOG_LEVEL=INFO

# ML Training Configuration
TRAINING_EPISODES=1000
TRAINING_BATCH_SIZE=32
TRAINING_LEARNING_RATE=0.001

# Game Configuration
GAME_MAX_PLAYERS=100
GAME_WORLD_SIZE=1000
"""
        
        env_example_path = self.project_path / ".env.example"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create {env_example_path}")
            return True
        
        try:
            with open(env_example_path, 'w') as f:
                f.write(env_example_content)
            
            self.migration_report["files_modified"].append(".env.example")
            logger.info("Created .env.example file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .env.example: {e}")
            self.migration_report["errors"].append(f"Environment config creation failed: {e}")
            return False

    def create_migration_validation_script(self) -> bool:
        """Create a script to validate migration success."""
        validation_script_content = '''#!/usr/bin/env python3
"""
Migration Validation Script for blackholio-agent
================================================

This script validates that the migration to blackholio-python-client was successful.
"""

import sys
import traceback
from typing import List, Tuple

def test_imports() -> List[Tuple[str, bool, str]]:
    """Test that all required imports work correctly."""
    tests = []
    
    # Test blackholio_client imports
    try:
        from blackholio_client import GameClient, create_game_client
        tests.append(("blackholio_client.GameClient", True, "OK"))
    except Exception as e:
        tests.append(("blackholio_client.GameClient", False, str(e)))
    
    # Test data model imports
    try:
        from blackholio_client.models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle
        tests.append(("blackholio_client.models.game_entities", True, "OK"))
    except Exception as e:
        tests.append(("blackholio_client.models.game_entities", False, str(e)))
    
    # Test statistics imports
    try:
        from blackholio_client.models.game_statistics import PlayerStatistics, SessionStatistics
        tests.append(("blackholio_client.models.game_statistics", True, "OK"))
    except Exception as e:
        tests.append(("blackholio_client.models.game_statistics", False, str(e)))
    
    # Test physics imports
    try:
        from blackholio_client.models.physics import calculate_center_of_mass, check_collision
        tests.append(("blackholio_client.models.physics", True, "OK"))
    except Exception as e:
        tests.append(("blackholio_client.models.physics", False, str(e)))
    
    return tests

def test_functionality() -> List[Tuple[str, bool, str]]:
    """Test basic functionality of migrated components."""
    tests = []
    
    try:
        from blackholio_client.models.game_entities import Vector2, GameEntity
        
        # Test Vector2 operations
        v1 = Vector2(3.0, 4.0)
        v2 = Vector2(1.0, 2.0)
        v3 = v1 + v2
        magnitude = v1.magnitude()
        
        if abs(magnitude - 5.0) < 0.001 and v3.x == 4.0 and v3.y == 6.0:
            tests.append(("Vector2 operations", True, "OK"))
        else:
            tests.append(("Vector2 operations", False, f"Expected magnitude=5.0, got {magnitude}"))
    
    except Exception as e:
        tests.append(("Vector2 operations", False, str(e)))
    
    try:
        from blackholio_client.models.game_entities import GameEntity
        
        # Test GameEntity creation
        entity = GameEntity(
            entity_id=1,
            position=Vector2(10.0, 20.0),
            mass=50.0
        )
        
        radius = entity.radius
        if radius > 0:
            tests.append(("GameEntity creation", True, "OK"))
        else:
            tests.append(("GameEntity creation", False, f"Invalid radius: {radius}"))
    
    except Exception as e:
        tests.append(("GameEntity creation", False, str(e)))
    
    try:
        from blackholio_client import create_game_client
        
        # Test client creation (this might fail without server, but import should work)
        client = create_game_client()
        tests.append(("GameClient creation", True, "OK"))
    
    except Exception as e:
        # This is expected to fail without a server running
        if "connect" in str(e).lower() or "server" in str(e).lower():
            tests.append(("GameClient creation", True, "OK (server not running)"))
        else:
            tests.append(("GameClient creation", False, str(e)))
    
    return tests

def main():
    """Run migration validation tests."""
    print("blackholio-agent Migration Validation")
    print("=" * 40)
    
    all_passed = True
    
    # Test imports
    print("\\nTesting imports...")
    import_tests = test_imports()
    for test_name, passed, message in import_tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}: {message}")
        if not passed:
            all_passed = False
    
    # Test functionality
    print("\\nTesting functionality...")
    func_tests = test_functionality()
    for test_name, passed, message in func_tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}: {message}")
        if not passed:
            all_passed = False
    
    # Summary
    print("\\n" + "=" * 40)
    if all_passed:
        print("✅ Migration validation PASSED!")
        print("Your blackholio-agent project has been successfully migrated.")
        return 0
    else:
        print("❌ Migration validation FAILED!")
        print("Please check the errors above and fix any issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        
        validation_script_path = self.project_path / "validate_migration.py"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create {validation_script_path}")
            return True
        
        try:
            with open(validation_script_path, 'w') as f:
                f.write(validation_script_content)
            
            # Make script executable
            os.chmod(validation_script_path, 0o755)
            
            self.migration_report["files_modified"].append("validate_migration.py")
            logger.info("Created validation script: validate_migration.py")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create validation script: {e}")
            self.migration_report["errors"].append(f"Validation script creation failed: {e}")
            return False

    def generate_migration_report(self) -> bool:
        """Generate a detailed migration report."""
        report_path = self.project_path / "migration_report.json"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create migration report at {report_path}")
            logger.info(f"[DRY RUN] Report content: {json.dumps(self.migration_report, indent=2)}")
            return True
        
        try:
            with open(report_path, 'w') as f:
                json.dump(self.migration_report, f, indent=2)
            
            logger.info(f"Migration report saved to: {report_path}")
            
            # Also create a human-readable summary
            summary_path = self.project_path / "MIGRATION_SUMMARY.md"
            summary_content = f"""# blackholio-agent Migration Summary

Migration completed on: {self.migration_report['timestamp']}

## Files Modified
- Total files modified: {len(self.migration_report['files_modified'])}

### Modified Files:
{chr(10).join(f'- {file}' for file in self.migration_report['files_modified'])}

## Pattern Replacements
{chr(10).join(f'- {pattern}: {count} replacements' for pattern, count in self.migration_report['patterns_replaced'].items())}

## Errors and Warnings
- Errors: {len(self.migration_report['errors'])}
- Warnings: {len(self.migration_report['warnings'])}

{chr(10).join(f'- ERROR: {error}' for error in self.migration_report['errors'])}
{chr(10).join(f'- WARNING: {warning}' for warning in self.migration_report['warnings'])}

## Next Steps

1. **Install Dependencies**: Run `pip install -r requirements.txt`
2. **Validate Migration**: Run `python validate_migration.py`
3. **Update Environment**: Copy `.env.example` to `.env` and configure
4. **Test Your Application**: Run your normal test suite
5. **Performance Validation**: Monitor for any performance changes

## Backup Location
Your original code has been backed up to: `backup_pre_migration/`

## Support
If you encounter issues, refer to:
- Migration documentation: docs/MIGRATION_BLACKHOLIO_AGENT.md
- Troubleshooting guide: docs/TROUBLESHOOTING.md
- Project issues: https://github.com/punk1290/blackholio-python-client/issues
"""
            
            with open(summary_path, 'w') as f:
                f.write(summary_content)
            
            logger.info(f"Migration summary saved to: {summary_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate migration report: {e}")
            return False

    def run_migration(self) -> bool:
        """Execute the complete migration process."""
        logger.info("Starting blackholio-agent migration...")
        logger.info(f"Project path: {self.project_path}")
        logger.info(f"Dry run mode: {self.dry_run}")
        
        # Step 1: Validate project structure
        if not self.validate_project_structure():
            return False
        
        # Step 2: Create backup
        if not self.create_backup():
            return False
        
        # Step 3: Analyze dependencies
        dependency_analysis = self.analyze_dependencies()
        
        # Step 4: Update requirements
        if not self.update_requirements(dependency_analysis):
            return False
        
        # Step 5: Find and migrate Python files
        python_files = self.find_python_files()
        total_replacements = {}
        
        for file_path in python_files:
            file_replacements = self.migrate_file(file_path)
            for pattern, count in file_replacements.items():
                total_replacements[pattern] = total_replacements.get(pattern, 0) + count
        
        self.migration_report["patterns_replaced"] = total_replacements
        
        # Step 6: Create environment configuration
        if not self.create_environment_config():
            return False
        
        # Step 7: Create validation script
        if not self.create_migration_validation_script():
            return False
        
        # Step 8: Generate migration report
        if not self.generate_migration_report():
            return False
        
        # Summary
        logger.info("Migration completed successfully!")
        logger.info(f"Files modified: {len(self.migration_report['files_modified'])}")
        logger.info(f"Patterns replaced: {sum(total_replacements.values())}")
        logger.info(f"Errors: {len(self.migration_report['errors'])}")
        logger.info(f"Warnings: {len(self.migration_report['warnings'])}")
        
        if self.migration_report['errors']:
            logger.warning("Migration completed with errors. Please review the migration report.")
            return False
        
        return True


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate blackholio-agent to use blackholio-python-client"
    )
    parser.add_argument(
        "--project-path",
        default=os.path.expanduser("~/git/blackholio-agent"),
        help="Path to the blackholio-agent project (default: ~/git/blackholio-agent)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes"
    )
    
    args = parser.parse_args()
    
    # Validate project path exists
    project_path = Path(args.project_path)
    if not project_path.exists():
        logger.error(f"Project path does not exist: {project_path}")
        return 1
    
    # Run migration
    migrator = BlackholioAgentMigrator(
        project_path=str(project_path),
        dry_run=args.dry_run
    )
    
    success = migrator.run_migration()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())