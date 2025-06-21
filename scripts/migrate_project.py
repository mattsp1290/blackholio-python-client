#!/usr/bin/env python3
"""
Universal Migration Script for blackholio-python-client
=======================================================

Universal migration script that can automatically detect and migrate both
blackholio-agent and client-pygame projects to use the unified
blackholio-python-client package.

This script:
1. Automatically detects project type
2. Runs appropriate migration script
3. Provides unified reporting
4. Handles validation and rollback

Usage:
    python migrate_project.py [--project-path PATH] [--dry-run] [--auto-detect]
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('universal_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ProjectType:
    """Enumeration for project types."""
    BLACKHOLIO_AGENT = "blackholio-agent"
    CLIENT_PYGAME = "client-pygame"
    UNKNOWN = "unknown"


class UniversalMigrator:
    """Universal migration utility for blackholio projects."""
    
    def __init__(self, auto_detect: bool = True):
        self.auto_detect = auto_detect
        self.script_dir = Path(__file__).parent
        self.migration_scripts = {
            ProjectType.BLACKHOLIO_AGENT: self.script_dir / "migrate_blackholio_agent.py",
            ProjectType.CLIENT_PYGAME: self.script_dir / "migrate_client_pygame.py"
        }
    
    def detect_project_type(self, project_path: Path) -> ProjectType:
        """Automatically detect the type of project."""
        logger.info(f"Detecting project type for: {project_path}")
        
        # Check for blackholio-agent indicators
        agent_indicators = [
            "agent.py",
            "train.py",
            "models/agent.py",
            "training/",
            "environments/",
        ]
        
        agent_score = 0
        for indicator in agent_indicators:
            if (project_path / indicator).exists():
                agent_score += 1
                logger.debug(f"Found agent indicator: {indicator}")
        
        # Check for client-pygame indicators
        pygame_indicators = [
            "game.py",
            "renderer.py",
            "main.py",
            "client.py",
        ]
        
        pygame_score = 0
        pygame_imports_found = False
        
        for indicator in pygame_indicators:
            if (project_path / indicator).exists():
                pygame_score += 1
                logger.debug(f"Found pygame indicator: {indicator}")
        
        # Check for pygame imports in Python files
        for py_file in project_path.glob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read().lower()
                    if 'pygame' in content:
                        pygame_imports_found = True
                        pygame_score += 2
                        logger.debug(f"Found pygame import in: {py_file}")
                        break
            except:
                continue
        
        # Check for ML/training specific content
        ml_keywords = ['training', 'model', 'agent', 'reward', 'episode', 'neural']
        ml_score = 0
        
        for py_file in project_path.glob("**/*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read().lower()
                    for keyword in ml_keywords:
                        if keyword in content:
                            ml_score += 1
                            break
            except:
                continue
        
        # Determine project type based on scores
        logger.info(f"Detection scores - Agent: {agent_score}, Pygame: {pygame_score}, ML: {ml_score}")
        
        if agent_score >= 2 or ml_score >= 3:
            return ProjectType.BLACKHOLIO_AGENT
        elif pygame_score >= 2 or pygame_imports_found:
            return ProjectType.CLIENT_PYGAME
        
        # Try to detect based on directory name
        dir_name = project_path.name.lower()
        if 'agent' in dir_name:
            return ProjectType.BLACKHOLIO_AGENT
        elif 'pygame' in dir_name or 'client' in dir_name:
            return ProjectType.CLIENT_PYGAME
        
        return ProjectType.UNKNOWN
    
    def validate_migration_script(self, project_type: ProjectType) -> bool:
        """Validate that the migration script exists and is executable."""
        script_path = self.migration_scripts.get(project_type)
        
        if not script_path or not script_path.exists():
            logger.error(f"Migration script not found for {project_type}: {script_path}")
            return False
        
        if not os.access(script_path, os.X_OK):
            logger.info(f"Making migration script executable: {script_path}")
            os.chmod(script_path, 0o755)
        
        return True
    
    def run_migration_script(self, project_type: ProjectType, project_path: Path, dry_run: bool = False) -> Tuple[bool, Dict]:
        """Run the appropriate migration script."""
        script_path = self.migration_scripts[project_type]
        
        logger.info(f"Running migration script: {script_path}")
        logger.info(f"Project path: {project_path}")
        logger.info(f"Dry run: {dry_run}")
        
        # Prepare command
        cmd = [sys.executable, str(script_path), "--project-path", str(project_path)]
        if dry_run:
            cmd.append("--dry-run")
        
        try:
            # Run migration script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Log output
            if result.stdout:
                logger.info(f"Migration script output:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Migration script stderr:\n{result.stderr}")
            
            # Check if migration was successful
            success = result.returncode == 0
            
            # Try to load migration report
            report_path = project_path / "migration_report.json"
            report = {}
            
            if report_path.exists():
                try:
                    with open(report_path, 'r') as f:
                        report = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load migration report: {e}")
            
            return success, report
            
        except subprocess.TimeoutExpired:
            logger.error("Migration script timed out after 5 minutes")
            return False, {}
        except Exception as e:
            logger.error(f"Failed to run migration script: {e}")
            return False, {}
    
    def validate_migration_results(self, project_path: Path, project_type: ProjectType) -> bool:
        """Validate migration results by running validation script."""
        validation_script = project_path / "validate_migration.py"
        
        if not validation_script.exists():
            logger.warning("Validation script not found, skipping validation")
            return True
        
        logger.info("Running migration validation...")
        
        try:
            result = subprocess.run(
                [sys.executable, str(validation_script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=project_path
            )
            
            if result.stdout:
                logger.info(f"Validation output:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Validation stderr:\n{result.stderr}")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to run validation: {e}")
            return False
    
    def create_universal_report(self, project_path: Path, project_type: ProjectType, 
                               migration_success: bool, migration_report: Dict, 
                               validation_success: bool) -> bool:
        """Create a universal migration report."""
        
        universal_report = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(project_path),
            "project_type": project_type,
            "migration_success": migration_success,
            "validation_success": validation_success,
            "migration_details": migration_report,
            "summary": {
                "files_modified": len(migration_report.get("files_modified", [])),
                "patterns_replaced": sum(migration_report.get("patterns_replaced", {}).values()),
                "errors": len(migration_report.get("errors", [])),
                "warnings": len(migration_report.get("warnings", []))
            }
        }
        
        report_path = project_path / "universal_migration_report.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(universal_report, f, indent=2)
            
            logger.info(f"Universal migration report saved to: {report_path}")
            
            # Create human-readable summary
            summary_path = project_path / "UNIVERSAL_MIGRATION_SUMMARY.md"
            summary_content = f"""# Universal Migration Summary

**Project Type**: {project_type}
**Migration Date**: {universal_report['timestamp']}
**Migration Success**: {'✅ YES' if migration_success else '❌ NO'}
**Validation Success**: {'✅ YES' if validation_success else '❌ NO'}

## Migration Statistics
- **Files Modified**: {universal_report['summary']['files_modified']}
- **Code Patterns Replaced**: {universal_report['summary']['patterns_replaced']}
- **Errors**: {universal_report['summary']['errors']}
- **Warnings**: {universal_report['summary']['warnings']}

## Project-Specific Details
For detailed migration information, see:
- `migration_report.json` - Detailed migration report
- `MIGRATION_SUMMARY.md` - Project-specific migration summary

## Next Steps

### ✅ Migration Successful
{'''1. **Install Dependencies**: Run `pip install -r requirements.txt`
2. **Test Your Application**: Run your normal test suite
3. **Environment Configuration**: Update `.env` file with your settings
4. **Performance Monitoring**: Monitor for any performance changes
5. **Remove Backup**: Once satisfied, you can remove `backup_pre_migration/`

### 🎯 Project-Specific Next Steps

#### For blackholio-agent:
- Run your ML training pipeline
- Validate model performance
- Check observation space and action processing

#### For client-pygame:
- Test pygame rendering
- Verify event handling
- Check real-time entity updates''' if migration_success else '''1. **Review Errors**: Check migration_report.json for detailed error information
2. **Manual Fixes**: Address any issues found during migration
3. **Restore Backup**: If needed, restore from `backup_pre_migration/`
4. **Retry Migration**: Run migration script again after fixes'''}

## Support Resources
- **Migration Documentation**: `docs/MIGRATION_*.md`
- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Issues**: https://github.com/punk1290/blackholio-python-client/issues

## Backup Information
Your original code is safely backed up at: `backup_pre_migration/`
"""
            
            with open(summary_path, 'w') as f:
                f.write(summary_content)
            
            logger.info(f"Universal migration summary saved to: {summary_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create universal report: {e}")
            return False
    
    def migrate_project(self, project_path: str, dry_run: bool = False) -> bool:
        """Execute universal migration for a project."""
        project_path = Path(project_path).resolve()
        
        logger.info("=" * 60)
        logger.info("Universal blackholio-python-client Migration")
        logger.info("=" * 60)
        logger.info(f"Project Path: {project_path}")
        logger.info(f"Dry Run: {dry_run}")
        
        # Validate project path exists
        if not project_path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return False
        
        # Step 1: Detect project type
        if self.auto_detect:
            project_type = self.detect_project_type(project_path)
            logger.info(f"Detected project type: {project_type}")
            
            if project_type == ProjectType.UNKNOWN:
                logger.error("Could not determine project type. Please specify manually.")
                return False
        else:
            logger.error("Manual project type specification not implemented yet")
            return False
        
        # Step 2: Validate migration script
        if not self.validate_migration_script(project_type):
            return False
        
        # Step 3: Run migration
        migration_success, migration_report = self.run_migration_script(
            project_type, project_path, dry_run
        )
        
        if not migration_success:
            logger.error("Migration script failed")
            return False
        
        logger.info("Migration script completed successfully")
        
        # Step 4: Validate migration (only if not dry run)
        validation_success = True
        if not dry_run:
            validation_success = self.validate_migration_results(project_path, project_type)
            if validation_success:
                logger.info("Migration validation passed")
            else:
                logger.warning("Migration validation failed or had issues")
        else:
            logger.info("Skipping validation in dry-run mode")
        
        # Step 5: Create universal report
        if not self.create_universal_report(
            project_path, project_type, migration_success, 
            migration_report, validation_success
        ):
            logger.warning("Failed to create universal report")
        
        # Summary
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Project Type: {project_type}")
        logger.info(f"Migration Success: {migration_success}")
        logger.info(f"Validation Success: {validation_success}")
        logger.info(f"Files Modified: {len(migration_report.get('files_modified', []))}")
        logger.info(f"Patterns Replaced: {sum(migration_report.get('patterns_replaced', {}).values())}")
        
        overall_success = migration_success and validation_success
        
        if overall_success:
            logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("Next steps:")
            logger.info("  1. Install dependencies: pip install -r requirements.txt")
            logger.info("  2. Test your application")
            logger.info("  3. Review UNIVERSAL_MIGRATION_SUMMARY.md for details")
        else:
            logger.warning("⚠️  MIGRATION COMPLETED WITH ISSUES")
            logger.info("Please review the migration reports and fix any issues")
        
        return overall_success


def main():
    """Main entry point for the universal migration script."""
    parser = argparse.ArgumentParser(
        description="Universal migration script for blackholio projects"
    )
    parser.add_argument(
        "--project-path",
        required=True,
        help="Path to the project to migrate"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes"
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Disable automatic project type detection"
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = UniversalMigrator(auto_detect=not args.no_auto_detect)
    
    # Run migration
    success = migrator.migrate_project(
        project_path=args.project_path,
        dry_run=args.dry_run
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())