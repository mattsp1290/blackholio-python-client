"""
Logging Configuration - Centralized Logging Setup

Provides structured logging configuration with multiple output formats,
handlers, and filtering for the blackholio client with proper log rotation
and performance considerations.
"""

import logging
import logging.handlers
import os
import sys
import time
import functools
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import json
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs log records as JSON objects for easy parsing and analysis.
    """
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    try:
                        # Only include JSON-serializable values
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    
    Adds colors to log levels for better visibility during development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, format_string: Optional[str] = None, use_colors: bool = True):
        """
        Initialize colored formatter.
        
        Args:
            format_string: Custom format string
            use_colors: Whether to use colors (auto-detected if None)
        """
        if format_string is None:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        super().__init__(format_string)
        self.use_colors = use_colors and self._supports_color()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format record with colors if enabled."""
        if self.use_colors:
            # Add color to levelname
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            
            # Format the message
            formatted = super().format(record)
            
            # Reset levelname for other formatters
            record.levelname = levelname
            
            return formatted
        else:
            return super().format(record)
    
    def _supports_color(self) -> bool:
        """Check if terminal supports colors."""
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        
        # Check for common color-supporting terminals
        term = os.environ.get('TERM', '').lower()
        return any(color_term in term for color_term in ['color', 'xterm', 'screen'])


class PerformanceFilter(logging.Filter):
    """
    Filter for performance monitoring.
    
    Adds performance metrics and filters based on execution time.
    """
    
    def __init__(self, min_duration: float = 0.1):
        """
        Initialize performance filter.
        
        Args:
            min_duration: Minimum duration in seconds to log
        """
        super().__init__()
        self.min_duration = min_duration
        self._start_times: Dict[int, float] = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter based on performance criteria."""
        # Add timing information if available
        thread_id = record.thread
        current_time = time.time()
        
        # Check for performance markers
        if hasattr(record, 'performance_start'):
            self._start_times[thread_id] = current_time
            record.duration = 0.0
            return True
        
        if hasattr(record, 'performance_end'):
            if thread_id in self._start_times:
                duration = current_time - self._start_times.pop(thread_id)
                record.duration = duration
                
                # Filter based on minimum duration
                return duration >= self.min_duration
        
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Filter to remove sensitive data from logs.
    
    Prevents passwords, tokens, and other sensitive information
    from being logged in production environments.
    """
    
    SENSITIVE_PATTERNS = [
        'password', 'passwd', 'pwd',
        'token', 'key', 'secret',
        'auth', 'credential', 'cred',
        'api_key', 'access_token',
        'private_key', 'priv_key'
    ]
    
    def __init__(self, mask_value: str = "[REDACTED]"):
        """
        Initialize sensitive data filter.
        
        Args:
            mask_value: Value to replace sensitive data with
        """
        super().__init__()
        self.mask_value = mask_value
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        # Check message
        if record.msg and isinstance(record.msg, str):
            record.msg = self._mask_sensitive_data(record.msg)
        
        # Check args
        if record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data in text."""
        import re
        
        # Simple pattern matching for common sensitive fields
        for pattern in self.SENSITIVE_PATTERNS:
            # Match key=value or key: value patterns
            regex = rf'({pattern}["\']?\s*[:=]\s*["\']?)([^,\s}}\]]+)'
            text = re.sub(regex, rf'\1{self.mask_value}', text, flags=re.IGNORECASE)
        
        return text


class LoggingConfig:
    """
    Centralized logging configuration for the blackholio client.
    
    Provides easy setup of structured logging with multiple handlers,
    formatters, and filters for different environments and use cases.
    """
    
    def __init__(self):
        """Initialize logging configuration."""
        self.handlers: Dict[str, logging.Handler] = {}
        self.formatters: Dict[str, logging.Formatter] = {}
        self.filters: Dict[str, logging.Filter] = {}
        self._configured = False
    
    def setup_logging(self,
                     level: Union[str, int] = logging.INFO,
                     format_type: str = "colored",
                     log_file: Optional[Union[str, Path]] = None,
                     json_logs: bool = False,
                     max_file_size: int = 10 * 1024 * 1024,  # 10MB
                     backup_count: int = 5,
                     performance_logging: bool = False,
                     filter_sensitive: bool = True) -> Dict[str, Any]:
        """
        Setup logging configuration.
        
        Args:
            level: Logging level
            format_type: Formatter type ('colored', 'simple', 'detailed')
            log_file: Optional log file path
            json_logs: Whether to use JSON formatting for file logs
            max_file_size: Maximum size for log files before rotation
            backup_count: Number of backup files to keep
            performance_logging: Whether to enable performance logging
            filter_sensitive: Whether to filter sensitive data
            
        Returns:
            Dictionary with configuration details
        """
        # Convert string level to int
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        # Create formatters
        self._create_formatters(format_type, json_logs)
        
        # Create filters
        self._create_filters(performance_logging, filter_sensitive)
        
        # Setup console handler
        self._setup_console_handler(level, format_type)
        
        # Setup file handler if requested
        if log_file:
            self._setup_file_handler(log_file, level, json_logs, max_file_size, backup_count)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Configure blackholio client logger specifically
        client_logger = logging.getLogger('blackholio_client')
        client_logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicates
        client_logger.handlers.clear()
        
        # Add handlers to client logger
        for handler in self.handlers.values():
            client_logger.addHandler(handler)
        
        # Prevent propagation to root logger
        client_logger.propagate = False
        
        self._configured = True
        
        config_info = {
            'level': logging.getLevelName(level),
            'handlers': list(self.handlers.keys()),
            'log_file': str(log_file) if log_file else None,
            'json_logs': json_logs,
            'performance_logging': performance_logging,
            'filter_sensitive': filter_sensitive
        }
        
        logging.info(f"Logging configured: {config_info}")
        return config_info
    
    def _create_formatters(self, format_type: str, json_logs: bool):
        """Create logging formatters."""
        # Standard format string
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Colored formatter for console
        self.formatters['colored'] = ColoredFormatter(format_string)
        
        # Simple formatter
        self.formatters['simple'] = logging.Formatter(format_string)
        
        # Detailed formatter
        self.formatters['detailed'] = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        
        # JSON formatter
        if json_logs:
            self.formatters['json'] = JsonFormatter()
    
    def _create_filters(self, performance_logging: bool, filter_sensitive: bool):
        """Create logging filters."""
        if performance_logging:
            self.filters['performance'] = PerformanceFilter()
        
        if filter_sensitive:
            self.filters['sensitive'] = SensitiveDataFilter()
    
    def _setup_console_handler(self, level: int, format_type: str):
        """Setup console handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Use appropriate formatter
        formatter = self.formatters.get(format_type, self.formatters['simple'])
        console_handler.setFormatter(formatter)
        
        # Add filters
        for filter_obj in self.filters.values():
            console_handler.addFilter(filter_obj)
        
        self.handlers['console'] = console_handler
    
    def _setup_file_handler(self,
                           log_file: Union[str, Path],
                           level: int,
                           json_logs: bool,
                           max_file_size: int,
                           backup_count: int):
        """Setup file handler with rotation."""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Use JSON formatter for files if requested
        if json_logs and 'json' in self.formatters:
            file_handler.setFormatter(self.formatters['json'])
        else:
            file_handler.setFormatter(self.formatters['detailed'])
        
        # Add filters
        for filter_obj in self.filters.values():
            file_handler.addFilter(filter_obj)
        
        self.handlers['file'] = file_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger."""
        # Ensure the name is under the blackholio_client namespace
        if not name.startswith('blackholio_client'):
            if name == '__main__':
                name = 'blackholio_client.main'
            else:
                name = f'blackholio_client.{name}'
        
        return logging.getLogger(name)


# Performance logging helpers
class PerformanceLogger:
    """Context manager for performance logging."""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        """
        Initialize performance logger.
        
        Args:
            logger: Logger to use
            operation: Operation name
            level: Log level
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        """Enter performance logging context."""
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}", extra={'performance_start': True})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit performance logging context."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.log(
                self.level,
                f"Completed {self.operation} in {duration:.3f}s",
                extra={'performance_end': True, 'duration': duration}
            )


class StructuredLogger:
    """
    Structured logger for JSON-like log output.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.
        
        Args:
            logger: Base logger instance
        """
        self.logger = logger
    
    def log(self, level: str, message: str, **kwargs):
        """
        Log a structured message.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        # Create structured log data
        log_data = {
            'message': message,
            'timestamp': time.time(),
            **kwargs
        }
        
        # Format as key=value pairs
        extra_info = ' '.join(f"{k}={v}" for k, v in kwargs.items())
        formatted_message = f"{message} {extra_info}".strip()
        
        # Log with appropriate level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(numeric_level, formatted_message, extra=log_data)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self.log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        self.log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data."""
        self.log('CRITICAL', message, **kwargs)


# Global logging configuration instance
_global_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """Get global logging configuration instance."""
    global _global_logging_config
    if _global_logging_config is None:
        _global_logging_config = LoggingConfig()
    return _global_logging_config


def setup_logging(**kwargs) -> Dict[str, Any]:
    """Convenience function for setting up logging."""
    config = get_logging_config()
    return config.setup_logging(**kwargs)


def get_logger(name: str) -> logging.Logger:
    """Convenience function for getting a configured logger."""
    config = get_logging_config()
    return config.get_logger(name)


def log_performance(operation: str = None, level: int = logging.INFO):
    """
    Decorator for logging function performance.
    
    Args:
        operation: Operation name
        level: Log level
    """
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            name = operation or func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(level, f"Function '{name}' completed in {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Function '{name}' failed after {execution_time:.4f}s: {e}")
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            name = operation or func.__name__
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(level, f"Async function '{name}' completed in {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Async function '{name}' failed after {execution_time:.4f}s: {e}")
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Development helpers
def enable_debug_logging():
    """Enable debug logging for development."""
    setup_logging(
        level=logging.DEBUG,
        format_type="colored",
        performance_logging=True,
        filter_sensitive=False
    )


def enable_production_logging(log_file: Union[str, Path]):
    """Enable production logging with file output."""
    setup_logging(
        level=logging.INFO,
        format_type="simple",
        log_file=log_file,
        json_logs=True,
        performance_logging=False,
        filter_sensitive=True
    )


def configure_third_party_loggers(level: str = "WARNING"):
    """
    Configure third-party library loggers to reduce noise.
    
    Args:
        level: Log level for third-party loggers
    """
    third_party_loggers = [
        'websockets',
        'aiohttp',
        'urllib3',
        'requests',
        'asyncio'
    ]
    
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    
    for logger_name in third_party_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(numeric_level)


# Convenience functions for common logging patterns
def log_connection_event(logger: logging.Logger, 
                        event: str, 
                        server: str,
                        **kwargs):
    """
    Log a connection-related event.
    
    Args:
        logger: Logger instance
        event: Event type (connected, disconnected, error, etc.)
        server: Server identifier
        **kwargs: Additional context
    """
    structured_logger = StructuredLogger(logger)
    structured_logger.info(
        f"Connection {event}",
        event_type="connection",
        event=event,
        server=server,
        **kwargs
    )


def log_game_event(logger: logging.Logger,
                  event: str,
                  player_id: Optional[str] = None,
                  **kwargs):
    """
    Log a game-related event.
    
    Args:
        logger: Logger instance
        event: Event type
        player_id: Optional player identifier
        **kwargs: Additional context
    """
    structured_logger = StructuredLogger(logger)
    structured_logger.info(
        f"Game {event}",
        event_type="game",
        event=event,
        player_id=player_id,
        **kwargs
    )


# Initialize default logger configuration
def init_default_logging():
    """Initialize default logging configuration for the package."""
    try:
        # Try to get configuration from environment
        from ..config.environment import get_environment_config
        config = get_environment_config()
        
        setup_logging(
            level=config.log_level,
            format_type="colored" if config.is_development_mode() else "simple",
            log_file=None  # No file logging by default
        )
        
        # Configure third-party loggers
        configure_third_party_loggers()
        
    except Exception:
        # Fallback to basic configuration
        setup_logging(level="INFO")


# Auto-initialize when module is imported
init_default_logging()