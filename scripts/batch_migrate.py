#!/usr/bin/env python3
"""
Batch Migration Script for blackholio-python-client
===================================================

Batch migration script that can migrate multiple blackholio projects
simultaneously. Useful for migrating both blackholio-agent and client-pygame
in a single operation.

This script:
1. Discovers blackholio projects in specified directories
2. Runs parallel migrations with progress tracking
3. Provides consolidated reporting
4. Handles error recovery and rollback

Usage:
    python batch_migrate.py [--search-paths PATH1 PATH2] [--dry-run] [--parallel]
"""

import os
import sys
import json
import argparse
import concurrent.futures
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Thread-safe logging
log_lock = threading.Lock()


class BatchMigrator:
    """Batch migration utility for multiple blackholio projects."""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.script_dir = Path(__file__).parent
        self.universal_migrator = self.script_dir / "migrate_project.py"
        self.results = []
    
    def discover_projects(self, search_paths: List[str]) -> List[Tuple[Path, str]]:
        """Discover blackholio projects in specified search paths."""
        logger.info(f"Discovering projects in: {search_paths}")
        
        projects = []
        
        for search_path in search_paths:
            search_path = Path(search_path).expanduser().resolve()
            
            if not search_path.exists():
                logger.warning(f"Search path does not exist: {search_path}")
                continue
            
            logger.info(f"Searching in: {search_path}")
            
            # Look for potential project directories
            for item in search_path.iterdir():
                if not item.is_dir():
                    continue
                
                # Skip common non-project directories
                skip_patterns = [
                    '.git', '__pycache__', '.venv', 'venv', 'env',
                    'node_modules', '.idea', '.vscode'
                ]
                
                if any(pattern in item.name.lower() for pattern in skip_patterns):
                    continue
                
                project_type = self.detect_project_type(item)
                if project_type != "unknown":
                    projects.append((item, project_type))
                    logger.info(f"Found {project_type} project: {item}")
        
        logger.info(f"Discovered {len(projects)} projects")
        return projects
    
    def detect_project_type(self, project_path: Path) -> str:
        """Quick project type detection."""
        
        # Check for blackholio-agent indicators
        agent_indicators = [
            "agent.py",
            "train.py",
            "models/agent.py",
        ]
        
        agent_score = sum(1 for indicator in agent_indicators if (project_path / indicator).exists())
        
        # Check for client-pygame indicators
        pygame_indicators = [
            "game.py",
            "renderer.py",
            "main.py",
        ]
        
        pygame_score = sum(1 for indicator in pygame_indicators if (project_path / indicator).exists())
        
        # Check for pygame imports
        pygame_imports = False
        try:
            for py_file in project_path.glob("*.py"):
                with open(py_file, 'r') as f:
                    if 'pygame' in f.read().lower():
                        pygame_imports = True
                        break
        except:
            pass
        
        # Determine type
        if agent_score >= 1:
            return "blackholio-agent"
        elif pygame_score >= 1 or pygame_imports:
            return "client-pygame"
        elif 'agent' in project_path.name.lower():
            return "blackholio-agent"
        elif 'pygame' in project_path.name.lower() or 'client' in project_path.name.lower():
            return "client-pygame"
        
        return "unknown"
    
    def migrate_single_project(self, project_info: Tuple[Path, str], dry_run: bool = False) -> Dict:
        """Migrate a single project."""
        project_path, project_type = project_info
        
        with log_lock:
            logger.info(f"Starting migration for {project_type}: {project_path}")
        
        import subprocess
        
        # Prepare command
        cmd = [
            sys.executable,
            str(self.universal_migrator),
            "--project-path", str(project_path)
        ]
        
        if dry_run:
            cmd.append("--dry-run")
        
        start_time = datetime.now()
        
        try:
            # Run migration
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout per project
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Parse results
            success = result.returncode == 0
            
            migration_result = {
                "project_path": str(project_path),
                "project_type": project_type,
                "success": success,
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            # Try to load detailed migration report
            report_path = project_path / "migration_report.json"
            if report_path.exists():
                try:
                    with open(report_path, 'r') as f:
                        migration_result["detailed_report"] = json.load(f)
                except Exception as e:
                    migration_result["report_load_error"] = str(e)
            
            with log_lock:
                if success:
                    logger.info(f"✅ Successfully migrated {project_type}: {project_path} ({duration:.1f}s)")
                else:
                    logger.error(f"❌ Failed to migrate {project_type}: {project_path} ({duration:.1f}s)")
            
            return migration_result
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            with log_lock:
                logger.error(f"⏰ Migration timed out for {project_type}: {project_path} ({duration:.1f}s)")
            
            return {
                "project_path": str(project_path),
                "project_type": project_type,
                "success": False,
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "error": "Migration timed out after 10 minutes",
                "return_code": -1
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            with log_lock:
                logger.error(f"💥 Migration failed with exception for {project_type}: {project_path} - {e}")
            
            return {
                "project_path": str(project_path),
                "project_type": project_type,
                "success": False,
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "error": str(e),
                "return_code": -1
            }
    
    def migrate_parallel(self, projects: List[Tuple[Path, str]], dry_run: bool = False) -> List[Dict]:
        """Migrate multiple projects in parallel."""
        logger.info(f"Starting parallel migration of {len(projects)} projects (max workers: {self.max_workers})")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all migration tasks
            future_to_project = {
                executor.submit(self.migrate_single_project, project, dry_run): project
                for project in projects
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {project}: {e}")
                    results.append({
                        "project_path": str(project[0]),
                        "project_type": project[1],
                        "success": False,
                        "error": f"Future execution error: {e}",
                        "return_code": -1
                    })
        
        return results
    
    def migrate_sequential(self, projects: List[Tuple[Path, str]], dry_run: bool = False) -> List[Dict]:
        """Migrate projects one by one."""
        logger.info(f"Starting sequential migration of {len(projects)} projects")
        
        results = []
        for i, project in enumerate(projects, 1):
            logger.info(f"Progress: {i}/{len(projects)} projects")
            result = self.migrate_single_project(project, dry_run)
            results.append(result)
        
        return results
    
    def generate_batch_report(self, results: List[Dict], output_dir: Path) -> bool:
        """Generate comprehensive batch migration report."""
        
        # Calculate statistics
        total_projects = len(results)
        successful_migrations = sum(1 for r in results if r.get("success", False))
        failed_migrations = total_projects - successful_migrations
        
        total_duration = sum(r.get("duration_seconds", 0) for r in results)
        
        # Group by project type
        by_type = {}
        for result in results:
            project_type = result.get("project_type", "unknown")
            if project_type not in by_type:
                by_type[project_type] = {"total": 0, "successful": 0, "failed": 0}
            
            by_type[project_type]["total"] += 1
            if result.get("success", False):
                by_type[project_type]["successful"] += 1
            else:
                by_type[project_type]["failed"] += 1
        
        # Create batch report
        batch_report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_projects": total_projects,
                "successful_migrations": successful_migrations,
                "failed_migrations": failed_migrations,
                "success_rate": (successful_migrations / total_projects * 100) if total_projects > 0 else 0,
                "total_duration_seconds": total_duration,
                "average_duration_seconds": (total_duration / total_projects) if total_projects > 0 else 0
            },
            "by_project_type": by_type,
            "detailed_results": results
        }
        
        # Save JSON report
        json_report_path = output_dir / "batch_migration_report.json"
        try:
            with open(json_report_path, 'w') as f:
                json.dump(batch_report, f, indent=2)
            logger.info(f"Batch migration report saved to: {json_report_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
            return False
        
        # Create human-readable summary
        markdown_report_path = output_dir / "BATCH_MIGRATION_SUMMARY.md"
        
        success_emoji = "✅" if failed_migrations == 0 else "⚠️"
        
        markdown_content = f"""# Batch Migration Summary {success_emoji}

**Migration Date**: {batch_report['timestamp']}
**Total Projects**: {total_projects}
**Success Rate**: {batch_report['summary']['success_rate']:.1f}%

## Overall Statistics
- ✅ **Successful Migrations**: {successful_migrations}
- ❌ **Failed Migrations**: {failed_migrations}
- ⏱️ **Total Duration**: {total_duration:.1f} seconds
- 📊 **Average Duration**: {batch_report['summary']['average_duration_seconds']:.1f} seconds per project

## By Project Type
{chr(10).join(f"### {ptype}\\n- Total: {stats['total']}\\n- Successful: {stats['successful']}\\n- Failed: {stats['failed']}\\n" for ptype, stats in by_type.items())}

## Detailed Results

| Project | Type | Status | Duration | Path |
|---------|------|--------|----------|------|
{chr(10).join(f"| {Path(r['project_path']).name} | {r['project_type']} | {'✅ Success' if r.get('success') else '❌ Failed'} | {r.get('duration_seconds', 0):.1f}s | `{r['project_path']}` |" for r in results)}

## Failed Migrations
{chr(10).join(f"### {Path(r['project_path']).name}\\n- **Error**: {r.get('error', 'Unknown error')}\\n- **Path**: `{r['project_path']}`\\n" for r in results if not r.get('success', False)) if failed_migrations > 0 else "None! 🎉"}

## Next Steps

### For Successful Migrations
1. **Install Dependencies**: Run `pip install -r requirements.txt` in each project
2. **Test Applications**: Run your normal test suites
3. **Review Migration Reports**: Check individual `MIGRATION_SUMMARY.md` files
4. **Environment Configuration**: Update `.env` files as needed

### For Failed Migrations
1. **Review Error Messages**: Check the error details above
2. **Manual Migration**: Consider manual migration steps
3. **Report Issues**: Submit issues to the blackholio-python-client repository

## Support Resources
- **Migration Documentation**: Check individual project migration guides
- **Troubleshooting**: See docs/TROUBLESHOOTING.md
- **Issues**: https://github.com/punk1290/blackholio-python-client/issues

---
*Generated by blackholio-python-client batch migration tool*
"""
        
        try:
            with open(markdown_report_path, 'w') as f:
                f.write(markdown_content)
            logger.info(f"Batch migration summary saved to: {markdown_report_path}")
        except Exception as e:
            logger.error(f"Failed to save markdown summary: {e}")
            return False
        
        return True
    
    def run_batch_migration(self, search_paths: List[str], dry_run: bool = False, 
                           parallel: bool = True, output_dir: Optional[str] = None) -> bool:
        """Execute batch migration process."""
        
        logger.info("=" * 70)
        logger.info("Batch Migration for blackholio-python-client")
        logger.info("=" * 70)
        
        # Set output directory
        if output_dir:
            output_dir = Path(output_dir).resolve()
        else:
            output_dir = Path.cwd()
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Discover projects
        projects = self.discover_projects(search_paths)
        
        if not projects:
            logger.warning("No blackholio projects found in specified paths")
            return False
        
        logger.info(f"Found {len(projects)} projects to migrate")
        for project_path, project_type in projects:
            logger.info(f"  - {project_type}: {project_path}")
        
        # Step 2: Run migrations
        if parallel and len(projects) > 1:
            results = self.migrate_parallel(projects, dry_run)
        else:
            results = self.migrate_sequential(projects, dry_run)
        
        # Step 3: Generate batch report
        if not self.generate_batch_report(results, output_dir):
            logger.warning("Failed to generate batch report")
        
        # Step 4: Summary
        successful = sum(1 for r in results if r.get("success", False))
        total = len(results)
        
        logger.info("=" * 70)
        logger.info("Batch Migration Complete")
        logger.info("=" * 70)
        logger.info(f"Projects Processed: {total}")
        logger.info(f"Successful Migrations: {successful}")
        logger.info(f"Failed Migrations: {total - successful}")
        logger.info(f"Success Rate: {(successful / total * 100):.1f}%")
        
        if successful == total:
            logger.info("🎉 ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
        elif successful > 0:
            logger.warning(f"⚠️  PARTIAL SUCCESS: {successful}/{total} migrations completed")
        else:
            logger.error("❌ ALL MIGRATIONS FAILED")
        
        logger.info(f"Detailed reports saved to: {output_dir}")
        
        return successful == total


def main():
    """Main entry point for batch migration script."""
    parser = argparse.ArgumentParser(
        description="Batch migration script for multiple blackholio projects"
    )
    parser.add_argument(
        "--search-paths",
        nargs="+",
        default=["~/git"],
        help="Paths to search for blackholio projects (default: ~/git)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without making changes"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run migrations sequentially instead of in parallel"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Maximum number of parallel workers (default: 2)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save batch migration reports (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Create batch migrator
    migrator = BatchMigrator(max_workers=args.max_workers)
    
    # Run batch migration
    success = migrator.run_batch_migration(
        search_paths=args.search_paths,
        dry_run=args.dry_run,
        parallel=not args.sequential,
        output_dir=args.output_dir
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())