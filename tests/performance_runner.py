#!/usr/bin/env python3
"""
Performance Test Runner - Automated Performance Testing and Benchmarking

Provides automated execution of performance tests with result collection,
analysis, and reporting for the blackholio-python-client package.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tests.benchmarks import AdvancedBenchmark
from blackholio_client.utils.debugging import get_diagnostic_collector


class PerformanceTestRunner:
    """
    Comprehensive performance test runner.
    
    Manages execution of performance tests, collection of results,
    and generation of performance reports.
    """
    
    def __init__(self, 
                 output_dir: str = "performance_results",
                 baseline_file: Optional[str] = None):
        """
        Initialize performance test runner.
        
        Args:
            output_dir: Directory for output files
            baseline_file: Optional baseline file for comparison
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_file = Path(baseline_file) if baseline_file else None
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Results storage
        self.test_results: List[Dict[str, Any]] = []
        self.benchmark_results: List[Dict[str, Any]] = []
        self.system_info: Dict[str, Any] = {}
        
    def collect_system_info(self):
        """Collect system information for context."""
        print("Collecting system information...")
        
        collector = get_diagnostic_collector()
        diagnostics = collector.generate_diagnostic_report()
        
        self.system_info = {
            'timestamp': self.timestamp,
            'system_info': diagnostics.get('system_info', {}),
            'environment_info': diagnostics.get('environment_info', {}),
            'performance_metrics': diagnostics.get('performance_metrics', {}),
            'package_info': diagnostics.get('package_info', {}),
            'dependency_info': diagnostics.get('dependency_info', {})
        }
        
        # Save system info
        system_info_file = self.output_dir / f"system_info_{self.timestamp}.json"
        with open(system_info_file, 'w') as f:
            json.dump(self.system_info, f, indent=2, default=str)
        
        print(f"System info saved to: {system_info_file}")
    
    def run_performance_tests(self, 
                            test_pattern: str = "test_performance.py",
                            pytest_args: Optional[List[str]] = None) -> bool:
        """
        Run performance tests using pytest.
        
        Args:
            test_pattern: Test file pattern
            pytest_args: Additional pytest arguments
            
        Returns:
            True if tests passed, False otherwise
        """
        print(f"Running performance tests: {test_pattern}")
        
        # Prepare pytest arguments
        args = [
            str(Path(__file__).parent / test_pattern),
            "-v",
            "--tb=short",
            "--capture=no",  # Show print statements
            f"--junitxml={self.output_dir}/performance_junit_{self.timestamp}.xml"
        ]
        
        if pytest_args:
            args.extend(pytest_args)
        
        # Run tests
        exit_code = pytest.main(args)
        
        print(f"Performance tests completed with exit code: {exit_code}")
        return exit_code == 0
    
    def run_memory_profiling(self):
        """Run memory profiling tests."""
        print("Running memory profiling...")
        
        try:
            from memory_profiler import profile
            import subprocess
            
            # Run memory profiling on specific test
            profile_script = Path(__file__).parent / "test_performance.py"
            profile_output = self.output_dir / f"memory_profile_{self.timestamp}.txt"
            
            cmd = [
                sys.executable, "-m", "memory_profiler",
                str(profile_script)
            ]
            
            with open(profile_output, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=Path(__file__).parent)
            
            if result.returncode == 0:
                print(f"Memory profile saved to: {profile_output}")
            else:
                print("Memory profiling failed")
                
        except ImportError:
            print("memory_profiler not available, skipping memory profiling")
        except Exception as e:
            print(f"Memory profiling error: {e}")
    
    def run_cpu_profiling(self):
        """Run CPU profiling tests."""
        print("Running CPU profiling...")
        
        try:
            import subprocess
            
            # Use py-spy for CPU profiling
            profile_output = self.output_dir / f"cpu_profile_{self.timestamp}.svg"
            
            # Run a simple performance test under py-spy
            test_script = f"""
import sys
sys.path.insert(0, "{Path(__file__).parent.parent / 'src'}")
from tests.test_performance import TestDataModelPerformance
test = TestDataModelPerformance()
for _ in range(10):
    test.test_vector2_operations_performance()
    test.test_game_entity_creation_performance()
"""
            
            # Write temporary test script
            temp_script = self.output_dir / f"temp_profile_test_{self.timestamp}.py"
            with open(temp_script, 'w') as f:
                f.write(test_script)
            
            cmd = [
                "py-spy", "record", 
                "-o", str(profile_output),
                "-d", "30",  # 30 second duration
                "--", sys.executable, str(temp_script)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"CPU profile saved to: {profile_output}")
            else:
                print(f"CPU profiling failed: {result.stderr}")
            
            # Clean up temp script
            temp_script.unlink(missing_ok=True)
                
        except FileNotFoundError:
            print("py-spy not available, skipping CPU profiling")
        except Exception as e:
            print(f"CPU profiling error: {e}")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        print("Generating performance report...")
        
        # Load benchmark results
        benchmark_files = list(self.output_dir.glob("performance_benchmarks_*.json"))
        
        for file_path in benchmark_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.benchmark_results.extend(data)
            except Exception as e:
                print(f"Error loading benchmark file {file_path}: {e}")
        
        # Generate report
        report = {
            'metadata': {
                'timestamp': self.timestamp,
                'total_benchmarks': len(self.benchmark_results),
                'report_version': '1.0'
            },
            'system_info': self.system_info,
            'benchmark_results': self.benchmark_results,
            'summary': self._generate_summary(),
            'recommendations': self._generate_recommendations()
        }
        
        # Save main report
        report_file = self.output_dir / f"performance_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate HTML report
        html_report_file = self.output_dir / f"performance_report_{self.timestamp}.html"
        self._generate_html_report(report, html_report_file)
        
        print(f"Performance report saved to: {report_file}")
        print(f"HTML report saved to: {html_report_file}")
        
        return report
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary."""
        if not self.benchmark_results:
            return {'error': 'No benchmark results available'}
        
        # Calculate summary statistics
        total_tests = len(self.benchmark_results)
        successful_tests = sum(1 for r in self.benchmark_results if r.get('success_rate', 0) > 0.95)
        
        avg_ops_per_sec = sum(r.get('operations_per_second', 0) for r in self.benchmark_results) / total_tests
        avg_memory_usage = sum(r.get('memory_usage_mb', 0) for r in self.benchmark_results) / total_tests
        
        # Find fastest and slowest tests
        fastest_test = max(self.benchmark_results, key=lambda r: r.get('operations_per_second', 0))
        slowest_test = min(self.benchmark_results, key=lambda r: r.get('operations_per_second', 0))
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
            'average_operations_per_second': avg_ops_per_sec,
            'average_memory_usage_mb': avg_memory_usage,
            'fastest_test': {
                'name': fastest_test.get('test_name', 'unknown'),
                'ops_per_second': fastest_test.get('operations_per_second', 0)
            },
            'slowest_test': {
                'name': slowest_test.get('test_name', 'unknown'),
                'ops_per_second': slowest_test.get('operations_per_second', 0)
            }
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        if not self.benchmark_results:
            return ["No benchmark data available for recommendations"]
        
        # Check for slow operations
        slow_tests = [r for r in self.benchmark_results if r.get('operations_per_second', 0) < 1000]
        if slow_tests:
            recommendations.append(
                f"Consider optimizing {len(slow_tests)} tests with < 1000 ops/sec performance"
            )
        
        # Check for high memory usage
        high_memory_tests = [r for r in self.benchmark_results if r.get('memory_usage_mb', 0) > 10]
        if high_memory_tests:
            recommendations.append(
                f"Review memory usage in {len(high_memory_tests)} tests using > 10MB"
            )
        
        # Check for low success rates
        failing_tests = [r for r in self.benchmark_results if r.get('success_rate', 1) < 0.95]
        if failing_tests:
            recommendations.append(
                f"Investigate {len(failing_tests)} tests with < 95% success rate"
            )
        
        # Performance targets
        vector_tests = [r for r in self.benchmark_results if 'vector' in r.get('test_name', '').lower()]
        if vector_tests and any(r.get('operations_per_second', 0) < 10000 for r in vector_tests):
            recommendations.append("Vector operations should achieve > 10,000 ops/sec")
        
        entity_tests = [r for r in self.benchmark_results if 'entity' in r.get('test_name', '').lower()]
        if entity_tests and any(r.get('operations_per_second', 0) < 5000 for r in entity_tests):
            recommendations.append("Entity operations should achieve > 5,000 ops/sec")
        
        if not recommendations:
            recommendations.append("All performance metrics are within acceptable ranges")
        
        return recommendations
    
    def _generate_html_report(self, report: Dict[str, Any], output_file: Path):
        """Generate HTML performance report."""
        summary = report.get('summary', {})
        benchmarks = report.get('benchmark_results', [])
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Blackholio Python Client - Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .good {{ color: #27ae60; font-weight: bold; }}
        .warning {{ color: #f39c12; font-weight: bold; }}
        .bad {{ color: #e74c3c; font-weight: bold; }}
        .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }}
        .recommendations ul {{ margin: 10px 0; }}
        .recommendations li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Blackholio Python Client - Performance Report</h1>
        <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h2>📊 Performance Summary</h2>
            <div class="metric">
                <div class="metric-value">{summary.get('total_tests', 0)}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('success_rate', 0)*100:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('average_operations_per_second', 0):.0f}</div>
                <div class="metric-label">Avg Ops/Sec</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get('average_memory_usage_mb', 0):.1f}MB</div>
                <div class="metric-label">Avg Memory</div>
            </div>
        </div>
        
        <h2>🏆 Top Performers</h2>
        <p><strong>Fastest Test:</strong> {summary.get('fastest_test', {}).get('name', 'N/A')} 
           ({summary.get('fastest_test', {}).get('ops_per_second', 0):.0f} ops/sec)</p>
        <p><strong>Slowest Test:</strong> {summary.get('slowest_test', {}).get('name', 'N/A')} 
           ({summary.get('slowest_test', {}).get('ops_per_second', 0):.0f} ops/sec)</p>
        
        <h2>📈 Detailed Results</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Operations/sec</th>
                <th>Mean Time (ms)</th>
                <th>95th Percentile (ms)</th>
                <th>Success Rate</th>
                <th>Memory Usage (MB)</th>
                <th>Status</th>
            </tr>
"""
        
        for benchmark in benchmarks:
            ops_per_sec = benchmark.get('operations_per_second', 0)
            mean_time = benchmark.get('mean_time', 0) * 1000  # Convert to ms
            p95_time = benchmark.get('percentile_95', 0) * 1000  # Convert to ms
            success_rate = benchmark.get('success_rate', 0) * 100
            memory_mb = benchmark.get('memory_usage_mb', 0)
            
            # Determine status
            if success_rate > 95 and ops_per_sec > 1000:
                status = '<span class="good">✓ Good</span>'
            elif success_rate > 80 and ops_per_sec > 500:
                status = '<span class="warning">⚠ Fair</span>'
            else:
                status = '<span class="bad">✗ Poor</span>'
            
            html_content += f"""
            <tr>
                <td>{benchmark.get('test_name', 'Unknown')}</td>
                <td>{ops_per_sec:.1f}</td>
                <td>{mean_time:.3f}</td>
                <td>{p95_time:.3f}</td>
                <td>{success_rate:.1f}%</td>
                <td>{memory_mb:.1f}</td>
                <td>{status}</td>
            </tr>
"""
        
        html_content += f"""
        </table>
        
        <div class="recommendations">
            <h2>💡 Recommendations</h2>
            <ul>
"""
        
        for recommendation in report.get('recommendations', []):
            html_content += f"<li>{recommendation}</li>"
        
        html_content += """
            </ul>
        </div>
        
        <h2>🔧 System Information</h2>
        <p><strong>Platform:</strong> """ + str(report.get('system_info', {}).get('system_info', {}).get('platform', 'Unknown')) + """</p>
        <p><strong>Python Version:</strong> """ + str(report.get('system_info', {}).get('system_info', {}).get('python_version', 'Unknown')) + """</p>
        <p><strong>Package Version:</strong> """ + str(report.get('system_info', {}).get('package_info', {}).get('package_version', 'Unknown')) + """</p>
        
    </div>
</body>
</html>"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    def compare_with_baseline(self) -> Optional[Dict[str, Any]]:
        """Compare results with baseline if available."""
        if not self.baseline_file or not self.baseline_file.exists():
            print("No baseline file available for comparison")
            return None
        
        print(f"Comparing with baseline: {self.baseline_file}")
        
        try:
            benchmark = AdvancedBenchmark("comparison")
            benchmark.results = [type('Result', (), result) for result in self.benchmark_results]
            
            comparison = benchmark.compare_with_baseline(self.baseline_file, tolerance=0.1)
            
            # Save comparison report
            comparison_file = self.output_dir / f"baseline_comparison_{self.timestamp}.json"
            with open(comparison_file, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
            
            print(f"Baseline comparison saved to: {comparison_file}")
            
            # Print summary
            summary = comparison.get('summary', {})
            print(f"\nBaseline Comparison Summary:")
            print(f"  Improved tests: {summary.get('improved', 0)}")
            print(f"  Stable tests: {summary.get('stable', 0)}")
            print(f"  Degraded tests: {summary.get('degraded', 0)}")
            print(f"  New tests: {summary.get('new_tests', 0)}")
            
            return comparison
            
        except Exception as e:
            print(f"Error comparing with baseline: {e}")
            return None


def main():
    """Main entry point for performance test runner."""
    parser = argparse.ArgumentParser(description="Blackholio Python Client Performance Test Runner")
    
    parser.add_argument("--output-dir", "-o", 
                       default="performance_results",
                       help="Output directory for results")
    
    parser.add_argument("--baseline", "-b",
                       help="Baseline file for comparison")
    
    parser.add_argument("--test-pattern", "-p",
                       default="test_performance.py",
                       help="Test file pattern")
    
    parser.add_argument("--skip-profiling", "-s",
                       action="store_true",
                       help="Skip memory and CPU profiling")
    
    parser.add_argument("--quick", "-q",
                       action="store_true", 
                       help="Run quick tests only")
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = PerformanceTestRunner(
        output_dir=args.output_dir,
        baseline_file=args.baseline
    )
    
    print("🚀 Starting Blackholio Python Client Performance Testing")
    print("=" * 60)
    
    # Collect system information
    runner.collect_system_info()
    
    # Prepare pytest arguments
    pytest_args = []
    if args.quick:
        pytest_args.extend(["-k", "not load_test"])
    
    # Run performance tests
    test_success = runner.run_performance_tests(
        test_pattern=args.test_pattern,
        pytest_args=pytest_args
    )
    
    if not test_success:
        print("⚠️  Performance tests failed!")
    
    # Run profiling (unless skipped)
    if not args.skip_profiling:
        runner.run_memory_profiling()
        runner.run_cpu_profiling()
    
    # Generate reports
    report = runner.generate_performance_report()
    
    # Compare with baseline
    if args.baseline:
        runner.compare_with_baseline()
    
    print("=" * 60)
    print("✅ Performance testing completed!")
    print(f"📁 Results saved to: {runner.output_dir}")
    
    # Return appropriate exit code
    return 0 if test_success else 1


if __name__ == "__main__":
    sys.exit(main())