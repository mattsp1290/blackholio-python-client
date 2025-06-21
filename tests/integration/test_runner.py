"""
Integration test runner for blackholio-python-client.

Provides utilities to run integration tests against real SpacetimeDB servers
with proper setup and teardown.
"""

import asyncio
import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from blackholio_client.config.environment import EnvironmentConfig


class IntegrationTestRunner:
    """Manages integration test execution with real SpacetimeDB servers."""
    
    def __init__(self, server_languages: Optional[List[str]] = None):
        self.server_languages = server_languages or ["rust"]
        self.spacetime_cli = "/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli"
        self.server_base = "/Users/punk1290/git/Blackholio"
        self.test_processes: Dict[str, subprocess.Popen] = {}
        self.test_ports = {"rust": 3000, "python": 3001, "csharp": 3002, "go": 3003}
        
    def check_prerequisites(self) -> Tuple[bool, List[str]]:
        """Check if all prerequisites are available."""
        issues = []
        
        # Check SpacetimeDB CLI
        if not os.path.exists(self.spacetime_cli):
            issues.append(f"SpacetimeDB CLI not found at {self.spacetime_cli}")
        elif not os.access(self.spacetime_cli, os.X_OK):
            issues.append(f"SpacetimeDB CLI not executable at {self.spacetime_cli}")
        
        # Check SpacetimeDB server is running
        if not self._check_server_running():
            issues.append("SpacetimeDB server not running on port 3000 - please start server before running integration tests")
        
        # Check server implementations
        for language in self.server_languages:
            server_path = f"{self.server_base}/server-{language}"
            if not os.path.exists(server_path):
                issues.append(f"{language} server not found at {server_path}")
                continue
            
            # Check language-specific files
            if language == "rust" and not os.path.exists(f"{server_path}/Cargo.toml"):
                issues.append(f"Rust server missing Cargo.toml")
            elif language == "python" and not os.path.exists(f"{server_path}/Cargo.toml"):
                issues.append(f"Python server missing Cargo.toml")
            elif language == "csharp" and not os.path.exists(f"{server_path}/StdbModule.csproj"):
                issues.append(f"C# server missing StdbModule.csproj")
            elif language == "go" and not os.path.exists(f"{server_path}/go.mod"):
                issues.append(f"Go server missing go.mod")
        
        return len(issues) == 0, issues
    
    def _check_server_running(self) -> bool:
        """Check if SpacetimeDB server is running."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 3000), timeout=5):
                return True
        except (socket.error, ConnectionRefusedError):
            return False
    
    def setup_test_environment(self, language: str) -> bool:
        """Setup test environment for the specified language."""
        server_path = f"{self.server_base}/server-{language}"
        
        print(f"Setting up test environment for {language} server...")
        
        try:
            # Generate client code for testing
            gen_cmd = [
                self.spacetime_cli,
                "generate", 
                "--lang", "python",
                "--out-dir", f"/tmp/spacetime_test_{language}",
                "--project-path", server_path
            ]
            
            gen_result = subprocess.run(gen_cmd, capture_output=True, text=True, timeout=60)
            if gen_result.returncode != 0:
                print(f"Client generation failed for {language}: {gen_result.stderr}")
                return False
            
            print(f"✓ {language} test environment setup successfully")
            return True
            
        except Exception as e:
            print(f"Error setting up test environment for {language}: {e}")
            return False
    
    def run_tests(self, test_pattern: str = "tests/integration/", verbose: bool = False) -> bool:
        """Run integration tests."""
        print(f"Running integration tests: {test_pattern}")
        
        # Build pytest command
        cmd = ["pytest", test_pattern]
        
        if verbose:
            cmd.append("-v")
        
        # Add coverage if available
        cmd.extend(["--cov=blackholio_client", "--cov-report=term-missing"])
        
        # Add markers for integration tests
        cmd.extend(["-m", "not slow"])
        
        try:
            result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
            return result.returncode == 0
        except Exception as e:
            print(f"Error running tests: {e}")
            return False
    
    def run_full_integration_test(self, verbose: bool = False) -> bool:
        """Run complete integration test suite."""
        print("=" * 60)
        print("BLACKHOLIO PYTHON CLIENT - INTEGRATION TESTS")
        print("=" * 60)
        
        # Check prerequisites
        prereqs_ok, issues = self.check_prerequisites()
        if not prereqs_ok:
            print("Prerequisites check failed:")
            for issue in issues:
                print(f"  ✗ {issue}")
            return False
        
        print("✓ Prerequisites check passed")
        print("✓ SpacetimeDB server is running on port 3000")
        
        # Setup test environments
        environments_setup = []
        for language in self.server_languages:
            if self.setup_test_environment(language):
                environments_setup.append(language)
            else:
                print(f"✗ Failed to setup test environment for {language}")
        
        if not environments_setup:
            print("✗ No test environments could be setup")
            return False
        
        print(f"✓ Setup {len(environments_setup)} test environment(s): {', '.join(environments_setup)}")
        
        # Run tests
        print("\nRunning integration tests...")
        test_success = self.run_tests(verbose=verbose)
        
        if test_success:
            print("✓ All integration tests passed!")
        else:
            print("✗ Some integration tests failed")
        
        return test_success


def main():
    """Main entry point for integration test runner."""
    parser = argparse.ArgumentParser(description="Run blackholio-python-client integration tests")
    parser.add_argument(
        "--languages", 
        nargs="+", 
        default=["rust"],
        choices=["rust", "python", "csharp", "go"],
        help="Server languages to test (default: rust)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "--test-pattern",
        default="tests/integration/",
        help="Test pattern to run (default: tests/integration/)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true", 
        help="Only check prerequisites, don't run tests"
    )
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(args.languages)
    
    if args.check_only:
        prereqs_ok, issues = runner.check_prerequisites()
        if prereqs_ok:
            print("✓ All prerequisites available")
            return 0
        else:
            print("✗ Prerequisites check failed:")
            for issue in issues:
                print(f"  {issue}")
            return 1
    
    # Run full integration test
    success = runner.run_full_integration_test(args.verbose)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())