#!/usr/bin/env python3
"""
Security Audit Tool for blackholio-python-client
Comprehensive security analysis and vulnerability assessment
"""

import ast
import os
import re
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class SecurityFinding:
    """Security finding/vulnerability"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # Input validation, Authentication, etc.
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    recommendation: str
    cwe_id: str = None  # Common Weakness Enumeration ID

class SecurityAuditor:
    """Comprehensive security auditor for Python code"""
    
    def __init__(self, src_dir: str):
        self.src_dir = Path(src_dir)
        self.findings: List[SecurityFinding] = []
        self.patterns = self._init_security_patterns()
        
    def _init_security_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize security vulnerability patterns"""
        return {
            "injection": [
                {
                    "pattern": r"exec\s*\(",
                    "severity": "CRITICAL",
                    "description": "Use of exec() can lead to code injection",
                    "cwe": "CWE-94"
                },
                {
                    "pattern": r"eval\s*\(",
                    "severity": "CRITICAL", 
                    "description": "Use of eval() can lead to code injection",
                    "cwe": "CWE-94"
                },
                {
                    "pattern": r"subprocess\.call.*shell=True",
                    "severity": "HIGH",
                    "description": "shell=True in subprocess calls can lead to command injection",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r"os\.system\s*\(",
                    "severity": "HIGH",
                    "description": "os.system() can lead to command injection",
                    "cwe": "CWE-78"
                }
            ],
            "crypto": [
                {
                    "pattern": r"md5\s*\(",
                    "severity": "MEDIUM",
                    "description": "MD5 is cryptographically weak",
                    "cwe": "CWE-327"
                },
                {
                    "pattern": r"sha1\s*\(",
                    "severity": "MEDIUM", 
                    "description": "SHA1 is cryptographically weak",
                    "cwe": "CWE-327"
                },
                {
                    "pattern": r"random\.random\s*\(",
                    "severity": "LOW",
                    "description": "random.random() is not cryptographically secure",
                    "cwe": "CWE-338"
                }
            ],
            "secrets": [
                {
                    "pattern": r"['\"]([A-Za-z0-9+/]{40,})['\"]",
                    "severity": "HIGH",
                    "description": "Potential hardcoded secret or API key",
                    "cwe": "CWE-798"
                },
                {
                    "pattern": r"password\s*=\s*['\"][\w]+['\"]",
                    "severity": "HIGH",
                    "description": "Hardcoded password detected",
                    "cwe": "CWE-798"
                },
                {
                    "pattern": r"api_key\s*=\s*['\"][\w]+['\"]",
                    "severity": "HIGH",
                    "description": "Hardcoded API key detected",
                    "cwe": "CWE-798"
                }
            ],
            "input_validation": [
                {
                    "pattern": r"open\s*\([^)]*\)",
                    "severity": "MEDIUM",
                    "description": "File operations should validate paths",
                    "cwe": "CWE-22"
                },
                {
                    "pattern": r"pickle\.load",
                    "severity": "HIGH",
                    "description": "pickle.load() can execute arbitrary code",
                    "cwe": "CWE-502"
                }
            ],
            "logging": [
                {
                    "pattern": r"print\s*\([^)]*password[^)]*\)",
                    "severity": "MEDIUM",
                    "description": "Potential password logging",
                    "cwe": "CWE-532"
                },
                {
                    "pattern": r"log.*\.info\([^)]*password[^)]*\)",
                    "severity": "MEDIUM",
                    "description": "Potential password logging",
                    "cwe": "CWE-532"
                }
            ]
        }
    
    def audit_file(self, file_path: Path) -> None:
        """Audit a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Pattern-based analysis
            self._analyze_patterns(file_path, content, lines)
            
            # AST-based analysis
            try:
                tree = ast.parse(content)
                self._analyze_ast(file_path, tree, lines)
            except SyntaxError:
                self.findings.append(SecurityFinding(
                    severity="LOW",
                    category="Syntax",
                    file_path=str(file_path),
                    line_number=0,
                    description="File has syntax errors",
                    code_snippet="",
                    recommendation="Fix syntax errors"
                ))
                
        except Exception as e:
            print(f"Error auditing {file_path}: {e}")
    
    def _analyze_patterns(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Analyze file content using regex patterns"""
        for category, patterns in self.patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    line_number = content[:match.start()].count('\n') + 1
                    line_content = lines[line_number - 1] if line_number <= len(lines) else ""
                    
                    # Skip false positives in comments
                    if line_content.strip().startswith('#'):
                        continue
                    
                    self.findings.append(SecurityFinding(
                        severity=pattern_info["severity"],
                        category=category.title(),
                        file_path=str(file_path),
                        line_number=line_number,
                        description=pattern_info["description"],
                        code_snippet=line_content.strip(),
                        recommendation=self._get_recommendation(pattern_info),
                        cwe_id=pattern_info.get("cwe", "")
                    ))
    
    def _analyze_ast(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Analyze file using AST for more sophisticated checks"""
        for node in ast.walk(tree):
            # Check for dangerous functions
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ['exec', 'eval', 'compile']:
                        line = getattr(node, 'lineno', 0)
                        line_content = lines[line - 1] if line <= len(lines) else ""
                        
                        self.findings.append(SecurityFinding(
                            severity="CRITICAL",
                            category="Code Injection",
                            file_path=str(file_path),
                            line_number=line,
                            description=f"Dangerous function '{func_name}' usage",
                            code_snippet=line_content.strip(),
                            recommendation=f"Avoid using {func_name}() or validate inputs thoroughly",
                            cwe_id="CWE-94"
                        ))
            
            # Check for SQL-like patterns
            if isinstance(node, ast.Str):
                if any(keyword in node.s.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                    line = getattr(node, 'lineno', 0)
                    line_content = lines[line - 1] if line <= len(lines) else ""
                    
                    # Check if it looks like string formatting
                    if '%' in node.s or '{' in node.s:
                        self.findings.append(SecurityFinding(
                            severity="MEDIUM",
                            category="SQL Injection",
                            file_path=str(file_path),
                            line_number=line,
                            description="Potential SQL injection via string formatting",
                            code_snippet=line_content.strip(),
                            recommendation="Use parameterized queries",
                            cwe_id="CWE-89"
                        ))
    
    def _get_recommendation(self, pattern_info: Dict) -> str:
        """Get security recommendation based on pattern"""
        recommendations = {
            "exec": "Use safer alternatives like importlib or avoid dynamic execution",
            "eval": "Use ast.literal_eval() for safe evaluation or avoid eval()",
            "shell=True": "Use shell=False and pass arguments as list",
            "os.system": "Use subprocess.run() with proper argument handling",
            "md5": "Use SHA-256 or higher for cryptographic purposes",
            "sha1": "Use SHA-256 or higher for cryptographic purposes",
            "random.random": "Use secrets module for cryptographically secure randomness",
            "password": "Store passwords securely using environment variables or secrets management",
            "api_key": "Store API keys in environment variables or secure key management",
            "open": "Validate file paths and use Path.resolve() to prevent directory traversal",
            "pickle.load": "Use safer serialization formats like JSON"
        }
        
        for key, rec in recommendations.items():
            if key in pattern_info["pattern"]:
                return rec
        
        return "Review this code for security implications"
    
    def check_dependencies(self) -> None:
        """Check for vulnerable dependencies"""
        try:
            # Check requirements files
            req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
            for req_file in req_files:
                req_path = self.src_dir.parent / req_file
                if req_path.exists():
                    self._audit_requirements(req_path)
        except Exception as e:
            print(f"Error checking dependencies: {e}")
    
    def _audit_requirements(self, req_file: Path) -> None:
        """Audit requirements file for known vulnerabilities"""
        # Known vulnerable packages (simplified example)
        vulnerable_packages = {
            "django": {"<3.2.13": "CVE-2022-28346"},
            "flask": {"<2.0.3": "CVE-2021-23385"},
            "requests": {"<2.25.1": "CVE-2020-26137"},
            "pyyaml": {"<5.4": "CVE-2020-14343"},
            "pillow": {"<8.3.2": "CVE-2021-34552"}
        }
        
        try:
            with open(req_file, 'r') as f:
                content = f.read()
            
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Simple package parsing
                    package_match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if package_match:
                        package = package_match.group(1).lower()
                        if package in vulnerable_packages:
                            self.findings.append(SecurityFinding(
                                severity="MEDIUM",
                                category="Dependency",
                                file_path=str(req_file),
                                line_number=0,
                                description=f"Potentially vulnerable dependency: {package}",
                                code_snippet=line,
                                recommendation="Update to latest secure version"
                            ))
        except Exception as e:
            print(f"Error reading {req_file}: {e}")
    
    def check_environment_variables(self) -> None:
        """Check for insecure environment variable handling"""
        env_files = list(self.src_dir.rglob("*.py"))
        
        for file_path in env_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for os.environ usage without defaults
                env_pattern = r'os\.environ\[[\'"](.*?)[\'"]\]'
                matches = re.finditer(env_pattern, content)
                
                for match in matches:
                    line_number = content[:match.start()].count('\n') + 1
                    line_content = lines[line_number - 1] if line_number <= len(lines) else ""
                    env_var = match.group(1)
                    
                    # Check if it's a sensitive variable
                    if any(keyword in env_var.lower() for keyword in ['password', 'secret', 'key', 'token']):
                        self.findings.append(SecurityFinding(
                            severity="MEDIUM",
                            category="Environment Variables",
                            file_path=str(file_path),
                            line_number=line_number,
                            description=f"Direct access to sensitive environment variable: {env_var}",
                            code_snippet=line_content.strip(),
                            recommendation="Use os.environ.get() with secure defaults or validation",
                            cwe_id="CWE-209"
                        ))
                        
            except Exception as e:
                print(f"Error checking environment variables in {file_path}: {e}")
    
    def run_security_tools(self) -> None:
        """Run external security tools if available"""
        tools = [
            {
                "name": "bandit",
                "command": ["bandit", "-r", str(self.src_dir), "-f", "json"],
                "parse": self._parse_bandit_output
            },
            {
                "name": "safety",
                "command": ["safety", "check", "--json"],
                "parse": self._parse_safety_output
            }
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(
                    tool["command"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 or result.stdout:
                    tool["parse"](result.stdout)
                    
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                # Tool not available or failed
                self.findings.append(SecurityFinding(
                    severity="INFO",
                    category="Tools",
                    file_path="",
                    line_number=0,
                    description=f"Security tool '{tool['name']}' not available or failed",
                    code_snippet="",
                    recommendation=f"Install {tool['name']} for additional security analysis"
                ))
    
    def _parse_bandit_output(self, output: str) -> None:
        """Parse bandit JSON output"""
        try:
            data = json.loads(output)
            for result in data.get("results", []):
                self.findings.append(SecurityFinding(
                    severity=result.get("issue_severity", "MEDIUM").upper(),
                    category="Bandit",
                    file_path=result.get("filename", ""),
                    line_number=result.get("line_number", 0),
                    description=result.get("issue_text", ""),
                    code_snippet=result.get("code", ""),
                    recommendation="Review bandit findings",
                    cwe_id=result.get("issue_cwe", {}).get("id", "")
                ))
        except json.JSONDecodeError:
            pass
    
    def _parse_safety_output(self, output: str) -> None:
        """Parse safety JSON output"""
        try:
            data = json.loads(output)
            for vuln in data:
                self.findings.append(SecurityFinding(
                    severity="HIGH",
                    category="Dependency Vulnerability",
                    file_path="requirements",
                    line_number=0,
                    description=f"Vulnerable dependency: {vuln.get('package')} {vuln.get('installed_version')}",
                    code_snippet="",
                    recommendation=f"Update to version {vuln.get('vulnerable_spec', 'latest')}"
                ))
        except (json.JSONDecodeError, TypeError):
            pass
    
    def audit_all(self) -> None:
        """Run complete security audit"""
        print("🔍 Starting comprehensive security audit...")
        
        # Find all Python files
        python_files = list(self.src_dir.rglob("*.py"))
        print(f"📁 Found {len(python_files)} Python files to audit")
        
        # Audit each file
        for file_path in python_files:
            self.audit_file(file_path)
        
        # Check dependencies
        print("🔗 Checking dependencies...")
        self.check_dependencies()
        
        # Check environment variables
        print("🌍 Checking environment variable handling...")
        self.check_environment_variables()
        
        # Run external security tools
        print("🛠️  Running external security tools...")
        self.run_security_tools()
        
        print(f"✅ Security audit complete. Found {len(self.findings)} findings.")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        # Group findings by severity
        by_severity = defaultdict(list)
        by_category = defaultdict(list)
        
        for finding in self.findings:
            by_severity[finding.severity].append(finding)
            by_category[finding.category].append(finding)
        
        # Calculate security score
        scores = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 2, "INFO": 1}
        total_score = sum(scores.get(f.severity, 1) for f in self.findings)
        max_possible = len(self.findings) * 10
        security_score = max(0, 100 - (total_score / max(max_possible, 1) * 100)) if self.findings else 100
        
        return {
            "summary": {
                "total_findings": len(self.findings),
                "critical": len(by_severity["CRITICAL"]),
                "high": len(by_severity["HIGH"]),
                "medium": len(by_severity["MEDIUM"]),
                "low": len(by_severity["LOW"]),
                "info": len(by_severity["INFO"]),
                "security_score": round(security_score, 2)
            },
            "findings_by_severity": {k: [asdict(f) for f in v] for k, v in by_severity.items()},
            "findings_by_category": {k: len(v) for k, v in by_category.items()},
            "all_findings": [asdict(f) for f in self.findings]
        }
    
    def print_report(self) -> None:
        """Print human-readable security report"""
        report = self.generate_report()
        summary = report["summary"]
        
        print("\n" + "="*80)
        print("🛡️  SECURITY AUDIT REPORT - BLACKHOLIO PYTHON CLIENT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Findings: {summary['total_findings']}")
        print(f"   Security Score: {summary['security_score']}/100")
        print(f"   🔴 Critical: {summary['critical']}")
        print(f"   🟠 High:     {summary['high']}")
        print(f"   🟡 Medium:   {summary['medium']}")
        print(f"   🔵 Low:      {summary['low']}")
        print(f"   ℹ️  Info:     {summary['info']}")
        
        print(f"\n📋 FINDINGS BY CATEGORY:")
        for category, count in report["findings_by_category"].items():
            print(f"   {category}: {count}")
        
        # Show detailed findings
        if self.findings:
            print(f"\n🔍 DETAILED FINDINGS:")
            for i, finding in enumerate(self.findings[:20], 1):  # Show first 20
                severity_emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠", 
                    "MEDIUM": "🟡",
                    "LOW": "🔵",
                    "INFO": "ℹ️"
                }.get(finding.severity, "❓")
                
                print(f"\n{i}. {severity_emoji} {finding.severity} - {finding.category}")
                print(f"   File: {finding.file_path}:{finding.line_number}")
                print(f"   Issue: {finding.description}")
                if finding.code_snippet:
                    print(f"   Code: {finding.code_snippet}")
                print(f"   Fix: {finding.recommendation}")
                if finding.cwe_id:
                    print(f"   CWE: {finding.cwe_id}")
            
            if len(self.findings) > 20:
                print(f"\n... and {len(self.findings) - 20} more findings")
        
        # Security assessment
        print(f"\n🎯 SECURITY ASSESSMENT:")
        if summary["security_score"] >= 95:
            print("   ✅ EXCELLENT - Very strong security posture")
        elif summary["security_score"] >= 85:
            print("   ✅ GOOD - Strong security with minor issues")
        elif summary["security_score"] >= 70:
            print("   ⚠️  FAIR - Some security concerns need attention")
        elif summary["security_score"] >= 50:
            print("   ⚠️  POOR - Significant security issues found")
        else:
            print("   ❌ CRITICAL - Major security vulnerabilities present")
        
        print("\n" + "="*80)

def main():
    """Main security audit execution"""
    if len(sys.argv) > 1:
        src_dir = sys.argv[1]
    else:
        src_dir = "src"
    
    if not os.path.exists(src_dir):
        print(f"❌ Source directory '{src_dir}' not found!")
        sys.exit(1)
    
    auditor = SecurityAuditor(src_dir)
    auditor.audit_all()
    auditor.print_report()
    
    # Save detailed report
    report = auditor.generate_report()
    with open("security_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Detailed report saved to: security_audit_report.json")

if __name__ == "__main__":
    main()