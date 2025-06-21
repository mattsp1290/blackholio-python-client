"""
Debugging Utilities - Comprehensive Debugging and Error Reporting Tools

Provides advanced debugging tools, error reporting capabilities, diagnostic
utilities, and development helpers for the blackholio client package.
"""

import inspect
import json
import logging
import os
import pprint
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union, TextIO
from datetime import datetime
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..exceptions.connection_errors import BlackholioConnectionError, get_error_category
from .logging_config import get_logger


@dataclass
class DebugContext:
    """Context information for debugging."""
    timestamp: float
    thread_id: int
    function: str
    module: str
    filename: str
    line_number: int
    locals_snapshot: Dict[str, str]
    call_stack: List[str]
    extra_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class ErrorReport:
    """Comprehensive error report."""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    error_category: str
    traceback_lines: List[str]
    context: DebugContext
    system_info: Dict[str, Any]
    environment_info: Dict[str, str]
    performance_metrics: Dict[str, Any]
    additional_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def save_to_file(self, file_path: Union[str, Path]) -> Path:
        """Save error report to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        path = Path(path).resolve()
        if not str(path).startswith(str(Path.cwd())):
            raise ValueError(f"Path traversal detected: {path}")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        
        return path


class DebugCapture:
    """
    Context manager for capturing debug information.
    
    Captures local variables, call stack, timing information,
    and other debugging context during execution.
    """
    
    def __init__(self, 
                 capture_locals: bool = True,
                 capture_stack: bool = True,
                 max_locals_size: int = 1000,
                 max_stack_depth: int = 10):
        """
        Initialize debug capture.
        
        Args:
            capture_locals: Whether to capture local variables
            capture_stack: Whether to capture call stack
            max_locals_size: Maximum size of local variable values
            max_stack_depth: Maximum depth of call stack to capture
        """
        self.capture_locals = capture_locals
        self.capture_stack = capture_stack
        self.max_locals_size = max_locals_size
        self.max_stack_depth = max_stack_depth
        
        self.start_time: Optional[float] = None
        self.context: Optional[DebugContext] = None
        self.logger = get_logger(__name__)
    
    def __enter__(self) -> 'DebugCapture':
        """Enter debug capture context."""
        self.start_time = time.time()
        
        # Get caller frame
        frame = inspect.currentframe().f_back
        
        # Capture context
        self.context = self._capture_context(frame)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit debug capture context."""
        if exc_type is not None:
            self.logger.debug(f"Exception in debug context: {exc_type.__name__}: {exc_val}")
            
            # Add exception info to context
            if self.context:
                self.context.extra_data['exception_type'] = exc_type.__name__
                self.context.extra_data['exception_message'] = str(exc_val)
                
                if self.start_time:
                    self.context.extra_data['execution_time'] = time.time() - self.start_time
    
    def _capture_context(self, frame) -> DebugContext:
        """Capture debugging context from frame."""
        # Basic frame information
        filename = frame.f_code.co_filename
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        module = inspect.getmodule(frame).__name__ if inspect.getmodule(frame) else 'unknown'
        
        # Capture local variables
        locals_snapshot = {}
        if self.capture_locals:
            for name, value in frame.f_locals.items():
                try:
                    # Convert to string and limit size
                    str_value = str(value)
                    if len(str_value) > self.max_locals_size:
                        str_value = str_value[:self.max_locals_size] + "... [truncated]"
                    locals_snapshot[name] = str_value
                except Exception:
                    locals_snapshot[name] = "<unable to convert to string>"
        
        # Capture call stack
        call_stack = []
        if self.capture_stack:
            stack = inspect.stack()[2:self.max_stack_depth + 2]  # Skip current and caller frames
            for frame_info in stack:
                call_stack.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
        
        return DebugContext(
            timestamp=time.time(),
            thread_id=threading.get_ident(),
            function=function,
            module=module,
            filename=filename,
            line_number=line_number,
            locals_snapshot=locals_snapshot,
            call_stack=call_stack,
            extra_data={}
        )
    
    def get_context(self) -> Optional[DebugContext]:
        """Get captured context."""
        return self.context


class PerformanceProfiler:
    """
    Performance profiler for debugging performance issues.
    
    Tracks execution times, memory usage, and other performance metrics.
    """
    
    def __init__(self, name: str = "profiler"):
        """
        Initialize performance profiler.
        
        Args:
            name: Profiler name for identification
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.checkpoints: List[Dict[str, Any]] = []
        self.logger = get_logger(__name__)
    
    def start(self):
        """Start profiling."""
        self.start_time = time.time()
        self.checkpoints.clear()
        self.logger.debug(f"Performance profiler '{self.name}' started")
    
    def checkpoint(self, name: str, **kwargs):
        """
        Add performance checkpoint.
        
        Args:
            name: Checkpoint name
            **kwargs: Additional data to record
        """
        if self.start_time is None:
            self.logger.warning("Profiler checkpoint called before start()")
            return
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        checkpoint_data = {
            'name': name,
            'timestamp': current_time,
            'elapsed_time': elapsed,
            'delta_time': elapsed - (self.checkpoints[-1]['elapsed_time'] if self.checkpoints else 0),
            **kwargs
        }
        
        self.checkpoints.append(checkpoint_data)
        self.logger.debug(f"Checkpoint '{name}' at {elapsed:.4f}s")
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop profiling and return results.
        
        Returns:
            Performance metrics
        """
        if self.start_time is None:
            self.logger.warning("Profiler stop() called before start()")
            return {}
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        metrics = {
            'profiler_name': self.name,
            'total_time': total_time,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'checkpoints': self.checkpoints,
            'checkpoint_count': len(self.checkpoints)
        }
        
        self.logger.info(f"Performance profiler '{self.name}' completed in {total_time:.4f}s")
        return metrics
    
    def __enter__(self) -> 'PerformanceProfiler':
        """Enter profiler context."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit profiler context."""
        self.stop()


class ErrorReporter:
    """
    Comprehensive error reporter for debugging and monitoring.
    
    Generates detailed error reports with context, system information,
    and diagnostic data for troubleshooting and monitoring.
    """
    
    def __init__(self, 
                 report_directory: Optional[Union[str, Path]] = None,
                 auto_save: bool = True,
                 max_reports: int = 100):
        """
        Initialize error reporter.
        
        Args:
            report_directory: Directory to save error reports
            auto_save: Whether to automatically save reports to files
            max_reports: Maximum number of reports to keep in memory
        """
        self.report_directory = Path(report_directory) if report_directory else Path.cwd() / "error_reports"
        self.auto_save = auto_save
        self.max_reports = max_reports
        
        self.reports: List[ErrorReport] = []
        self.logger = get_logger(__name__)
        self._lock = threading.Lock()
        
        if self.auto_save:
            self.report_directory.mkdir(parents=True, exist_ok=True)
    
    def generate_error_id(self) -> str:
        """Generate unique error ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_id = threading.get_ident()
        return f"error_{timestamp}_{thread_id}"
    
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        import platform
        
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'system': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture(),
            'hostname': platform.node(),
            'current_directory': str(Path.cwd()),
            'script_path': sys.argv[0] if sys.argv else 'unknown'
        }
    
    def collect_environment_info(self) -> Dict[str, str]:
        """Collect environment variables (safe subset)."""
        safe_vars = [
            'PYTHONPATH', 'PATH', 'HOME', 'USER', 'USERNAME',
            'SERVER_LANGUAGE', 'SERVER_IP', 'SERVER_PORT',
            'BLACKHOLIO_LOG_LEVEL', 'BLACKHOLIO_DEBUG'
        ]
        
        env_info = {}
        for var in safe_vars:
            value = os.environ.get(var)
            if value is not None:
                env_info[var] = value
        
        return env_info
    
    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics."""
        import psutil
        
        try:
            process = psutil.Process()
            return {
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time(),
                'uptime': time.time() - process.create_time()
            }
        except Exception:
            return {'error': 'Unable to collect performance metrics'}
    
    def create_error_report(self, 
                          exception: Exception,
                          context: Optional[DebugContext] = None,
                          additional_data: Optional[Dict[str, Any]] = None) -> ErrorReport:
        """
        Create comprehensive error report.
        
        Args:
            exception: Exception that occurred
            context: Optional debug context
            additional_data: Additional data to include
            
        Returns:
            Error report
        """
        error_id = self.generate_error_id()
        
        # Get traceback
        tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
        
        # Create context if not provided
        if context is None:
            frame = inspect.currentframe().f_back
            with DebugCapture() as debug_capture:
                debug_capture._capture_context(frame)
                context = debug_capture.get_context()
        
        # Create error report
        report = ErrorReport(
            error_id=error_id,
            timestamp=datetime.now(),
            error_type=type(exception).__name__,
            error_message=str(exception),
            error_category=get_error_category(exception),
            traceback_lines=tb_lines,
            context=context or DebugContext(
                timestamp=time.time(),
                thread_id=threading.get_ident(),
                function='unknown',
                module='unknown',
                filename='unknown',
                line_number=0,
                locals_snapshot={},
                call_stack=[],
                extra_data={}
            ),
            system_info=self.collect_system_info(),
            environment_info=self.collect_environment_info(),
            performance_metrics=self.collect_performance_metrics(),
            additional_data=additional_data or {}
        )
        
        # Store report
        with self._lock:
            self.reports.append(report)
            
            # Limit number of reports in memory
            if len(self.reports) > self.max_reports:
                self.reports.pop(0)
        
        # Auto-save if enabled
        if self.auto_save:
            try:
                filename = f"{error_id}.json"
                file_path = self.report_directory / filename
                report.save_to_file(file_path)
                self.logger.info(f"Error report saved to {file_path}")
            except Exception as save_error:
                self.logger.error(f"Failed to save error report: {save_error}")
        
        return report
    
    def get_reports(self, 
                   error_type: Optional[str] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[ErrorReport]:
        """
        Get error reports with optional filtering.
        
        Args:
            error_type: Filter by error type
            since: Get reports since this datetime
            limit: Maximum number of reports to return
            
        Returns:
            List of error reports
        """
        with self._lock:
            reports = list(self.reports)
        
        # Apply filters
        if error_type:
            reports = [r for r in reports if r.error_type == error_type]
        
        if since:
            reports = [r for r in reports if r.timestamp >= since]
        
        # Sort by timestamp (newest first)
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        
        if limit:
            reports = reports[:limit]
        
        return reports
    
    def export_reports(self, 
                      file_path: Union[str, Path],
                      format: str = 'json',
                      **filter_kwargs) -> Path:
        """
        Export error reports to file.
        
        Args:
            file_path: Output file path
            format: Export format ('json' or 'csv')
            **filter_kwargs: Filtering arguments for get_reports()
            
        Returns:
            Path to exported file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        reports = self.get_reports(**filter_kwargs)
        
        if format.lower() == 'json':
            path = Path(path).resolve()
            if not str(path).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {path}")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in reports], f, indent=2, default=str)
        elif format.lower() == 'csv':
            import csv
            path = Path(path).resolve()
            if not str(path).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {path}")
            with open(path, 'w', newline='', encoding='utf-8') as f:
                if reports:
                    writer = csv.DictWriter(f, fieldnames=reports[0].to_dict().keys())
                    writer.writeheader()
                    for report in reports:
                        writer.writerow(report.to_dict())
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Exported {len(reports)} error reports to {path}")
        return path


class DiagnosticCollector:
    """
    Collects diagnostic information for troubleshooting.
    
    Gathers system state, configuration, logs, and other diagnostic
    data to help with debugging and support.
    """
    
    def __init__(self):
        """Initialize diagnostic collector."""
        self.logger = get_logger(__name__)
    
    def collect_package_info(self) -> Dict[str, Any]:
        """Collect blackholio client package information."""
        try:
            from .. import __version__
            version = __version__
        except ImportError:
            version = 'unknown'
        
        info = {
            'package_version': version,
            'package_path': str(Path(__file__).parent.parent),
            'python_path': sys.path.copy()
        }
        
        # Check if package is in development mode
        try:
            import pkg_resources
            dist = pkg_resources.get_distribution('blackholio-client')
            info['distribution_location'] = dist.location
            info['distribution_version'] = dist.version
        except Exception:
            info['distribution_info'] = 'Package not installed via pip'
        
        return info
    
    def collect_dependency_info(self) -> Dict[str, Any]:
        """Collect information about dependencies."""
        dependencies = {}
        
        # Check for key dependencies
        key_deps = ['websockets', 'aiohttp', 'requests', 'pydantic', 'numpy']
        
        for dep in key_deps:
            try:
                module = __import__(dep)
                version = getattr(module, '__version__', 'unknown')
                dependencies[dep] = {
                    'version': version,
                    'location': getattr(module, '__file__', 'unknown')
                }
            except ImportError:
                dependencies[dep] = {'status': 'not_installed'}
            except Exception as e:
                dependencies[dep] = {'status': 'error', 'error': str(e)}
        
        return dependencies
    
    def collect_configuration_info(self) -> Dict[str, Any]:
        """Collect configuration information."""
        try:
            from ..config.environment import get_environment_config
            config = get_environment_config()
            
            # Get safe configuration (excluding sensitive data)
            config_dict = config.to_dict()
            
            # Remove sensitive fields
            sensitive_fields = ['password', 'token', 'key', 'secret']
            safe_config = {}
            
            for key, value in config_dict.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    safe_config[key] = '[REDACTED]'
                else:
                    safe_config[key] = value
            
            return safe_config
            
        except Exception as e:
            return {'error': f'Unable to collect configuration: {e}'}
    
    def collect_connection_info(self) -> Dict[str, Any]:
        """Collect connection-related diagnostic information."""
        try:
            from ..connection.connection_manager import get_connection_manager
            manager = get_connection_manager()
            
            return {
                'connection_manager_status': manager.get_status(),
                'active_connections': manager.get_active_connections_count(),
                'connection_metrics': manager.get_metrics()
            }
        except Exception as e:
            return {'error': f'Unable to collect connection info: {e}'}
    
    def run_connectivity_tests(self) -> Dict[str, Any]:
        """Run basic connectivity tests."""
        tests = {}
        
        # Test network connectivity
        try:
            import socket
            socket.create_connection(('8.8.8.8', 53), timeout=5)
            tests['internet_connectivity'] = 'ok'
        except Exception as e:
            tests['internet_connectivity'] = f'failed: {e}'
        
        # Test DNS resolution
        try:
            import socket
            socket.gethostbyname('google.com')
            tests['dns_resolution'] = 'ok'
        except Exception as e:
            tests['dns_resolution'] = f'failed: {e}'
        
        return tests
    
    def generate_diagnostic_report(self) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report."""
        self.logger.info("Generating diagnostic report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'report_version': '1.0',
            'system_info': ErrorReporter().collect_system_info(),
            'environment_info': ErrorReporter().collect_environment_info(),
            'performance_metrics': ErrorReporter().collect_performance_metrics(),
            'package_info': self.collect_package_info(),
            'dependency_info': self.collect_dependency_info(),
            'configuration_info': self.collect_configuration_info(),
            'connection_info': self.collect_connection_info(),
            'connectivity_tests': self.run_connectivity_tests()
        }
        
        self.logger.info("Diagnostic report generated successfully")
        return report
    
    def save_diagnostic_report(self, file_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Save diagnostic report to file.
        
        Args:
            file_path: Optional file path, defaults to timestamp-based name
            
        Returns:
            Path to saved report
        """
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = Path.cwd() / f"blackholio_diagnostics_{timestamp}.json"
        else:
            file_path = Path(file_path)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_diagnostic_report()
        
        file_path = Path(file_path).resolve()
        if not str(file_path).startswith(str(Path.cwd())):
            raise ValueError(f"Path traversal detected: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Diagnostic report saved to {file_path}")
        return file_path


# Debugging decorators and context managers
@contextmanager
def debug_context(name: str = "debug_context", 
                 capture_locals: bool = True,
                 log_entry_exit: bool = True):
    """
    Context manager for debugging with automatic context capture.
    
    Args:
        name: Context name for logging
        capture_locals: Whether to capture local variables
        log_entry_exit: Whether to log entry and exit
    """
    logger = get_logger(__name__)
    
    if log_entry_exit:
        logger.debug(f"Entering debug context: {name}")
    
    with DebugCapture(capture_locals=capture_locals) as capture:
        try:
            yield capture
        except Exception as e:
            logger.error(f"Exception in debug context '{name}': {e}", exc_info=True)
            
            # Create error report
            reporter = ErrorReporter()
            context = capture.get_context()
            report = reporter.create_error_report(e, context)
            logger.info(f"Error report created: {report.error_id}")
            
            raise
        finally:
            if log_entry_exit:
                logger.debug(f"Exiting debug context: {name}")


def debug_function(capture_args: bool = True, 
                  capture_return: bool = True,
                  log_performance: bool = True):
    """
    Decorator for debugging functions.
    
    Args:
        capture_args: Whether to capture function arguments
        capture_return: Whether to capture return value
        log_performance: Whether to log performance metrics
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Capture arguments
            call_info = {}
            if capture_args:
                call_info['args'] = [str(arg)[:100] for arg in args]  # Limit size
                call_info['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
            
            with PerformanceProfiler(func_name) as profiler:
                try:
                    result = func(*args, **kwargs)
                    
                    if capture_return:
                        call_info['return_value'] = str(result)[:100]  # Limit size
                    
                    if log_performance:
                        metrics = profiler.stop()
                        logger.debug(f"Function {func_name} completed", extra={
                            'function_call': call_info,
                            'performance': metrics
                        })
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Function {func_name} failed: {e}", extra={
                        'function_call': call_info,
                        'error_type': type(e).__name__
                    })
                    raise
        
        return wrapper
    return decorator


# Global instances
_global_error_reporter: Optional[ErrorReporter] = None
_global_diagnostic_collector: Optional[DiagnosticCollector] = None


def get_error_reporter() -> ErrorReporter:
    """Get global error reporter instance."""
    global _global_error_reporter
    if _global_error_reporter is None:
        _global_error_reporter = ErrorReporter()
    return _global_error_reporter


def get_diagnostic_collector() -> DiagnosticCollector:
    """Get global diagnostic collector instance."""
    global _global_diagnostic_collector
    if _global_diagnostic_collector is None:
        _global_diagnostic_collector = DiagnosticCollector()
    return _global_diagnostic_collector


# Convenience functions
def capture_exception(exception: Exception, **kwargs) -> ErrorReport:
    """Capture exception with error report."""
    reporter = get_error_reporter()
    return reporter.create_error_report(exception, **kwargs)


def generate_diagnostics(save_to_file: bool = True) -> Union[Dict[str, Any], Path]:
    """
    Generate diagnostic report.
    
    Args:
        save_to_file: Whether to save to file
        
    Returns:
        Diagnostic data or path to saved file
    """
    collector = get_diagnostic_collector()
    
    if save_to_file:
        return collector.save_diagnostic_report()
    else:
        return collector.generate_diagnostic_report()