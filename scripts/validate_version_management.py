#!/usr/bin/env python3
"""
Validation script for version management system.

This script validates that all version management components are working correctly
including version parsing, file updates, changelog generation, and CI/CD integration.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.version_manager import VersionManager


class VersionManagementValidator:
    """Validates the version management system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.vm = VersionManager(self.project_root)
        self.passed_tests = 0
        self.total_tests = 0
        
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a test and track results."""
        self.total_tests += 1
        try:
            test_func()
            print(f"✅ {test_name}")
            self.passed_tests += 1
            return True
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            return False
    
    def test_version_parsing(self) -> None:
        """Test version string parsing."""
        # Test valid versions
        assert self.vm.parse_version("1.2.3") == (1, 2, 3)
        assert self.vm.parse_version("0.1.0") == (0, 1, 0)
        assert self.vm.parse_version("10.20.30") == (10, 20, 30)
        assert self.vm.parse_version("1.2.3-alpha") == (1, 2, 3)
        
        # Test invalid versions
        try:
            self.vm.parse_version("invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    
    def test_version_formatting(self) -> None:
        """Test version formatting."""
        assert self.vm.format_version(1, 2, 3) == "1.2.3"
        assert self.vm.format_version(0, 1, 0) == "0.1.0"
        assert self.vm.format_version(10, 20, 30) == "10.20.30"
    
    def test_version_bumping(self) -> None:
        """Test version bumping logic."""
        # Test from current version 0.1.0
        current = self.vm.get_current_version()
        major, minor, patch = self.vm.parse_version(current)
        
        # Test patch bump
        patch_version = self.vm.bump_version("patch")
        assert patch_version == f"{major}.{minor}.{patch + 1}"
        
        # Test minor bump
        minor_version = self.vm.bump_version("minor")
        assert minor_version == f"{major}.{minor + 1}.0"
        
        # Test major bump
        major_version = self.vm.bump_version("major")
        assert major_version == f"{major + 1}.0.0"
    
    def test_prerelease_versions(self) -> None:
        """Test prerelease version handling."""
        alpha_version = self.vm.bump_version("patch", "alpha")
        assert alpha_version.endswith("-alpha")
        
        beta_version = self.vm.bump_version("minor", "beta")
        assert beta_version.endswith("-beta")
        
        rc_version = self.vm.bump_version("major", "rc")
        assert rc_version.endswith("-rc")
    
    def test_current_version_reading(self) -> None:
        """Test reading current version from files."""
        version = self.vm.get_current_version()
        assert version is not None
        assert isinstance(version, str)
        assert len(version.split('.')) == 3
    
    def test_commit_analysis(self) -> None:
        """Test commit message analysis for version bumping."""
        # Test different commit types
        feat_commits = ["feat: add new feature"]
        fix_commits = ["fix: resolve bug"]
        breaking_commits = ["feat!: breaking change", "feat: new feature\n\nBREAKING CHANGE: API changed"]
        
        assert self.vm.analyze_commits_for_version_bump(feat_commits) == "minor"
        assert self.vm.analyze_commits_for_version_bump(fix_commits) == "patch"
        assert self.vm.analyze_commits_for_version_bump(breaking_commits) == "major"
        
        # Test mixed commits (should use highest priority)
        mixed_commits = ["fix: bug fix", "feat: new feature"]
        assert self.vm.analyze_commits_for_version_bump(mixed_commits) == "minor"
        
        mixed_breaking = ["fix: bug fix", "feat!: breaking change"]
        assert self.vm.analyze_commits_for_version_bump(mixed_breaking) == "major"
    
    def test_git_integration(self) -> None:
        """Test git integration functions."""
        # Test getting commits (may be empty in CI)
        commits = self.vm.get_git_commits_since_last_tag()
        assert isinstance(commits, list)
        
        # All commits should be strings
        for commit in commits:
            assert isinstance(commit, str)
    
    def test_file_structure(self) -> None:
        """Test that required files exist."""
        required_files = [
            self.vm.pyproject_path,
            self.vm.init_path,
            self.vm.changelog_path,
            self.project_root / "scripts" / "version_manager.py",
            self.project_root / "scripts" / "release.sh",
        ]
        
        for file_path in required_files:
            assert file_path.exists(), f"Required file missing: {file_path}"
    
    def test_version_consistency(self) -> None:
        """Test version consistency across files."""
        # Get version from pyproject.toml
        pyproject_version = self.vm.get_current_version()
        
        # Get version from __init__.py
        with open(self.vm.init_path, 'r') as f:
            content = f.read()
        
        import re
        version_match = re.search(r'__version__ = "([^"]+)"', content)
        assert version_match, "Could not find __version__ in __init__.py"
        init_version = version_match.group(1)
        
        assert pyproject_version == init_version, f"Version mismatch: pyproject.toml={pyproject_version}, __init__.py={init_version}"
    
    def test_changelog_structure(self) -> None:
        """Test changelog structure and format."""
        with open(self.vm.changelog_path, 'r') as f:
            content = f.read()
        
        # Check for required sections
        assert "# Changelog" in content
        assert "## [Unreleased]" in content
        assert "### Added" in content
        assert "### Changed" in content
        assert "### Fixed" in content
        assert "### Removed" in content
        
        # Check for current version
        current_version = self.vm.get_current_version()
        assert f"[{current_version}]" in content
    
    def test_makefile_integration(self) -> None:
        """Test Makefile version commands."""
        makefile_path = self.project_root / "Makefile"
        assert makefile_path.exists(), "Makefile not found"
        
        with open(makefile_path, 'r') as f:
            content = f.read()
        
        # Check for version management targets
        required_targets = [
            "version:",
            "version-next:",
            "version-bump-patch:",
            "version-bump-minor:",
            "version-bump-major:",
            "release-patch:",
            "release-minor:",
            "release-major:",
            "release-auto:",
        ]
        
        for target in required_targets:
            assert target in content, f"Missing Makefile target: {target}"
    
    def test_github_actions_integration(self) -> None:
        """Test GitHub Actions workflow integration."""
        workflow_path = self.project_root / ".github" / "workflows" / "release.yml"
        assert workflow_path.exists(), "Release workflow not found"
        
        with open(workflow_path, 'r') as f:
            content = f.read()
        
        # Check for version management integration
        assert "scripts/version_manager.py" in content
        assert "validate-release" in content
        assert "build-package" in content
        assert "create-release" in content
    
    def test_script_permissions(self) -> None:
        """Test that scripts have correct permissions."""
        release_script = self.project_root / "scripts" / "release.sh"
        assert release_script.exists(), "Release script not found"
        
        # Check if script is executable
        stat_info = release_script.stat()
        assert stat_info.st_mode & 0o111, "Release script is not executable"
    
    def test_documentation(self) -> None:
        """Test that version management documentation exists."""
        docs = [
            self.project_root / "docs" / "VERSION_MANAGEMENT.md",
            self.project_root / "CHANGELOG.md",
        ]
        
        for doc in docs:
            assert doc.exists(), f"Documentation file missing: {doc}"
            
            # Check file is not empty
            assert doc.stat().st_size > 0, f"Documentation file is empty: {doc}"
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Run all validation tests."""
        print("🔍 Validating Version Management System")
        print("=" * 50)
        
        # Run all tests
        self.run_test("Version parsing", self.test_version_parsing)
        self.run_test("Version formatting", self.test_version_formatting)
        self.run_test("Version bumping", self.test_version_bumping)
        self.run_test("Prerelease versions", self.test_prerelease_versions)
        self.run_test("Current version reading", self.test_current_version_reading)
        self.run_test("Commit analysis", self.test_commit_analysis)
        self.run_test("Git integration", self.test_git_integration)
        self.run_test("File structure", self.test_file_structure)
        self.run_test("Version consistency", self.test_version_consistency)
        self.run_test("Changelog structure", self.test_changelog_structure)
        self.run_test("Makefile integration", self.test_makefile_integration)
        self.run_test("GitHub Actions integration", self.test_github_actions_integration)
        self.run_test("Script permissions", self.test_script_permissions)
        self.run_test("Documentation", self.test_documentation)
        
        return self.passed_tests, self.total_tests


def main():
    """Main validation function."""
    validator = VersionManagementValidator()
    passed, total = validator.run_all_tests()
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All version management tests passed!")
        print("\n✅ Version management system is ready for production use")
        return 0
    else:
        failed = total - passed
        print(f"❌ {failed} test(s) failed")
        print("\n⚠️  Version management system needs attention before use")
        return 1


if __name__ == "__main__":
    sys.exit(main())