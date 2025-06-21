"""
Error Handling Utilities - Comprehensive Error Recovery and Retry Logic

Provides robust error handling utilities including retry mechanisms,
circuit breakers, error recovery strategies, and graceful failure handling
for production-ready blackholio client operations.
"""

import asyncio
import functools
import logging
import random
import secrets
import time
from typing import (
    Any, Callable, Dict, List, Optional, Type, Union, 
    Tuple, Set, Awaitable, TypeVar, Generic
)
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import contextmanager, asynccontextmanager

from ..exceptions.connection_errors import (
    BlackholioConnectionError, 
    BlackholioTimeoutError,
    ConnectionLostError,
    ServerUnavailableError,
    BlackholioConfigurationError,
    is_retryable_error,
    get_error_category
)
from .logging_config import get_logger

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class RetryStrategy(Enum):
    """Retry strategy enumeration."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    JITTERED_EXPONENTIAL = "jittered_exponential"


class CircuitState(Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionLostError,
        ServerUnavailableError,
        BlackholioTimeoutError
    )
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: Type[Exception] = Exception
    
    def __post_init__(self):
        """Validate configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout must be non-negative")


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    attempt: int
    max_attempts: int
    error: Exception
    duration: float
    timestamp: float
    extra_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'operation': self.operation,
            'attempt': self.attempt,
            'max_attempts': self.max_attempts,
            'error_type': type(self.error).__name__,
            'error_message': str(self.error),
            'duration': self.duration,
            'timestamp': self.timestamp,
            'error_category': get_error_category(self.error),
            **self.extra_data
        }


class RetryManager:
    """
    Manages retry logic with various backoff strategies.
    
    Provides configurable retry behavior with support for different
    backoff strategies, jitter, and custom retry conditions.
    """
    
    def __init__(self, config: RetryConfig):
        """
        Initialize retry manager.
        
        Args:
            config: Retry configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self._fibonacci_cache = [1, 1]  # Cache for Fibonacci sequence
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        if attempt == 0:
            return 0.0
        
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._get_fibonacci(attempt)
        elif self.config.strategy == RetryStrategy.JITTERED_EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
            # Add jitter regardless of strategy setting
            delay = delay * (0.5 + secrets.SystemRandom().random() * 0.5)
        else:
            delay = self.config.base_delay
        
        # Apply jitter if enabled (except for jittered exponential which already has it)
        if self.config.jitter and self.config.strategy != RetryStrategy.JITTERED_EXPONENTIAL:
            jitter_factor = 0.1  # 10% jitter
            delay = delay * (1 + secrets.SystemRandom().uniform(-jitter_factor, jitter_factor))
        
        # Cap at max delay
        return min(delay, self.config.max_delay)
    
    def _get_fibonacci(self, n: int) -> int:
        """Get nth Fibonacci number with caching."""
        while len(self._fibonacci_cache) <= n:
            self._fibonacci_cache.append(
                self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            )
        return self._fibonacci_cache[n]
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            True if should retry
        """
        if attempt >= self.config.max_attempts:
            return False
        
        # Check if exception is retryable
        if not isinstance(exception, self.config.retryable_exceptions):
            return False
        
        # Use built-in retryable check
        return is_retryable_error(exception)
    
    def execute_with_retry(self, func: Callable[[], T], operation_name: str = "operation") -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            operation_name: Name of operation for logging
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            start_time = time.time()
            
            try:
                result = func()
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation '{operation_name}' succeeded on attempt {attempt + 1}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                duration = time.time() - start_time
                
                # Create error context
                context = ErrorContext(
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    error=e,
                    duration=duration,
                    timestamp=time.time(),
                    extra_data={}
                )
                
                # Check if should retry
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Operation '{operation_name}' failed permanently on attempt {attempt + 1}: {e}",
                        extra=context.to_dict()
                    )
                    raise e
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
                
                self.logger.warning(
                    f"Operation '{operation_name}' failed on attempt {attempt + 1}, "
                    f"retrying in {delay:.2f}s: {e}",
                    extra=context.to_dict()
                )
                
                # Wait before retry
                if delay > 0:
                    time.sleep(delay)
        
        # All retries exhausted
        self.logger.error(
            f"Operation '{operation_name}' failed after {self.config.max_attempts} attempts"
        )
        raise last_exception
    
    async def execute_with_retry_async(self, 
                                     func: Callable[[], Awaitable[T]], 
                                     operation_name: str = "async_operation") -> T:
        """
        Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            operation_name: Name of operation for logging
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            start_time = time.time()
            
            try:
                result = await func()
                
                if attempt > 0:
                    self.logger.info(
                        f"Async operation '{operation_name}' succeeded on attempt {attempt + 1}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                duration = time.time() - start_time
                
                # Create error context
                context = ErrorContext(
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    error=e,
                    duration=duration,
                    timestamp=time.time(),
                    extra_data={}
                )
                
                # Check if should retry
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Async operation '{operation_name}' failed permanently on attempt {attempt + 1}: {e}",
                        extra=context.to_dict()
                    )
                    raise e
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
                
                self.logger.warning(
                    f"Async operation '{operation_name}' failed on attempt {attempt + 1}, "
                    f"retrying in {delay:.2f}s: {e}",
                    extra=context.to_dict()
                )
                
                # Wait before retry
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        self.logger.error(
            f"Async operation '{operation_name}' failed after {self.config.max_attempts} attempts"
        )
        raise last_exception


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Provides protection against cascading failures by monitoring
    error rates and temporarily stopping calls to failing services.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.logger = get_logger(__name__)
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """
        Check if operation can be executed.
        
        Returns:
            True if operation can proceed
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True
            
            return False
    
    def record_success(self):
        """Record successful operation."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.logger.info("Circuit breaker reset to CLOSED state after successful operation")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def record_failure(self, exception: Exception):
        """
        Record failed operation.
        
        Args:
            exception: Exception that occurred
        """
        with self._lock:
            if isinstance(exception, self.config.expected_exception):
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.config.failure_threshold:
                    if self.state != CircuitState.OPEN:
                        self.state = CircuitState.OPEN
                        self.logger.warning(
                            f"Circuit breaker opened after {self.failure_count} failures"
                        )
                elif self.state == CircuitState.HALF_OPEN:
                    # Failure in half-open state means we're not recovered
                    self.state = CircuitState.OPEN
                    self.logger.warning("Circuit breaker returned to OPEN state after failure in HALF_OPEN")
    
    def execute(self, func: Callable[[], T], operation_name: str = "operation") -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            operation_name: Name of operation for logging
            
        Returns:
            Function result
            
        Raises:
            Exception if circuit is open or function fails
        """
        if not self.can_execute():
            raise ServerUnavailableError(
                f"Circuit breaker is OPEN for operation '{operation_name}'",
                error_code="CIRCUIT_OPEN"
            )
        
        try:
            result = func()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise
    
    async def execute_async(self, 
                          func: Callable[[], Awaitable[T]], 
                          operation_name: str = "async_operation") -> T:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            operation_name: Name of operation for logging
            
        Returns:
            Function result
            
        Raises:
            Exception if circuit is open or function fails
        """
        if not self.can_execute():
            raise ServerUnavailableError(
                f"Circuit breaker is OPEN for async operation '{operation_name}'",
                error_code="CIRCUIT_OPEN"
            )
        
        try:
            result = await func()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        with self._lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'last_failure_time': self.last_failure_time,
                'time_since_last_failure': time.time() - self.last_failure_time,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'recovery_timeout': self.config.recovery_timeout
                }
            }


class ErrorRecoveryManager:
    """
    Comprehensive error recovery manager.
    
    Combines retry logic, circuit breaker, and custom recovery strategies
    for robust error handling in production environments.
    """
    
    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 circuit_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize error recovery manager.
        
        Args:
            retry_config: Retry configuration
            circuit_config: Circuit breaker configuration
        """
        self.retry_config = retry_config or RetryConfig()
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        
        self.retry_manager = RetryManager(self.retry_config)
        self.circuit_breaker = CircuitBreaker(self.circuit_config)
        
        self.logger = get_logger(__name__)
        self._recovery_strategies: Dict[str, Callable] = {}
        self._error_handlers: Dict[Type[Exception], Callable] = {}
    
    def register_recovery_strategy(self, name: str, strategy: Callable):
        """
        Register a custom recovery strategy.
        
        Args:
            name: Strategy name
            strategy: Recovery function
        """
        self._recovery_strategies[name] = strategy
        self.logger.debug(f"Registered recovery strategy: {name}")
    
    def register_error_handler(self, exception_type: Type[Exception], handler: Callable):
        """
        Register custom error handler.
        
        Args:
            exception_type: Exception type to handle
            handler: Handler function
        """
        self._error_handlers[exception_type] = handler
        self.logger.debug(f"Registered error handler for: {exception_type.__name__}")
    
    def execute_with_recovery(self, 
                            func: Callable[[], T], 
                            operation_name: str = "operation",
                            recovery_strategy: Optional[str] = None) -> T:
        """
        Execute function with comprehensive error recovery.
        
        Args:
            func: Function to execute
            operation_name: Name of operation for logging
            recovery_strategy: Optional recovery strategy name
            
        Returns:
            Function result
        """
        def protected_func():
            return self.circuit_breaker.execute(func, operation_name)
        
        try:
            return self.retry_manager.execute_with_retry(protected_func, operation_name)
        except Exception as e:
            # Try custom error handler
            handler = self._error_handlers.get(type(e))
            if handler:
                try:
                    return handler(e, func, operation_name)
                except Exception as handler_error:
                    self.logger.error(f"Error handler failed: {handler_error}")
            
            # Try recovery strategy
            if recovery_strategy and recovery_strategy in self._recovery_strategies:
                try:
                    strategy = self._recovery_strategies[recovery_strategy]
                    return strategy(e, func, operation_name)
                except Exception as strategy_error:
                    self.logger.error(f"Recovery strategy '{recovery_strategy}' failed: {strategy_error}")
            
            # Final failure
            raise
    
    async def execute_with_recovery_async(self, 
                                        func: Callable[[], Awaitable[T]], 
                                        operation_name: str = "async_operation",
                                        recovery_strategy: Optional[str] = None) -> T:
        """
        Execute async function with comprehensive error recovery.
        
        Args:
            func: Async function to execute
            operation_name: Name of operation for logging
            recovery_strategy: Optional recovery strategy name
            
        Returns:
            Function result
        """
        async def protected_func():
            return await self.circuit_breaker.execute_async(func, operation_name)
        
        try:
            return await self.retry_manager.execute_with_retry_async(protected_func, operation_name)
        except Exception as e:
            # Try custom error handler
            handler = self._error_handlers.get(type(e))
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(e, func, operation_name)
                    else:
                        return handler(e, func, operation_name)
                except Exception as handler_error:
                    self.logger.error(f"Error handler failed: {handler_error}")
            
            # Try recovery strategy
            if recovery_strategy and recovery_strategy in self._recovery_strategies:
                try:
                    strategy = self._recovery_strategies[recovery_strategy]
                    if asyncio.iscoroutinefunction(strategy):
                        return await strategy(e, func, operation_name)
                    else:
                        return strategy(e, func, operation_name)
                except Exception as strategy_error:
                    self.logger.error(f"Recovery strategy '{recovery_strategy}' failed: {strategy_error}")
            
            # Final failure
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current recovery manager status."""
        return {
            'retry_config': {
                'max_attempts': self.retry_config.max_attempts,
                'base_delay': self.retry_config.base_delay,
                'max_delay': self.retry_config.max_delay,
                'strategy': self.retry_config.strategy.value
            },
            'circuit_breaker': self.circuit_breaker.get_state(),
            'registered_strategies': list(self._recovery_strategies.keys()),
            'registered_handlers': [exc.__name__ for exc in self._error_handlers.keys()]
        }


# Decorators for easy error handling
def with_retry(config: Optional[RetryConfig] = None, operation_name: Optional[str] = None):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        config: Retry configuration
        operation_name: Optional operation name for logging
    """
    def decorator(func: F) -> F:
        retry_manager = RetryManager(config or RetryConfig())
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return retry_manager.execute_with_retry(
                lambda: func(*args, **kwargs), 
                name
            )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await retry_manager.execute_with_retry_async(
                lambda: func(*args, **kwargs), 
                name
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_circuit_breaker(config: Optional[CircuitBreakerConfig] = None, 
                        operation_name: Optional[str] = None):
    """
    Decorator for adding circuit breaker protection to functions.
    
    Args:
        config: Circuit breaker configuration
        operation_name: Optional operation name for logging
    """
    def decorator(func: F) -> F:
        circuit_breaker = CircuitBreaker(config or CircuitBreakerConfig())
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return circuit_breaker.execute(
                lambda: func(*args, **kwargs), 
                name
            )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await circuit_breaker.execute_async(
                lambda: func(*args, **kwargs), 
                name
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_error_recovery(retry_config: Optional[RetryConfig] = None,
                       circuit_config: Optional[CircuitBreakerConfig] = None,
                       operation_name: Optional[str] = None,
                       recovery_strategy: Optional[str] = None):
    """
    Decorator for comprehensive error recovery.
    
    Args:
        retry_config: Retry configuration
        circuit_config: Circuit breaker configuration
        operation_name: Optional operation name for logging
        recovery_strategy: Optional recovery strategy name
    """
    def decorator(func: F) -> F:
        manager = ErrorRecoveryManager(retry_config, circuit_config)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return manager.execute_with_recovery(
                lambda: func(*args, **kwargs), 
                name, 
                recovery_strategy
            )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await manager.execute_with_recovery_async(
                lambda: func(*args, **kwargs), 
                name, 
                recovery_strategy
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Context managers for error handling
@contextmanager
def handle_errors(operation_name: str = "operation", 
                 log_errors: bool = True,
                 raise_on_error: bool = True):
    """
    Context manager for error handling.
    
    Args:
        operation_name: Name of operation for logging
        log_errors: Whether to log errors
        raise_on_error: Whether to re-raise exceptions
    """
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        
        if log_errors:
            logger.error(
                f"Error in operation '{operation_name}' after {duration:.3f}s: {e}",
                exc_info=True,
                extra={
                    'operation': operation_name,
                    'duration': duration,
                    'error_type': type(e).__name__,
                    'error_category': get_error_category(e)
                }
            )
        
        if raise_on_error:
            raise


@asynccontextmanager
async def handle_errors_async(operation_name: str = "async_operation",
                             log_errors: bool = True,
                             raise_on_error: bool = True):
    """
    Async context manager for error handling.
    
    Args:
        operation_name: Name of operation for logging
        log_errors: Whether to log errors
        raise_on_error: Whether to re-raise exceptions
    """
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        
        if log_errors:
            logger.error(
                f"Error in async operation '{operation_name}' after {duration:.3f}s: {e}",
                exc_info=True,
                extra={
                    'operation': operation_name,
                    'duration': duration,
                    'error_type': type(e).__name__,
                    'error_category': get_error_category(e)
                }
            )
        
        if raise_on_error:
            raise


# Global error recovery manager instance
_global_error_manager: Optional[ErrorRecoveryManager] = None


def get_global_error_manager() -> ErrorRecoveryManager:
    """Get or create global error recovery manager."""
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorRecoveryManager()
    return _global_error_manager


def configure_global_error_handling(retry_config: Optional[RetryConfig] = None,
                                  circuit_config: Optional[CircuitBreakerConfig] = None):
    """
    Configure global error handling.
    
    Args:
        retry_config: Global retry configuration
        circuit_config: Global circuit breaker configuration
    """
    global _global_error_manager
    _global_error_manager = ErrorRecoveryManager(retry_config, circuit_config)


# Convenience functions using global manager
def execute_with_retry(func: Callable[[], T], operation_name: str = "operation") -> T:
    """Execute function with global retry manager."""
    manager = get_global_error_manager()
    return manager.execute_with_recovery(func, operation_name)


async def execute_with_retry_async(func: Callable[[], Awaitable[T]], 
                                  operation_name: str = "async_operation") -> T:
    """Execute async function with global retry manager."""
    manager = get_global_error_manager()
    return await manager.execute_with_recovery_async(func, operation_name)