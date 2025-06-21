#!/usr/bin/env python3
"""
Version Management Script for blackholio-python-client

This script handles semantic versioning, changelog generation, and release management.
Supports automated version bumping based on conventional commits and semantic versioning rules.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    # Python 3.11+
    import tomllib
    import tomli_w as toml_writer
    HAS_TOMLLIB = True
except ImportError:
    try:
        # Fallback to toml library
        import toml
        HAS_TOMLLIB = False
    except ImportError:
        # Manual TOML parsing as last resort
        import re
        HAS_TOMLLIB = False
        toml = None


class VersionManager:
    """Manages semantic versioning and release processes for the package."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize version manager with project root path."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.init_path = self.project_root / "src" / "blackholio_client" / "__init__.py"
        self.changelog_path = self.project_root / "CHANGELOG.md"
        
    def get_current_version(self) -> str:
        """Get the current version from pyproject.toml."""
        try:
            if HAS_TOMLLIB:
                with open(self.pyproject_path, 'rb') as f:
                    config = tomllib.load(f)
            elif toml:
                with open(self.pyproject_path, 'r') as f:
                    config = toml.load(f)
            else:
                # Manual parsing as fallback
                with open(self.pyproject_path, 'r') as f:
                    content = f.read()
                version_match = re.search(r'version = "([^"]+)"', content)
                if not version_match:
                    raise ValueError("Could not find version in pyproject.toml")
                return version_match.group(1)
                
            return config['project']['version']
        except (FileNotFoundError, KeyError) as e:
            raise ValueError(f"Could not read version from {self.pyproject_path}: {e}")
    
    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into major, minor, patch components."""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-.*)?$', version)
        if not match:
            raise ValueError(f"Invalid version format: {version}")
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    def format_version(self, major: int, minor: int, patch: int) -> str:
        """Format version components into version string."""
        return f"{major}.{minor}.{patch}"
    
    def bump_version(self, bump_type: str, prerelease: Optional[str] = None) -> str:
        """
        Bump version based on type (major, minor, patch).
        
        Args:
            bump_type: Type of version bump (major, minor, patch)
            prerelease: Optional prerelease identifier (alpha, beta, rc)
            
        Returns:
            New version string
        """
        current_version = self.get_current_version()
        major, minor, patch = self.parse_version(current_version)
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
        
        new_version = self.format_version(major, minor, patch)
        
        if prerelease:
            new_version += f"-{prerelease}"
        
        return new_version
    
    def update_version_files(self, new_version: str) -> None:
        """Update version in all relevant files."""
        # Update pyproject.toml
        if HAS_TOMLLIB:
            with open(self.pyproject_path, 'rb') as f:
                config = tomllib.load(f)
            config['project']['version'] = new_version
            config['tool']['commitizen']['version'] = new_version
            
            with open(self.pyproject_path, 'w') as f:
                toml_writer.dump(config, f)
        elif toml:
            with open(self.pyproject_path, 'r') as f:
                config = toml.load(f)
            config['project']['version'] = new_version
            config['tool']['commitizen']['version'] = new_version
            
            with open(self.pyproject_path, 'w') as f:
                toml.dump(config, f)
        else:
            # Manual replacement as fallback
            with open(self.pyproject_path, 'r') as f:
                content = f.read()
            
            content = re.sub(
                r'version = "[^"]*"',
                f'version = "{new_version}"',
                content,
                count=2  # Replace both project.version and tool.commitizen.version
            )
            
            with open(self.pyproject_path, 'w') as f:
                f.write(content)
        
        # Update __init__.py
        with open(self.init_path, 'r') as f:
            content = f.read()
        
        content = re.sub(
            r'__version__ = "[^"]*"',
            f'__version__ = "{new_version}"',
            content
        )
        
        with open(self.init_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated version to {new_version} in:")
        print(f"   - {self.pyproject_path}")
        print(f"   - {self.init_path}")
    
    def get_git_commits_since_last_tag(self) -> List[str]:
        """Get git commits since the last tag."""
        try:
            # Get the last tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                # No tags found, get all commits
                cmd = ["git", "log", "--oneline", "--pretty=format:%s"]
            else:
                last_tag = result.stdout.strip()
                cmd = ["git", "log", f"{last_tag}..HEAD", "--oneline", "--pretty=format:%s"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.splitlines() if line.strip()]
            else:
                return []
                
        except subprocess.SubprocessError:
            return []
    
    def analyze_commits_for_version_bump(self, commits: List[str]) -> str:
        """
        Analyze commit messages to determine version bump type.
        
        Uses conventional commits format:
        - BREAKING CHANGE or feat!: -> major
        - feat: -> minor
        - fix: -> patch
        - Other types -> patch
        """
        has_breaking = False
        has_feat = False
        has_fix = False
        
        for commit in commits:
            commit_lower = commit.lower()
            
            # Check for breaking changes
            if "breaking change" in commit_lower or re.search(r'\w+!:', commit):
                has_breaking = True
            
            # Check for features
            elif commit_lower.startswith("feat:") or commit_lower.startswith("feature:"):
                has_feat = True
            
            # Check for fixes
            elif commit_lower.startswith("fix:") or commit_lower.startswith("bugfix:"):
                has_fix = True
        
        if has_breaking:
            return "major"
        elif has_feat:
            return "minor"
        elif has_fix:
            return "patch"
        else:
            return "patch"  # Default to patch for other changes
    
    def update_changelog(self, new_version: str, commits: List[str]) -> None:
        """Update CHANGELOG.md with new version and commits."""
        if not self.changelog_path.exists():
            print(f"⚠️  Changelog not found at {self.changelog_path}")
            return
        
        with open(self.changelog_path, 'r') as f:
            content = f.read()
        
        # Parse commits into categories
        features = []
        fixes = []
        breaking = []
        others = []
        
        for commit in commits:
            commit_lower = commit.lower()
            
            if "breaking change" in commit_lower or re.search(r'\w+!:', commit):
                breaking.append(commit)
            elif commit_lower.startswith("feat:") or commit_lower.startswith("feature:"):
                features.append(commit)
            elif commit_lower.startswith("fix:") or commit_lower.startswith("bugfix:"):
                fixes.append(commit)
            else:
                others.append(commit)
        
        # Build changelog entry
        today = datetime.now().strftime("%Y-%m-%d")
        changelog_entry = f"\n## [{new_version}] - {today}\n\n"
        
        if breaking:
            changelog_entry += "### ⚠️ BREAKING CHANGES\n"
            for commit in breaking:
                changelog_entry += f"- {commit}\n"
            changelog_entry += "\n"
        
        if features:
            changelog_entry += "### Added\n"
            for commit in features:
                changelog_entry += f"- {commit}\n"
            changelog_entry += "\n"
        
        if fixes:
            changelog_entry += "### Fixed\n"
            for commit in fixes:
                changelog_entry += f"- {commit}\n"
            changelog_entry += "\n"
        
        if others:
            changelog_entry += "### Changed\n"
            for commit in others:
                changelog_entry += f"- {commit}\n"
            changelog_entry += "\n"
        
        # Insert entry after [Unreleased] section
        unreleased_pattern = r'(## \[Unreleased\].*?(?=## \[|\Z))'
        
        def replace_unreleased(match):
            unreleased_section = match.group(1)
            # Clear the unreleased section
            cleared_unreleased = re.sub(
                r'(### Added.*?)(### Changed.*?)(### Fixed.*?)(### Removed.*?)',
                '### Added\n- N/A\n\n### Changed\n- N/A\n\n### Fixed\n- N/A\n\n### Removed\n- N/A\n\n',
                unreleased_section,
                flags=re.DOTALL
            )
            return cleared_unreleased + changelog_entry
        
        content = re.sub(unreleased_pattern, replace_unreleased, content, flags=re.DOTALL)
        
        # Update links at the bottom
        current_version = self.get_current_version()
        
        # Add new version link
        if f"[{new_version}]" not in content:
            links_pattern = r'(\[Unreleased\]: https://github\.com/[^/]+/[^/]+/compare/v[^.]+\.[^.]+\.[^.]+\.\.\.HEAD\n)'
            new_link = f"[{new_version}]: https://github.com/blackholio/blackholio-python-client/releases/tag/v{new_version}\n"
            content = re.sub(links_pattern, f"\\1{new_link}", content)
        
        # Update unreleased link
        content = re.sub(
            r'\[Unreleased\]: https://github\.com/[^/]+/[^/]+/compare/v[^.]+\.[^.]+\.[^.]+\.\.\.HEAD',
            f"[Unreleased]: https://github.com/blackholio/blackholio-python-client/compare/v{new_version}...HEAD",
            content
        )
        
        with open(self.changelog_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated changelog with {len(commits)} commits")
    
    def create_git_tag(self, version: str, message: Optional[str] = None) -> None:
        """Create a git tag for the new version."""
        tag_name = f"v{version}"
        tag_message = message or f"Release {version}"
        
        try:
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                check=True,
                cwd=self.project_root
            )
            print(f"✅ Created git tag: {tag_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create git tag: {e}")
    
    def commit_version_changes(self, version: str) -> None:
        """Commit version changes to git."""
        try:
            subprocess.run(
                ["git", "add", "pyproject.toml", "src/blackholio_client/__init__.py", "CHANGELOG.md"],
                check=True,
                cwd=self.project_root
            )
            
            subprocess.run(
                ["git", "commit", "-m", f"chore: bump version to {version}"],
                check=True,
                cwd=self.project_root
            )
            
            print(f"✅ Committed version changes")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to commit changes: {e}")
    
    def release(self, bump_type: str, prerelease: Optional[str] = None, 
                auto: bool = False, dry_run: bool = False) -> str:
        """
        Perform a complete release process.
        
        Args:
            bump_type: Type of version bump or 'auto' for automatic detection
            prerelease: Optional prerelease identifier
            auto: Automatically determine bump type from commits
            dry_run: Show what would be done without making changes
            
        Returns:
            New version string
        """
        print("🚀 Starting release process...")
        
        current_version = self.get_current_version()
        print(f"📋 Current version: {current_version}")
        
        # Get commits since last tag
        commits = self.get_git_commits_since_last_tag()
        print(f"📝 Found {len(commits)} commits since last release")
        
        if auto or bump_type == "auto":
            bump_type = self.analyze_commits_for_version_bump(commits)
            print(f"🔍 Auto-detected bump type: {bump_type}")
        
        # Calculate new version
        new_version = self.bump_version(bump_type, prerelease)
        print(f"🎯 New version: {new_version}")
        
        if dry_run:
            print("\n🧪 DRY RUN - No changes will be made:")
            print(f"   - Would update version from {current_version} to {new_version}")
            print(f"   - Would update changelog with {len(commits)} commits")
            print(f"   - Would create git tag v{new_version}")
            return new_version
        
        # Confirm release
        if not auto:
            response = input(f"\n❓ Release version {new_version}? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Release cancelled")
                return current_version
        
        # Perform release steps
        try:
            self.update_version_files(new_version)
            self.update_changelog(new_version, commits)
            self.commit_version_changes(new_version)
            self.create_git_tag(new_version)
            
            print(f"\n🎉 Successfully released version {new_version}!")
            print(f"📋 Remember to push changes: git push origin main --tags")
            
        except Exception as e:
            print(f"❌ Release failed: {e}")
            return current_version
        
        return new_version


def main():
    """Main CLI interface for version management."""
    parser = argparse.ArgumentParser(
        description="Version management for blackholio-python-client"
    )
    
    parser.add_argument(
        "action",
        choices=["bump", "release", "current", "next"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch", "auto"],
        default="patch",
        help="Type of version bump (default: patch)"
    )
    
    parser.add_argument(
        "--prerelease",
        help="Prerelease identifier (alpha, beta, rc)"
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically determine bump type from commits"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    try:
        vm = VersionManager()
        
        if args.action == "current":
            version = vm.get_current_version()
            print(f"Current version: {version}")
            
        elif args.action == "next":
            bump_type = args.bump_type if not args.auto else "auto"
            if bump_type == "auto":
                commits = vm.get_git_commits_since_last_tag()
                bump_type = vm.analyze_commits_for_version_bump(commits)
            
            next_version = vm.bump_version(bump_type, args.prerelease)
            print(f"Next version ({bump_type}): {next_version}")
            
        elif args.action == "bump":
            bump_type = args.bump_type if not args.auto else "auto"
            if bump_type == "auto":
                commits = vm.get_git_commits_since_last_tag()
                bump_type = vm.analyze_commits_for_version_bump(commits)
            
            new_version = vm.bump_version(bump_type, args.prerelease)
            
            if not args.dry_run:
                vm.update_version_files(new_version)
                print(f"✅ Bumped version to {new_version}")
            else:
                print(f"🧪 DRY RUN: Would bump version to {new_version}")
            
        elif args.action == "release":
            vm.release(
                args.bump_type,
                args.prerelease,
                args.auto,
                args.dry_run
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()