"""
Benchmarking Utilities - Specialized Performance Testing Tools

Provides advanced benchmarking capabilities for measuring performance characteristics
of the blackholio-python-client package components.
"""

import asyncio
import gc
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
import threading

import psutil
import memory_profiler

from blackholio_client.utils.debugging import PerformanceProfiler


@dataclass
class BenchmarkResult:
    """Detailed benchmark result with comprehensive metrics."""
    name: str
    description: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    std_dev: float
    percentile_90: float
    percentile_95: float
    percentile_99: float
    operations_per_second: float
    memory_usage_mb: float
    memory_peak_mb: float
    cpu_percent: float
    success_count: int
    failure_count: int
    success_rate: float
    error_messages: List[str]
    execution_times: List[float]
    additional_metrics: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class AdvancedBenchmark:
    """
    Advanced benchmarking framework with comprehensive metrics collection.
    
    Provides detailed performance analysis including timing, memory usage,
    CPU utilization, and statistical analysis of results.
    """
    
    def __init__(self, name: str = "benchmark"):
        """
        Initialize benchmark.
        
        Args:
            name: Benchmark name for identification
        """
        self.name = name
        self.process = psutil.Process()
        self.results: List[BenchmarkResult] = []
        
    def run_benchmark(self,
                     func: Callable,
                     iterations: int = 1000,
                     warmup_iterations: int = 100,
                     description: str = "",
                     collect_memory: bool = True,
                     collect_cpu: bool = True,
                     **kwargs) -> BenchmarkResult:
        """
        Run comprehensive benchmark of a function.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            description: Description of the benchmark
            collect_memory: Whether to collect memory metrics
            collect_cpu: Whether to collect CPU metrics
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Detailed benchmark result
        """
        print(f"Running benchmark: {self.name} - {description}")
        print(f"Iterations: {iterations}, Warmup: {warmup_iterations}")
        
        # Warmup phase
        print("Running warmup...")
        for _ in range(warmup_iterations):
            try:
                func(**kwargs)
            except Exception as e:
                print(f"Warmup error (ignored): {e}")
        
        # Collect garbage before measurement
        gc.collect()
        
        # Initialize tracking variables
        execution_times = []
        error_messages = []
        success_count = 0
        failure_count = 0
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        # Run benchmark iterations
        print("Running benchmark...")
        start_time = time.perf_counter()
        
        for i in range(iterations):
            iter_start = time.perf_counter()
            
            try:
                func(**kwargs)
                success_count += 1
            except Exception as e:
                failure_count += 1
                error_messages.append(f"Iteration {i}: {str(e)}")
                if len(error_messages) < 10:  # Limit error message collection
                    error_messages.append(str(e))
            
            iter_end = time.perf_counter()
            execution_times.append(iter_end - iter_start)
            
            # Track peak memory usage
            if collect_memory and i % 100 == 0:  # Sample every 100 iterations
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Collect final metrics
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_usage = final_memory - initial_memory
        cpu_percent = self.process.cpu_percent() if collect_cpu else 0.0
        
        # Calculate statistics
        if execution_times:
            min_time = min(execution_times)
            max_time = max(execution_times)
            mean_time = statistics.mean(execution_times)
            median_time = statistics.median(execution_times)
            std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
            
            # Calculate percentiles
            sorted_times = sorted(execution_times)
            percentile_90 = sorted_times[int(0.90 * len(sorted_times))]
            percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            percentile_99 = sorted_times[int(0.99 * len(sorted_times))]
        else:
            min_time = max_time = mean_time = median_time = std_dev = 0.0
            percentile_90 = percentile_95 = percentile_99 = 0.0
        
        # Calculate operations per second
        ops_per_second = success_count / total_time if total_time > 0 else 0.0
        success_rate = success_count / iterations if iterations > 0 else 0.0
        
        # Create result
        result = BenchmarkResult(
            name=self.name,
            description=description,
            iterations=iterations,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            mean_time=mean_time,
            median_time=median_time,
            std_dev=std_dev,
            percentile_90=percentile_90,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            operations_per_second=ops_per_second,
            memory_usage_mb=memory_usage,
            memory_peak_mb=peak_memory - initial_memory,
            cpu_percent=cpu_percent,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_rate,
            error_messages=error_messages[:10],  # Limit error messages
            execution_times=execution_times,
            additional_metrics={},
            timestamp=time.time()
        )
        
        self.results.append(result)
        
        # Print summary
        print(f"Benchmark completed:")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Operations/sec: {ops_per_second:.1f}")
        print(f"  Mean time: {mean_time*1000:.3f}ms")
        print(f"  95th percentile: {percentile_95*1000:.3f}ms")
        print(f"  Memory usage: {memory_usage:.1f}MB")
        if failure_count > 0:
            print(f"  Failures: {failure_count}")
        print()
        
        return result
    
    async def run_async_benchmark(self,
                                 async_func: Callable,
                                 iterations: int = 1000,
                                 warmup_iterations: int = 100,
                                 description: str = "",
                                 **kwargs) -> BenchmarkResult:
        """
        Run benchmark of an async function.
        
        Args:
            async_func: Async function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            description: Description of the benchmark
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Detailed benchmark result
        """
        print(f"Running async benchmark: {self.name} - {description}")
        
        # Warmup phase
        print("Running async warmup...")
        for _ in range(warmup_iterations):
            try:
                await async_func(**kwargs)
            except Exception as e:
                print(f"Warmup error (ignored): {e}")
        
        # Collect garbage before measurement
        gc.collect()
        
        # Initialize tracking variables
        execution_times = []
        error_messages = []
        success_count = 0
        failure_count = 0
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        # Run benchmark iterations
        print("Running async benchmark...")
        start_time = time.perf_counter()
        
        for i in range(iterations):
            iter_start = time.perf_counter()
            
            try:
                await async_func(**kwargs)
                success_count += 1
            except Exception as e:
                failure_count += 1
                if len(error_messages) < 10:
                    error_messages.append(str(e))
            
            iter_end = time.perf_counter()
            execution_times.append(iter_end - iter_start)
            
            # Track peak memory usage
            if i % 100 == 0:  # Sample every 100 iterations
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Calculate final metrics (same as sync version)
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_usage = final_memory - initial_memory
        cpu_percent = self.process.cpu_percent()
        
        # Calculate statistics (same as sync version)
        if execution_times:
            min_time = min(execution_times)
            max_time = max(execution_times)
            mean_time = statistics.mean(execution_times)
            median_time = statistics.median(execution_times)
            std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
            
            sorted_times = sorted(execution_times)
            percentile_90 = sorted_times[int(0.90 * len(sorted_times))]
            percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            percentile_99 = sorted_times[int(0.99 * len(sorted_times))]
        else:
            min_time = max_time = mean_time = median_time = std_dev = 0.0
            percentile_90 = percentile_95 = percentile_99 = 0.0
        
        ops_per_second = success_count / total_time if total_time > 0 else 0.0
        success_rate = success_count / iterations if iterations > 0 else 0.0
        
        # Create result
        result = BenchmarkResult(
            name=f"{self.name}_async",
            description=description,
            iterations=iterations,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            mean_time=mean_time,
            median_time=median_time,
            std_dev=std_dev,
            percentile_90=percentile_90,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            operations_per_second=ops_per_second,
            memory_usage_mb=memory_usage,
            memory_peak_mb=peak_memory - initial_memory,
            cpu_percent=cpu_percent,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_rate,
            error_messages=error_messages,
            execution_times=execution_times,
            additional_metrics={'async': True},
            timestamp=time.time()
        )
        
        self.results.append(result)
        
        # Print summary
        print(f"Async benchmark completed:")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Operations/sec: {ops_per_second:.1f}")
        print(f"  Mean time: {mean_time*1000:.3f}ms")
        print(f"  95th percentile: {percentile_95*1000:.3f}ms")
        print(f"  Memory usage: {memory_usage:.1f}MB")
        if failure_count > 0:
            print(f"  Failures: {failure_count}")
        print()
        
        return result
    
    def run_load_test(self,
                     func: Callable,
                     concurrent_users: int = 10,
                     operations_per_user: int = 100,
                     ramp_up_time: float = 1.0,
                     description: str = "",
                     **kwargs) -> BenchmarkResult:
        """
        Run load test with concurrent users.
        
        Args:
            func: Function to test
            concurrent_users: Number of concurrent users
            operations_per_user: Operations per user
            ramp_up_time: Time to ramp up all users (seconds)
            description: Description of the test
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Load test result
        """
        print(f"Running load test: {self.name} - {description}")
        print(f"Concurrent users: {concurrent_users}, Ops per user: {operations_per_user}")
        
        total_operations = concurrent_users * operations_per_user
        execution_times = []
        error_messages = []
        success_count = 0
        failure_count = 0
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        def user_worker(user_id: int, start_delay: float):
            """Worker function for each simulated user."""
            time.sleep(start_delay)  # Ramp-up delay
            
            user_times = []
            user_successes = 0
            user_failures = 0
            
            for _ in range(operations_per_user):
                iter_start = time.perf_counter()
                
                try:
                    func(**kwargs)
                    user_successes += 1
                except Exception as e:
                    user_failures += 1
                    if len(error_messages) < 20:  # Limit error collection
                        error_messages.append(f"User {user_id}: {str(e)}")
                
                iter_end = time.perf_counter()
                user_times.append(iter_end - iter_start)
            
            return user_times, user_successes, user_failures
        
        # Start load test
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            # Submit workers with staggered start times
            futures = []
            for user_id in range(concurrent_users):
                start_delay = (user_id / concurrent_users) * ramp_up_time
                future = executor.submit(user_worker, user_id, start_delay)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    times, successes, failures = future.result()
                    execution_times.extend(times)
                    success_count += successes
                    failure_count += failures
                except Exception as e:
                    error_messages.append(f"Worker error: {str(e)}")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Collect final metrics
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_usage = final_memory - initial_memory
        cpu_percent = self.process.cpu_percent()
        
        # Calculate statistics
        if execution_times:
            min_time = min(execution_times)
            max_time = max(execution_times)
            mean_time = statistics.mean(execution_times)
            median_time = statistics.median(execution_times)
            std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
            
            sorted_times = sorted(execution_times)
            percentile_90 = sorted_times[int(0.90 * len(sorted_times))]
            percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            percentile_99 = sorted_times[int(0.99 * len(sorted_times))]
        else:
            min_time = max_time = mean_time = median_time = std_dev = 0.0
            percentile_90 = percentile_95 = percentile_99 = 0.0
        
        ops_per_second = success_count / total_time if total_time > 0 else 0.0
        success_rate = success_count / total_operations if total_operations > 0 else 0.0
        
        # Create result
        result = BenchmarkResult(
            name=f"{self.name}_load_test",
            description=description,
            iterations=total_operations,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            mean_time=mean_time,
            median_time=median_time,
            std_dev=std_dev,
            percentile_90=percentile_90,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            operations_per_second=ops_per_second,
            memory_usage_mb=memory_usage,
            memory_peak_mb=peak_memory - initial_memory,
            cpu_percent=cpu_percent,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_rate,
            error_messages=error_messages[:20],
            execution_times=execution_times,
            additional_metrics={
                'concurrent_users': concurrent_users,
                'operations_per_user': operations_per_user,
                'ramp_up_time': ramp_up_time,
                'load_test': True
            },
            timestamp=time.time()
        )
        
        self.results.append(result)
        
        # Print summary
        print(f"Load test completed:")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Total operations: {total_operations}")
        print(f"  Operations/sec: {ops_per_second:.1f}")
        print(f"  Mean time: {mean_time*1000:.3f}ms")
        print(f"  95th percentile: {percentile_95*1000:.3f}ms")
        print(f"  Memory usage: {memory_usage:.1f}MB")
        if failure_count > 0:
            print(f"  Failures: {failure_count}")
        print()
        
        return result
    
    def compare_with_baseline(self, 
                             baseline_file: Union[str, Path],
                             tolerance: float = 0.1) -> Dict[str, Any]:
        """
        Compare current results with baseline performance.
        
        Args:
            baseline_file: Path to baseline results file
            tolerance: Performance degradation tolerance (0.1 = 10%)
            
        Returns:
            Comparison report
        """
        baseline_path = Path(baseline_file)
        if not baseline_path.exists():
            return {'error': f'Baseline file not found: {baseline_path}'}
        
        # Load baseline results
        with open(baseline_path, 'r') as f:
            baseline_data = json.load(f)
        
        # Compare results
        comparison = {
            'baseline_file': str(baseline_path),
            'tolerance': tolerance,
            'comparisons': [],
            'summary': {
                'total_tests': 0,
                'improved': 0,
                'degraded': 0,
                'stable': 0,
                'new_tests': 0
            }
        }
        
        # Create lookup for baseline results
        baseline_lookup = {result['name']: result for result in baseline_data}
        
        for current_result in self.results:
            test_name = current_result.name
            comparison['summary']['total_tests'] += 1
            
            if test_name not in baseline_lookup:
                comparison['summary']['new_tests'] += 1
                comparison['comparisons'].append({
                    'test_name': test_name,
                    'status': 'new',
                    'current_ops_per_sec': current_result.operations_per_second,
                    'baseline_ops_per_sec': None,
                    'performance_ratio': None
                })
                continue
            
            baseline_result = baseline_lookup[test_name]
            current_ops = current_result.operations_per_second
            baseline_ops = baseline_result['operations_per_second']
            
            if baseline_ops > 0:
                performance_ratio = current_ops / baseline_ops
                
                if performance_ratio > (1 + tolerance):
                    status = 'improved'
                    comparison['summary']['improved'] += 1
                elif performance_ratio < (1 - tolerance):
                    status = 'degraded'
                    comparison['summary']['degraded'] += 1
                else:
                    status = 'stable'
                    comparison['summary']['stable'] += 1
            else:
                performance_ratio = None
                status = 'unknown'
            
            comparison['comparisons'].append({
                'test_name': test_name,
                'status': status,
                'current_ops_per_sec': current_ops,
                'baseline_ops_per_sec': baseline_ops,
                'performance_ratio': performance_ratio,
                'current_mean_time': current_result.mean_time,
                'baseline_mean_time': baseline_result.get('mean_time', 0),
                'current_memory_mb': current_result.memory_usage_mb,
                'baseline_memory_mb': baseline_result.get('memory_usage_mb', 0)
            })
        
        return comparison
    
    def export_results(self, file_path: Union[str, Path], format: str = 'json') -> Path:
        """
        Export benchmark results.
        
        Args:
            file_path: Output file path
            format: Export format ('json', 'csv', 'html')
            
        Returns:
            Path to exported file
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            with open(output_path, 'w') as f:
                json.dump([result.to_dict() for result in self.results], f, indent=2, default=str)
        
        elif format.lower() == 'csv':
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if self.results:
                    writer = csv.DictWriter(f, fieldnames=self.results[0].to_dict().keys())
                    writer.writeheader()
                    for result in self.results:
                        writer.writerow(result.to_dict())
        
        elif format.lower() == 'html':
            self._export_html_report(output_path)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return output_path
    
    def _export_html_report(self, file_path: Path):
        """Export HTML performance report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Benchmark Report - {self.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ color: #007bff; font-weight: bold; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .bad {{ color: #dc3545; }}
    </style>
</head>
<body>
    <h1>Performance Benchmark Report</h1>
    <h2>Benchmark: {self.name}</h2>
    <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h3>Summary</h3>
    <ul>
        <li>Total tests: {len(self.results)}</li>
        <li>Average success rate: {sum(r.success_rate for r in self.results) / len(self.results) * 100:.1f}%</li>
    </ul>
    
    <h3>Detailed Results</h3>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Operations/sec</th>
            <th>Mean Time (ms)</th>
            <th>95th Percentile (ms)</th>
            <th>Success Rate</th>
            <th>Memory Usage (MB)</th>
        </tr>
"""
        
        for result in self.results:
            success_class = "good" if result.success_rate > 0.95 else "warning" if result.success_rate > 0.8 else "bad"
            html_content += f"""
        <tr>
            <td>{result.name}</td>
            <td class="metric">{result.operations_per_second:.1f}</td>
            <td>{result.mean_time * 1000:.3f}</td>
            <td>{result.percentile_95 * 1000:.3f}</td>
            <td class="{success_class}">{result.success_rate * 100:.1f}%</td>
            <td>{result.memory_usage_mb:.1f}</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>"""
        
        with open(file_path, 'w') as f:
            f.write(html_content)


@contextmanager
def memory_profiler_context():
    """Context manager for memory profiling."""
    import tracemalloc
    
    tracemalloc.start()
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    try:
        yield
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        print(f"Memory usage: {final_memory - initial_memory:.1f}MB")
        print(f"Peak traced memory: {peak / 1024 / 1024:.1f}MB")


def run_comparative_benchmark(baseline_func: Callable,
                            optimized_func: Callable,
                            iterations: int = 1000,
                            name: str = "comparison") -> Tuple[BenchmarkResult, BenchmarkResult]:
    """
    Run comparative benchmark between two implementations.
    
    Args:
        baseline_func: Baseline implementation
        optimized_func: Optimized implementation
        iterations: Number of iterations
        name: Benchmark name
        
    Returns:
        Tuple of (baseline_result, optimized_result)
    """
    baseline_benchmark = AdvancedBenchmark(f"{name}_baseline")
    optimized_benchmark = AdvancedBenchmark(f"{name}_optimized")
    
    baseline_result = baseline_benchmark.run_benchmark(
        baseline_func,
        iterations=iterations,
        description=f"Baseline implementation"
    )
    
    optimized_result = optimized_benchmark.run_benchmark(
        optimized_func,
        iterations=iterations,
        description=f"Optimized implementation"
    )
    
    # Print comparison
    print(f"\nComparison Results for {name}:")
    print(f"Baseline:  {baseline_result.operations_per_second:.1f} ops/sec")
    print(f"Optimized: {optimized_result.operations_per_second:.1f} ops/sec")
    
    if baseline_result.operations_per_second > 0:
        improvement = (optimized_result.operations_per_second / baseline_result.operations_per_second - 1) * 100
        print(f"Improvement: {improvement:.1f}%")
    
    return baseline_result, optimized_result


if __name__ == "__main__":
    # Example usage
    def example_function():
        """Example function for testing."""
        import random
        import math
        
        data = [random.random() for _ in range(100)]
        result = sum(math.sqrt(x) for x in data)
        return result
    
    # Run example benchmark
    benchmark = AdvancedBenchmark("example")
    result = benchmark.run_benchmark(
        example_function,
        iterations=1000,
        description="Example mathematical operations"
    )
    
    # Export results
    benchmark.export_results("example_benchmark.json")
    benchmark.export_results("example_benchmark.html", format="html")
    
    print("Example benchmark completed!")