#!/usr/bin/env python3
"""
CI/CD Setup Validation Script

This script validates that the CI/CD pipeline is properly configured
and ready for production use.
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class CICDValidator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.successes = []
        
    def log_success(self, message: str):
        self.successes.append(f"✅ {message}")
        print(f"✅ {message}")
        
    def log_issue(self, message: str):
        self.issues.append(f"❌ {message}")
        print(f"❌ {message}")
        
    def log_warning(self, message: str):
        print(f"⚠️ {message}")

    def validate_workflow_files(self) -> bool:
        """Validate GitHub Actions workflow files exist and are valid."""
        print("\n🔍 Validating GitHub Actions workflows...")
        
        workflows_dir = self.project_root / ".github" / "workflows"
        if not workflows_dir.exists():
            self.log_issue("GitHub workflows directory missing")
            return False
            
        required_workflows = [
            "ci.yml",
            "daily-health-check.yml", 
            "dependency-update.yml",
            "release.yml",
            "dev.yml"
        ]
        
        all_valid = True
        for workflow in required_workflows:
            workflow_path = workflows_dir / workflow
            if not workflow_path.exists():
                self.log_issue(f"Missing workflow file: {workflow}")
                all_valid = False
                continue
                
            try:
                with open(workflow_path, 'r') as f:
                    yaml.safe_load(f)
                self.log_success(f"Valid workflow: {workflow}")
            except yaml.YAMLError as e:
                self.log_issue(f"Invalid YAML in {workflow}: {e}")
                all_valid = False
                
        return all_valid

    def validate_pytest_config(self) -> bool:
        """Validate pytest configuration for CI compatibility."""
        print("\n🔍 Validating pytest configuration...")
        
        pytest_ini = self.project_root / "pytest.ini"
        if not pytest_ini.exists():
            self.log_issue("pytest.ini file missing")
            return False
            
        with open(pytest_ini, 'r') as f:
            content = f.read()
            
        # Check for CI-friendly settings
        checks = [
            ("--cov-fail-under=20", "Coverage threshold set appropriately for CI"),
            ("--maxfail=3", "Maximum failures configured for CI"),
            ("--tb=short", "Traceback format optimized for CI"),
            ("ci:", "CI marker defined"),
            ("server_rust:", "Rust server marker defined"),
            ("server_python:", "Python server marker defined"),
            ("server_csharp:", "C# server marker defined"),
            ("server_go:", "Go server marker defined")
        ]
        
        all_valid = True
        for check, description in checks:
            if check in content:
                self.log_success(description)
            else:
                self.log_issue(f"Missing pytest config: {check}")
                all_valid = False
                
        return all_valid

    def validate_package_structure(self) -> bool:
        """Validate package structure for CI/CD compatibility."""
        print("\n🔍 Validating package structure...")
        
        required_files = [
            "pyproject.toml",
            "setup.py", 
            "requirements-dev.txt",
            "Dockerfile",
            "docker-compose.yml",
            ".gitignore"
        ]
        
        all_valid = True
        for file in required_files:
            file_path = self.project_root / file
            if file_path.exists():
                self.log_success(f"Required file present: {file}")
            else:
                self.log_issue(f"Missing required file: {file}")
                all_valid = False
                
        return all_valid

    def validate_documentation(self) -> bool:
        """Validate CI/CD documentation completeness."""
        print("\n🔍 Validating documentation...")
        
        docs_dir = self.project_root / "docs"
        required_docs = [
            "CI_CD_PIPELINE.md",
            "API_REFERENCE.md",
            "INSTALLATION.md",
            "TROUBLESHOOTING.md",
            "DOCKER_DEPLOYMENT.md"
        ]
        
        all_valid = True
        for doc in required_docs:
            doc_path = docs_dir / doc
            if doc_path.exists():
                self.log_success(f"Documentation present: {doc}")
            else:
                self.log_issue(f"Missing documentation: {doc}")
                all_valid = False
                
        return all_valid

    def validate_security_setup(self) -> bool:
        """Validate security configuration for CI/CD."""
        print("\n🔍 Validating security setup...")
        
        security_files = [
            "security_audit.py",
            "security_config.ini",
            ".secrets.baseline"
        ]
        
        all_valid = True
        for file in security_files:
            file_path = self.project_root / file
            if file_path.exists():
                self.log_success(f"Security file present: {file}")
            else:
                self.log_issue(f"Missing security file: {file}")
                all_valid = False
                
        return all_valid

    def validate_test_structure(self) -> bool:
        """Validate test structure for CI compatibility."""
        print("\n🔍 Validating test structure...")
        
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            self.log_issue("Tests directory missing")
            return False
            
        required_test_files = [
            "conftest.py",
            "test_core_modules.py",
            "test_performance.py",
            "test_security_validation.py"
        ]
        
        all_valid = True
        for test_file in required_test_files:
            test_path = tests_dir / test_file
            if test_path.exists():
                self.log_success(f"Test file present: {test_file}")
            else:
                self.log_issue(f"Missing test file: {test_file}")
                all_valid = False
                
        # Check integration tests
        integration_dir = tests_dir / "integration"
        if integration_dir.exists():
            self.log_success("Integration tests directory present")
        else:
            self.log_issue("Integration tests directory missing")
            all_valid = False
            
        return all_valid

    def validate_docker_setup(self) -> bool:
        """Validate Docker configuration for CI."""
        print("\n🔍 Validating Docker setup...")
        
        dockerfile = self.project_root / "Dockerfile"
        if not dockerfile.exists():
            self.log_issue("Dockerfile missing")
            return False
            
        with open(dockerfile, 'r') as f:
            content = f.read()
            
        # Check for multi-stage build
        if "FROM python:" in content and "as" in content.lower():
            self.log_success("Multi-stage Dockerfile detected")
        else:
            self.log_warning("Consider using multi-stage Dockerfile for optimization")
            
        # Check Docker Compose files
        compose_files = ["docker-compose.yml", "docker-compose.override.yml", "docker-compose.prod.yml"]
        for compose_file in compose_files:
            compose_path = self.project_root / compose_file
            if compose_path.exists():
                self.log_success(f"Docker Compose file present: {compose_file}")
            else:
                self.log_warning(f"Optional Docker Compose file missing: {compose_file}")
                
        return True

    def validate_performance_setup(self) -> bool:
        """Validate performance testing setup."""
        print("\n🔍 Validating performance testing setup...")
        
        perf_files = [
            "tests/test_performance.py",
            "tests/test_load_stress.py", 
            "tests/performance_runner.py",
            "run_load_tests.sh"
        ]
        
        all_valid = True
        for file in perf_files:
            file_path = self.project_root / file
            if file_path.exists():
                self.log_success(f"Performance file present: {file}")
            else:
                self.log_issue(f"Missing performance file: {file}")
                all_valid = False
                
        return all_valid

    def test_basic_functionality(self) -> bool:
        """Test basic package functionality."""
        print("\n🔍 Testing basic functionality...")
        
        try:
            # Test package import
            result = subprocess.run([
                sys.executable, "-c", 
                "import blackholio_client; print('Package imports successfully')"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.log_success("Package imports successfully")
            else:
                self.log_issue(f"Package import failed: {result.stderr}")
                return False
                
            # Test main API
            result = subprocess.run([
                sys.executable, "-c",
                "from blackholio_client import create_game_client; print('Main API available')"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.log_success("Main API available")
            else:
                self.log_issue(f"Main API test failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_issue(f"Functionality test error: {e}")
            return False
            
        return True

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        total_checks = len(self.successes) + len(self.issues)
        success_rate = len(self.successes) / total_checks * 100 if total_checks > 0 else 0
        
        report = {
            "timestamp": subprocess.check_output(["date"]).decode().strip(),
            "success_rate": round(success_rate, 1),
            "total_checks": total_checks,
            "successes": len(self.successes),
            "issues": len(self.issues),
            "successes_details": self.successes,
            "issues_details": self.issues,
            "deployment_ready": len(self.issues) == 0
        }
        
        return report

    def run_validation(self) -> bool:
        """Run complete CI/CD validation."""
        print("🚀 Starting CI/CD Pipeline Validation")
        print("=" * 50)
        
        validators = [
            self.validate_workflow_files,
            self.validate_pytest_config,
            self.validate_package_structure,
            self.validate_documentation,
            self.validate_security_setup,
            self.validate_test_structure,
            self.validate_docker_setup,
            self.validate_performance_setup,
            self.test_basic_functionality
        ]
        
        all_passed = True
        for validator in validators:
            try:
                passed = validator()
                if not passed:
                    all_passed = False
            except Exception as e:
                self.log_issue(f"Validation error in {validator.__name__}: {e}")
                all_passed = False
                
        # Generate and save report
        report = self.generate_report()
        
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Success Rate: {report['success_rate']}%")
        print(f"Total Checks: {report['total_checks']}")
        print(f"Successes: {report['successes']}")
        print(f"Issues: {report['issues']}")
        
        if report['deployment_ready']:
            print("\n🎉 CI/CD PIPELINE READY FOR DEPLOYMENT!")
        else:
            print(f"\n⚠️ CI/CD PIPELINE NEEDS ATTENTION ({report['issues']} issues)")
            
        # Save report
        report_path = self.project_root / "cicd-validation-report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        return all_passed

def main():
    """Main validation entry point."""
    project_root = os.getcwd()
    validator = CICDValidator(project_root)
    
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()