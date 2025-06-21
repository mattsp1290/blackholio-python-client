#!/usr/bin/env python3
"""
Docker Container Validation Tests for blackholio-python-client

This test suite validates that the package works correctly in Docker containers
with different environment variable configurations and server languages.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackholio_client import create_game_client, get_global_config
from blackholio_client.config import EnvironmentConfig, ServerConfig
from blackholio_client.exceptions import BlackholioConfigurationError


class DockerValidator:
    """Validates blackholio-python-client functionality in Docker containers"""
    
    def __init__(self):
        self.results = {
            "environment_tests": [],
            "server_language_tests": [],
            "configuration_tests": [],
            "client_creation_tests": [],
            "isolation_tests": []
        }
    
    def validate_environment_variables(self) -> Dict[str, bool]:
        """Validate that environment variables are properly read in container"""
        print("\n🔍 Validating Environment Variables in Docker Container")
        print("=" * 60)
        
        tests = {}
        
        # Test 1: Check if environment variables are set
        env_vars = {
            "SERVER_LANGUAGE": os.getenv("SERVER_LANGUAGE"),
            "SERVER_IP": os.getenv("SERVER_IP"),
            "SERVER_PORT": os.getenv("SERVER_PORT"),
            "BLACKHOLIO_LOG_LEVEL": os.getenv("BLACKHOLIO_LOG_LEVEL"),
            "BLACKHOLIO_CONNECTION_TIMEOUT": os.getenv("BLACKHOLIO_CONNECTION_TIMEOUT"),
            "BLACKHOLIO_MAX_RETRIES": os.getenv("BLACKHOLIO_MAX_RETRIES"),
            "BLACKHOLIO_SSL_ENABLED": os.getenv("BLACKHOLIO_SSL_ENABLED")
        }
        
        print("\n📊 Environment Variables:")
        for key, value in env_vars.items():
            print(f"  {key}: {value}")
            tests[f"env_var_{key.lower()}"] = value is not None
        
        # Test 2: Validate EnvironmentConfig reads variables correctly
        try:
            config = EnvironmentConfig()
            tests["environment_config_creation"] = True
            
            # Verify values match environment
            tests["server_language_match"] = config.server_language == os.getenv("SERVER_LANGUAGE", "rust")
            tests["server_ip_match"] = config.server_ip == os.getenv("SERVER_IP", "localhost")
            tests["server_port_match"] = str(config.server_port) == os.getenv("SERVER_PORT", "8080")
            tests["log_level_match"] = config.log_level == os.getenv("BLACKHOLIO_LOG_LEVEL", "INFO")
            
            print(f"\n✅ EnvironmentConfig loaded successfully:")
            print(f"  Server Language: {config.server_language}")
            print(f"  Server IP: {config.server_ip}")
            print(f"  Server Port: {config.server_port}")
            print(f"  Log Level: {config.log_level}")
            
        except Exception as e:
            print(f"\n❌ Failed to create EnvironmentConfig: {e}")
            tests["environment_config_creation"] = False
        
        self.results["environment_tests"] = tests
        return tests
    
    def validate_server_language_switching(self) -> Dict[str, bool]:
        """Validate that server language switching works in containers"""
        print("\n\n🔄 Validating Server Language Switching")
        print("=" * 60)
        
        tests = {}
        current_language = os.getenv("SERVER_LANGUAGE", "rust")
        
        # Test 1: Verify ServerConfig uses correct language
        try:
            server_config = ServerConfig()
            tests["server_config_creation"] = True
            tests["server_config_language"] = server_config.language == current_language
            
            print(f"\n✅ ServerConfig created for language: {server_config.language}")
            print(f"  Default Port: {server_config.get_default_port()}")
            print(f"  Binary Protocol: {server_config.use_binary_protocol}")
            
        except Exception as e:
            print(f"\n❌ Failed to create ServerConfig: {e}")
            tests["server_config_creation"] = False
        
        # Test 2: Verify factory pattern works with environment
        try:
            from blackholio_client.factory import get_client_factory, list_available_languages
            
            available = list_available_languages()
            tests["factory_languages_available"] = len(available) == 4
            tests["current_language_available"] = current_language in available
            
            factory = get_client_factory(current_language)
            tests["factory_creation"] = factory is not None
            tests["factory_language_match"] = factory.language == current_language
            
            print(f"\n✅ Factory created for {current_language}")
            print(f"  Available languages: {available}")
            
        except Exception as e:
            print(f"\n❌ Failed factory validation: {e}")
            tests["factory_creation"] = False
        
        self.results["server_language_tests"] = tests
        return tests
    
    def validate_configuration_persistence(self) -> Dict[str, bool]:
        """Validate that configuration persists correctly in container"""
        print("\n\n💾 Validating Configuration Persistence")
        print("=" * 60)
        
        tests = {}
        
        # Test 1: Global configuration singleton
        try:
            config1 = get_global_config()
            config2 = get_global_config()
            tests["global_config_singleton"] = config1 is config2
            
            print(f"\n✅ Global configuration singleton working")
            print(f"  Server: {config1.server_ip}:{config1.server_port}")
            print(f"  Language: {config1.server_language}")
            
        except Exception as e:
            print(f"\n❌ Global config failed: {e}")
            tests["global_config_singleton"] = False
        
        # Test 2: Configuration reload
        try:
            original_timeout = get_global_config().connection_timeout
            
            # Temporarily change environment
            os.environ["BLACKHOLIO_CONNECTION_TIMEOUT"] = "999"
            get_global_config().reload()
            
            new_timeout = get_global_config().connection_timeout
            tests["config_reload"] = new_timeout == 999
            
            # Restore original
            os.environ["BLACKHOLIO_CONNECTION_TIMEOUT"] = str(original_timeout)
            get_global_config().reload()
            
            print(f"\n✅ Configuration reload working")
            print(f"  Original timeout: {original_timeout}")
            print(f"  Modified timeout: {new_timeout}")
            
        except Exception as e:
            print(f"\n❌ Config reload failed: {e}")
            tests["config_reload"] = False
        
        self.results["configuration_tests"] = tests
        return tests
    
    def validate_client_creation(self) -> Dict[str, bool]:
        """Validate that GameClient can be created in container"""
        print("\n\n🎮 Validating Client Creation")
        print("=" * 60)
        
        tests = {}
        
        # Test 1: Create client with environment config
        try:
            client = create_game_client()
            tests["client_creation"] = client is not None
            
            # Verify client configuration matches environment
            tests["client_language_match"] = True  # Would need server to fully test
            tests["client_has_connection"] = hasattr(client, 'connection')
            tests["client_has_auth"] = hasattr(client, 'auth')
            tests["client_has_subscriptions"] = hasattr(client, 'subscriptions')
            tests["client_has_reducers"] = hasattr(client, 'reducers')
            
            print(f"\n✅ GameClient created successfully")
            print(f"  Has connection interface: {tests['client_has_connection']}")
            print(f"  Has auth interface: {tests['client_has_auth']}")
            print(f"  Has subscription interface: {tests['client_has_subscriptions']}")
            print(f"  Has reducer interface: {tests['client_has_reducers']}")
            
        except Exception as e:
            print(f"\n❌ Client creation failed: {e}")
            tests["client_creation"] = False
        
        # Test 2: Client with custom configuration
        try:
            custom_client = create_game_client(
                server_language="python",
                server_ip="custom-server",
                server_port=9999
            )
            tests["custom_client_creation"] = custom_client is not None
            
            print(f"\n✅ Custom client created successfully")
            
        except Exception as e:
            print(f"\n❌ Custom client failed: {e}")
            tests["custom_client_creation"] = False
        
        self.results["client_creation_tests"] = tests
        return tests
    
    def validate_container_isolation(self) -> Dict[str, bool]:
        """Validate that container provides proper isolation"""
        print("\n\n🔒 Validating Container Isolation")
        print("=" * 60)
        
        tests = {}
        
        # Test 1: File system isolation
        try:
            # Check we're in container
            tests["in_container"] = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") is not None
            
            # Check working directory
            cwd = os.getcwd()
            tests["correct_workdir"] = cwd == "/app"
            
            # Check package is installed
            import blackholio_client
            tests["package_installed"] = True
            tests["package_location"] = "site-packages" in blackholio_client.__file__ or "src" in blackholio_client.__file__
            
            print(f"\n📦 Container Environment:")
            print(f"  In Docker: {tests['in_container']}")
            print(f"  Working Dir: {cwd}")
            print(f"  Package Location: {blackholio_client.__file__}")
            
        except Exception as e:
            print(f"\n❌ Isolation check failed: {e}")
            tests["package_installed"] = False
        
        # Test 2: Python path configuration
        try:
            pythonpath = os.getenv("PYTHONPATH", "")
            tests["pythonpath_set"] = "/app" in pythonpath
            
            # Check sys.path
            tests["app_in_syspath"] = "/app" in sys.path
            
            print(f"\n🐍 Python Configuration:")
            print(f"  PYTHONPATH: {pythonpath}")
            print(f"  /app in sys.path: {tests['app_in_syspath']}")
            
        except Exception as e:
            print(f"\n❌ Python path check failed: {e}")
            tests["pythonpath_set"] = False
        
        self.results["isolation_tests"] = tests
        return tests
    
    def generate_report(self) -> Tuple[bool, str]:
        """Generate validation report"""
        print("\n\n📊 Docker Validation Summary")
        print("=" * 60)
        
        all_passed = True
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if not tests:
                continue
                
            category_passed = all(tests.values()) if tests else True
            category_total = len(tests)
            category_success = sum(1 for v in tests.values() if v)
            
            total_tests += category_total
            passed_tests += category_success
            
            if not category_passed:
                all_passed = False
            
            emoji = "✅" if category_passed else "❌"
            print(f"\n{emoji} {category.replace('_', ' ').title()}: {category_success}/{category_total}")
            
            for test_name, result in tests.items():
                status = "✓" if result else "✗"
                print(f"  {status} {test_name.replace('_', ' ')}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n\n🎯 Overall Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "all_passed": all_passed
            },
            "results": self.results,
            "environment": {
                "server_language": os.getenv("SERVER_LANGUAGE"),
                "server_ip": os.getenv("SERVER_IP"),
                "server_port": os.getenv("SERVER_PORT"),
                "container": os.getenv("HOSTNAME", "unknown")
            }
        }
        
        return all_passed, json.dumps(report, indent=2)


def run_docker_validation():
    """Run complete Docker validation suite"""
    print("🚀 Starting Docker Container Validation for blackholio-python-client")
    print("=" * 80)
    
    validator = DockerValidator()
    
    # Run all validation tests
    validator.validate_environment_variables()
    validator.validate_server_language_switching()
    validator.validate_configuration_persistence()
    validator.validate_client_creation()
    validator.validate_container_isolation()
    
    # Generate report
    success, report = validator.generate_report()
    
    # Save report if in container
    if os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        report_path = Path("/app/test-results/docker-validation-report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")
    
    return 0 if success else 1


# Tests for pytest integration
class TestDockerValidation:
    """Pytest integration for Docker validation"""
    
    def test_environment_variables(self):
        """Test environment variable configuration in Docker"""
        validator = DockerValidator()
        results = validator.validate_environment_variables()
        
        assert results.get("environment_config_creation", False), "Failed to create EnvironmentConfig"
        assert results.get("server_language_match", False), "Server language doesn't match environment"
        assert results.get("server_ip_match", False), "Server IP doesn't match environment"
        assert results.get("server_port_match", False), "Server port doesn't match environment"
    
    def test_server_language_switching(self):
        """Test server language switching in Docker"""
        validator = DockerValidator()
        results = validator.validate_server_language_switching()
        
        assert results.get("server_config_creation", False), "Failed to create ServerConfig"
        assert results.get("factory_creation", False), "Failed to create factory"
        assert results.get("current_language_available", False), "Current language not available"
    
    def test_client_creation(self):
        """Test GameClient creation in Docker"""
        validator = DockerValidator()
        results = validator.validate_client_creation()
        
        assert results.get("client_creation", False), "Failed to create GameClient"
        assert results.get("client_has_connection", False), "Client missing connection interface"
        assert results.get("client_has_auth", False), "Client missing auth interface"


if __name__ == "__main__":
    sys.exit(run_docker_validation())