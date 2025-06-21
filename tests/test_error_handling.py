"""
Test Error Handling - Comprehensive Error Handling Tests

Tests for retry logic, circuit breakers, error recovery mechanisms,
debugging utilities, and comprehensive error handling functionality.
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import tempfile

from blackholio_client.utils.error_handling import (
    RetryStrategy,
    CircuitState,
    RetryConfig,
    CircuitBreakerConfig,
    ErrorContext,
    RetryManager,
    CircuitBreaker,
    ErrorRecoveryManager,
    with_retry,
    with_circuit_breaker,
    with_error_recovery,
    handle_errors,
    handle_errors_async,
    get_global_error_manager,
    configure_global_error_handling,
    execute_with_retry,
    execute_with_retry_async
)

from blackholio_client.utils.debugging import (
    DebugContext,
    ErrorReport,
    DebugCapture,
    PerformanceProfiler,
    ErrorReporter,
    DiagnosticCollector,
    debug_context,
    debug_function,
    get_error_reporter,
    get_diagnostic_collector,
    capture_exception,
    generate_diagnostics
)

from blackholio_client.exceptions.connection_errors import (
    BlackholioConnectionError,
    BlackholioTimeoutError,
    ConnectionLostError,
    ServerUnavailableError,
    DataValidationError,
    GameStateError
)


class TestRetryConfig:
    """Test retry configuration."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert ConnectionLostError in config.retryable_exceptions
        assert ServerUnavailableError in config.retryable_exceptions
        assert BlackholioTimeoutError in config.retryable_exceptions
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_multiplier=3.0,
            jitter=False,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            retryable_exceptions=(ConnectionLostError,)
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_multiplier == 3.0
        assert config.jitter is False
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.retryable_exceptions == (ConnectionLostError,)
    
    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfig(max_attempts=0)
        
        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            RetryConfig(base_delay=-1.0)
        
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)


class TestRetryManager:
    """Test retry manager functionality."""
    
    def test_delay_calculation_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False
        )
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 0.0
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 2.0
        assert manager.calculate_delay(3) == 4.0
    
    def test_delay_calculation_linear(self):
        """Test linear backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            jitter=False
        )
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 0.0
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 2.0
        assert manager.calculate_delay(3) == 3.0
    
    def test_delay_calculation_fixed(self):
        """Test fixed delay calculation."""
        config = RetryConfig(
            base_delay=2.0,
            strategy=RetryStrategy.FIXED_DELAY,
            jitter=False
        )
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 0.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 2.0
        assert manager.calculate_delay(3) == 2.0
    
    def test_delay_calculation_fibonacci(self):
        """Test Fibonacci backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            strategy=RetryStrategy.FIBONACCI_BACKOFF,
            jitter=False
        )
        manager = RetryManager(config)
        
        assert manager.calculate_delay(0) == 0.0
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 1.0
        assert manager.calculate_delay(3) == 2.0
        assert manager.calculate_delay(4) == 3.0
        assert manager.calculate_delay(5) == 5.0
    
    def test_delay_calculation_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            base_delay=10.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True
        )
        manager = RetryManager(config)
        
        # With jitter, delays should vary but be within reasonable bounds
        delays = [manager.calculate_delay(1) for _ in range(10)]
        
        # All delays should be different (with high probability)
        assert len(set(delays)) > 1
        
        # All delays should be around the base delay
        for delay in delays:
            assert 9.0 <= delay <= 11.0  # 10% jitter
    
    def test_max_delay_cap(self):
        """Test maximum delay cap."""
        config = RetryConfig(
            base_delay=10.0,
            max_delay=15.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False
        )
        manager = RetryManager(config)
        
        assert manager.calculate_delay(1) == 10.0
        assert manager.calculate_delay(2) == 15.0  # Capped at max_delay
        assert manager.calculate_delay(3) == 15.0  # Still capped
    
    def test_should_retry(self):
        """Test retry decision logic."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ConnectionLostError, ServerUnavailableError)
        )
        manager = RetryManager(config)
        
        # Should retry retryable exceptions within attempt limit
        assert manager.should_retry(ConnectionLostError("test"), 0) is True
        assert manager.should_retry(ServerUnavailableError("test"), 1) is True
        
        # Should not retry non-retryable exceptions
        assert manager.should_retry(ValueError("test"), 0) is False
        assert manager.should_retry(DataValidationError("test"), 0) is False
        
        # Should not retry when attempts exhausted
        assert manager.should_retry(ConnectionLostError("test"), 3) is False
    
    def test_execute_with_retry_success(self):
        """Test successful execution with retry."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = RetryManager(config)
        
        mock_func = Mock(return_value="success")
        result = manager.execute_with_retry(mock_func, "test_operation")
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_execute_with_retry_success_after_failures(self):
        """Test successful execution after initial failures."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = RetryManager(config)
        
        # Fail first two times, succeed on third
        side_effects = [ConnectionLostError("fail1"), ConnectionLostError("fail2"), "success"]
        mock_func = Mock(side_effect=side_effects)
        
        result = manager.execute_with_retry(mock_func, "test_operation")
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_execute_with_retry_permanent_failure(self):
        """Test execution with permanent failure."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = RetryManager(config)
        
        # Non-retryable exception
        mock_func = Mock(side_effect=ValueError("permanent error"))
        
        with pytest.raises(ValueError, match="permanent error"):
            manager.execute_with_retry(mock_func, "test_operation")
        
        assert mock_func.call_count == 1
    
    def test_execute_with_retry_exhausted_attempts(self):
        """Test execution with exhausted retry attempts."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        manager = RetryManager(config)
        
        # Always fail with retryable exception
        mock_func = Mock(side_effect=ConnectionLostError("always fail"))
        
        with pytest.raises(ConnectionLostError, match="always fail"):
            manager.execute_with_retry(mock_func, "test_operation")
        
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_async_success(self):
        """Test successful async execution with retry."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = RetryManager(config)
        
        async def mock_func():
            return "async_success"
        
        result = await manager.execute_with_retry_async(mock_func, "async_test")
        assert result == "async_success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_async_with_failures(self):
        """Test async execution with initial failures."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = RetryManager(config)
        
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionLostError(f"fail_{call_count}")
            return "async_success"
        
        result = await manager.execute_with_retry_async(mock_func, "async_test")
        assert result == "async_success"
        assert call_count == 3


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.can_execute() is True
    
    def test_failure_threshold(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        
        # Record failures
        for i in range(2):
            breaker.record_failure(Exception(f"error_{i}"))
            assert breaker.state == CircuitState.CLOSED
        
        # Third failure should open circuit
        breaker.record_failure(Exception("error_3"))
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False
    
    def test_recovery_timeout(self):
        """Test circuit recovery after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure(Exception("error_1"))
        breaker.record_failure(Exception("error_2"))
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Should transition to half-open
        assert breaker.can_execute() is True
        assert breaker.state == CircuitState.HALF_OPEN
    
    def test_half_open_success(self):
        """Test successful operation in half-open state."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker(config)
        
        # Open circuit
        breaker.record_failure(Exception("error"))
        time.sleep(0.15)
        
        # Should be half-open
        assert breaker.can_execute() is True
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Success should close circuit
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_half_open_failure(self):
        """Test failure in half-open state."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker(config)
        
        # Open circuit
        breaker.record_failure(Exception("error"))
        time.sleep(0.15)
        
        # Should be half-open
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Failure should re-open circuit
        breaker.record_failure(Exception("error_2"))
        assert breaker.state == CircuitState.OPEN
    
    def test_execute_success(self):
        """Test successful execution."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        mock_func = Mock(return_value="success")
        result = breaker.execute(mock_func, "test_operation")
        
        assert result == "success"
        assert mock_func.call_count == 1
        assert breaker.failure_count == 0
    
    def test_execute_failure(self):
        """Test failed execution."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        mock_func = Mock(side_effect=Exception("test_error"))
        
        with pytest.raises(Exception, match="test_error"):
            breaker.execute(mock_func, "test_operation")
        
        assert mock_func.call_count == 1
        assert breaker.failure_count == 1
    
    def test_execute_circuit_open(self):
        """Test execution when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(config)
        
        # Open circuit
        breaker.record_failure(Exception("error"))
        
        mock_func = Mock()
        with pytest.raises(ServerUnavailableError, match="Circuit breaker is OPEN"):
            breaker.execute(mock_func, "test_operation")
        
        # Function should not be called
        assert mock_func.call_count == 0
    
    @pytest.mark.asyncio
    async def test_execute_async_success(self):
        """Test successful async execution."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        async def mock_func():
            return "async_success"
        
        result = await breaker.execute_async(mock_func, "async_test")
        assert result == "async_success"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_execute_async_failure(self):
        """Test failed async execution."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        async def mock_func():
            raise Exception("async_error")
        
        with pytest.raises(Exception, match="async_error"):
            await breaker.execute_async(mock_func, "async_test")
        
        assert breaker.failure_count == 1
    
    def test_get_state(self):
        """Test state reporting."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)
        breaker = CircuitBreaker(config)
        
        state = breaker.get_state()
        
        assert state['state'] == 'closed'
        assert state['failure_count'] == 0
        assert state['config']['failure_threshold'] == 3
        assert state['config']['recovery_timeout'] == 60.0


class TestErrorRecoveryManager:
    """Test comprehensive error recovery manager."""
    
    def test_initialization(self):
        """Test error recovery manager initialization."""
        retry_config = RetryConfig(max_attempts=5)
        circuit_config = CircuitBreakerConfig(failure_threshold=3)
        
        manager = ErrorRecoveryManager(retry_config, circuit_config)
        
        assert manager.retry_config.max_attempts == 5
        assert manager.circuit_config.failure_threshold == 3
    
    def test_register_recovery_strategy(self):
        """Test registering custom recovery strategies."""
        manager = ErrorRecoveryManager()
        
        def custom_strategy(error, func, operation):
            return "recovered"
        
        manager.register_recovery_strategy("custom", custom_strategy)
        
        assert "custom" in manager._recovery_strategies
        assert manager._recovery_strategies["custom"] == custom_strategy
    
    def test_register_error_handler(self):
        """Test registering custom error handlers."""
        manager = ErrorRecoveryManager()
        
        def custom_handler(error, func, operation):
            return "handled"
        
        manager.register_error_handler(ValueError, custom_handler)
        
        assert ValueError in manager._error_handlers
        assert manager._error_handlers[ValueError] == custom_handler
    
    def test_execute_with_recovery_success(self):
        """Test successful execution with recovery."""
        manager = ErrorRecoveryManager()
        
        mock_func = Mock(return_value="success")
        result = manager.execute_with_recovery(mock_func, "test_operation")
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_execute_with_recovery_with_retry(self):
        """Test execution with recovery using retry logic."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        manager = ErrorRecoveryManager(retry_config=config)
        
        # Fail twice, succeed third time
        side_effects = [ConnectionLostError("fail1"), ConnectionLostError("fail2"), "success"]
        mock_func = Mock(side_effect=side_effects)
        
        result = manager.execute_with_recovery(mock_func, "test_operation")
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_execute_with_custom_error_handler(self):
        """Test execution with custom error handler."""
        manager = ErrorRecoveryManager()
        
        def error_handler(error, func, operation):
            return "handled_error"
        
        manager.register_error_handler(ValueError, error_handler)
        
        mock_func = Mock(side_effect=ValueError("test_error"))
        result = manager.execute_with_recovery(mock_func, "test_operation")
        
        assert result == "handled_error"
    
    def test_execute_with_recovery_strategy(self):
        """Test execution with custom recovery strategy."""
        manager = ErrorRecoveryManager()
        
        def recovery_strategy(error, func, operation):
            return "recovered"
        
        manager.register_recovery_strategy("test_strategy", recovery_strategy)
        
        mock_func = Mock(side_effect=ValueError("test_error"))
        result = manager.execute_with_recovery(
            mock_func, 
            "test_operation", 
            recovery_strategy="test_strategy"
        )
        
        assert result == "recovered"
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_async(self):
        """Test async execution with recovery."""
        manager = ErrorRecoveryManager()
        
        async def mock_func():
            return "async_success"
        
        result = await manager.execute_with_recovery_async(mock_func, "async_test")
        assert result == "async_success"
    
    def test_get_status(self):
        """Test status reporting."""
        retry_config = RetryConfig(max_attempts=5, strategy=RetryStrategy.LINEAR_BACKOFF)
        circuit_config = CircuitBreakerConfig(failure_threshold=3)
        manager = ErrorRecoveryManager(retry_config, circuit_config)
        
        # Register some handlers
        manager.register_recovery_strategy("test_strategy", lambda: None)
        manager.register_error_handler(ValueError, lambda: None)
        
        status = manager.get_status()
        
        assert status['retry_config']['max_attempts'] == 5
        assert status['retry_config']['strategy'] == 'linear_backoff'
        assert status['circuit_breaker']['config']['failure_threshold'] == 3
        assert 'test_strategy' in status['registered_strategies']
        assert 'ValueError' in status['registered_handlers']


class TestDecorators:
    """Test error handling decorators."""
    
    def test_with_retry_decorator(self):
        """Test retry decorator."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        
        call_count = 0
        
        @with_retry(config, "decorated_function")
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionLostError(f"fail_{call_count}")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator_async(self):
        """Test async retry decorator."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        
        call_count = 0
        
        @with_retry(config, "async_decorated_function")
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionLostError(f"fail_{call_count}")
            return "async_success"
        
        result = await test_func()
        assert result == "async_success"
        assert call_count == 3
    
    def test_with_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        @with_circuit_breaker(config, "decorated_function")
        def test_func(should_fail=False):
            if should_fail:
                raise Exception("test_error")
            return "success"
        
        # Should succeed normally
        assert test_func() == "success"
        
        # Fail to open circuit
        with pytest.raises(Exception):
            test_func(should_fail=True)
        with pytest.raises(Exception):
            test_func(should_fail=True)
        
        # Circuit should now be open
        with pytest.raises(ServerUnavailableError):
            test_func()
    
    def test_with_error_recovery_decorator(self):
        """Test comprehensive error recovery decorator."""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)
        
        call_count = 0
        
        @with_error_recovery(retry_config, operation_name="comprehensive_test")
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionLostError(f"fail_{call_count}")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 3


class TestContextManagers:
    """Test error handling context managers."""
    
    def test_handle_errors_success(self):
        """Test error handling context manager with success."""
        with handle_errors("test_operation", log_errors=False):
            result = "success"
        
        assert result == "success"
    
    def test_handle_errors_with_exception(self):
        """Test error handling context manager with exception."""
        with pytest.raises(ValueError):
            with handle_errors("test_operation", log_errors=False, raise_on_error=True):
                raise ValueError("test_error")
    
    def test_handle_errors_suppress_exception(self):
        """Test error handling context manager suppressing exceptions."""
        with handle_errors("test_operation", log_errors=False, raise_on_error=False):
            raise ValueError("test_error")
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_handle_errors_async_success(self):
        """Test async error handling context manager with success."""
        async with handle_errors_async("async_test_operation", log_errors=False):
            result = "async_success"
        
        assert result == "async_success"
    
    @pytest.mark.asyncio
    async def test_handle_errors_async_with_exception(self):
        """Test async error handling context manager with exception."""
        with pytest.raises(ValueError):
            async with handle_errors_async("async_test_operation", log_errors=False, raise_on_error=True):
                raise ValueError("async_test_error")


class TestGlobalErrorManager:
    """Test global error manager functionality."""
    
    def test_get_global_error_manager(self):
        """Test getting global error manager."""
        manager1 = get_global_error_manager()
        manager2 = get_global_error_manager()
        
        # Should return same instance
        assert manager1 is manager2
    
    def test_configure_global_error_handling(self):
        """Test configuring global error handling."""
        retry_config = RetryConfig(max_attempts=5)
        circuit_config = CircuitBreakerConfig(failure_threshold=3)
        
        configure_global_error_handling(retry_config, circuit_config)
        
        manager = get_global_error_manager()
        assert manager.retry_config.max_attempts == 5
        assert manager.circuit_config.failure_threshold == 3
    
    def test_execute_with_retry_global(self):
        """Test global retry execution."""
        mock_func = Mock(return_value="global_success")
        result = execute_with_retry(mock_func, "global_test")
        
        assert result == "global_success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_async_global(self):
        """Test global async retry execution."""
        async def mock_func():
            return "global_async_success"
        
        result = await execute_with_retry_async(mock_func, "global_async_test")
        assert result == "global_async_success"


class TestDebugCapture:
    """Test debug capture functionality."""
    
    def test_debug_capture_basic(self):
        """Test basic debug capture."""
        with DebugCapture() as capture:
            local_var = "test_value"
            pass
        
        context = capture.get_context()
        
        assert context is not None
        assert context.function == "test_debug_capture_basic"
        assert context.module == "test_error_handling"
        assert "local_var" in context.locals_snapshot
        assert context.locals_snapshot["local_var"] == "test_value"
    
    def test_debug_capture_with_exception(self):
        """Test debug capture with exception."""
        with DebugCapture() as capture:
            try:
                raise ValueError("test_exception")
            except ValueError:
                pass
        
        context = capture.get_context()
        
        assert context is not None
        assert context.extra_data.get("exception_type") == "ValueError"
        assert context.extra_data.get("exception_message") == "test_exception"
    
    def test_debug_capture_without_locals(self):
        """Test debug capture without capturing locals."""
        with DebugCapture(capture_locals=False) as capture:
            local_var = "should_not_be_captured"
            pass
        
        context = capture.get_context()
        
        assert context is not None
        assert len(context.locals_snapshot) == 0
    
    def test_debug_capture_without_stack(self):
        """Test debug capture without capturing call stack."""
        with DebugCapture(capture_stack=False) as capture:
            pass
        
        context = capture.get_context()
        
        assert context is not None
        assert len(context.call_stack) == 0


class TestPerformanceProfiler:
    """Test performance profiler functionality."""
    
    def test_performance_profiler_basic(self):
        """Test basic performance profiling."""
        profiler = PerformanceProfiler("test_profiler")
        
        profiler.start()
        time.sleep(0.1)
        profiler.checkpoint("checkpoint_1")
        time.sleep(0.1)
        metrics = profiler.stop()
        
        assert metrics['profiler_name'] == "test_profiler"
        assert metrics['total_time'] >= 0.2
        assert metrics['checkpoint_count'] == 1
        assert len(metrics['checkpoints']) == 1
        assert metrics['checkpoints'][0]['name'] == "checkpoint_1"
    
    def test_performance_profiler_context_manager(self):
        """Test performance profiler as context manager."""
        with PerformanceProfiler("context_test") as profiler:
            time.sleep(0.05)
            profiler.checkpoint("mid_point")
            time.sleep(0.05)
        
        # Profiler should automatically stop
        assert profiler.end_time is not None
    
    def test_performance_profiler_multiple_checkpoints(self):
        """Test multiple checkpoints."""
        profiler = PerformanceProfiler("multi_checkpoint_test")
        
        profiler.start()
        
        for i in range(3):
            time.sleep(0.01)
            profiler.checkpoint(f"checkpoint_{i}", data=f"data_{i}")
        
        metrics = profiler.stop()
        
        assert metrics['checkpoint_count'] == 3
        assert len(metrics['checkpoints']) == 3
        
        # Check delta times
        for i, checkpoint in enumerate(metrics['checkpoints']):
            if i > 0:
                assert checkpoint['delta_time'] > 0
            assert checkpoint['data'] == f"data_{i}"


class TestErrorReporter:
    """Test error reporter functionality."""
    
    def test_error_reporter_initialization(self):
        """Test error reporter initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ErrorReporter(
                report_directory=temp_dir,
                auto_save=True,
                max_reports=50
            )
            
            assert reporter.report_directory == Path(temp_dir)
            assert reporter.auto_save is True
            assert reporter.max_reports == 50
    
    def test_generate_error_id(self):
        """Test error ID generation."""
        reporter = ErrorReporter(auto_save=False)
        
        error_id_1 = reporter.generate_error_id()
        time.sleep(0.01)
        error_id_2 = reporter.generate_error_id()
        
        assert error_id_1 != error_id_2
        assert error_id_1.startswith("error_")
        assert error_id_2.startswith("error_")
    
    def test_create_error_report(self):
        """Test creating error report."""
        reporter = ErrorReporter(auto_save=False)
        
        try:
            raise ValueError("test_error")
        except ValueError as e:
            report = reporter.create_error_report(e)
        
        assert report.error_type == "ValueError"
        assert report.error_message == "test_error"
        assert report.error_category == "unknown"
        assert len(report.traceback_lines) > 0
        assert report.context is not None
        assert "python_version" in report.system_info
    
    def test_error_report_with_debug_context(self):
        """Test error report with debug context."""
        reporter = ErrorReporter(auto_save=False)
        
        with DebugCapture() as capture:
            test_var = "context_test"
            try:
                raise ValueError("test_with_context")
            except ValueError as e:
                context = capture.get_context()
                report = reporter.create_error_report(e, context)
        
        assert "test_var" in report.context.locals_snapshot
        assert report.context.locals_snapshot["test_var"] == "context_test"
    
    def test_error_report_auto_save(self):
        """Test automatic error report saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ErrorReporter(
                report_directory=temp_dir,
                auto_save=True
            )
            
            try:
                raise ValueError("auto_save_test")
            except ValueError as e:
                report = reporter.create_error_report(e)
            
            # Check if file was saved
            expected_file = Path(temp_dir) / f"{report.error_id}.json"
            assert expected_file.exists()
            
            # Verify file content
            with open(expected_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['error_type'] == "ValueError"
            assert saved_data['error_message'] == "auto_save_test"
    
    def test_get_reports_filtering(self):
        """Test report filtering."""
        reporter = ErrorReporter(auto_save=False)
        
        # Create multiple reports
        try:
            raise ValueError("value_error")
        except ValueError as e:
            report1 = reporter.create_error_report(e)
        
        try:
            raise TypeError("type_error")
        except TypeError as e:
            report2 = reporter.create_error_report(e)
        
        # Test filtering by error type
        value_errors = reporter.get_reports(error_type="ValueError")
        assert len(value_errors) == 1
        assert value_errors[0].error_id == report1.error_id
        
        type_errors = reporter.get_reports(error_type="TypeError")
        assert len(type_errors) == 1
        assert type_errors[0].error_id == report2.error_id
        
        # Test limit
        limited = reporter.get_reports(limit=1)
        assert len(limited) == 1
    
    def test_export_reports_json(self):
        """Test exporting reports to JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ErrorReporter(auto_save=False)
            
            # Create a report
            try:
                raise ValueError("export_test")
            except ValueError as e:
                reporter.create_error_report(e)
            
            # Export to JSON
            export_path = Path(temp_dir) / "exported_reports.json"
            result_path = reporter.export_reports(export_path, format='json')
            
            assert result_path == export_path
            assert export_path.exists()
            
            # Verify exported content
            with open(export_path, 'r') as f:
                exported_data = json.load(f)
            
            assert len(exported_data) == 1
            assert exported_data[0]['error_type'] == "ValueError"


class TestDiagnosticCollector:
    """Test diagnostic collector functionality."""
    
    def test_collect_package_info(self):
        """Test collecting package information."""
        collector = DiagnosticCollector()
        info = collector.collect_package_info()
        
        assert 'package_version' in info
        assert 'package_path' in info
        assert 'python_path' in info
    
    def test_collect_dependency_info(self):
        """Test collecting dependency information."""
        collector = DiagnosticCollector()
        info = collector.collect_dependency_info()
        
        # Should check for some common dependencies
        assert isinstance(info, dict)
        # At least check that it doesn't crash
    
    def test_run_connectivity_tests(self):
        """Test connectivity tests."""
        collector = DiagnosticCollector()
        tests = collector.run_connectivity_tests()
        
        assert 'internet_connectivity' in tests
        assert 'dns_resolution' in tests
        # Results will vary based on network, just check structure
    
    def test_generate_diagnostic_report(self):
        """Test generating comprehensive diagnostic report."""
        collector = DiagnosticCollector()
        report = collector.generate_diagnostic_report()
        
        assert 'timestamp' in report
        assert 'report_version' in report
        assert 'system_info' in report
        assert 'environment_info' in report
        assert 'package_info' in report
        assert 'dependency_info' in report
        assert 'connectivity_tests' in report
    
    def test_save_diagnostic_report(self):
        """Test saving diagnostic report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = DiagnosticCollector()
            
            report_path = Path(temp_dir) / "diagnostic_report.json"
            result_path = collector.save_diagnostic_report(report_path)
            
            assert result_path == report_path
            assert report_path.exists()
            
            # Verify saved content
            with open(report_path, 'r') as f:
                saved_data = json.load(f)
            
            assert 'timestamp' in saved_data
            assert 'system_info' in saved_data


class TestDebugDecorators:
    """Test debugging decorators and context managers."""
    
    def test_debug_context_success(self):
        """Test debug context with successful operation."""
        with debug_context("test_context", log_entry_exit=False):
            result = "success"
        
        assert result == "success"
    
    def test_debug_context_with_exception(self):
        """Test debug context with exception."""
        with pytest.raises(ValueError):
            with debug_context("test_context", log_entry_exit=False):
                raise ValueError("test_error")
    
    def test_debug_function_decorator(self):
        """Test function debugging decorator."""
        @debug_function(log_performance=False)
        def test_func(x, y):
            return x + y
        
        result = test_func(2, 3)
        assert result == 5
    
    def test_debug_function_decorator_with_exception(self):
        """Test function debugging decorator with exception."""
        @debug_function(log_performance=False)
        def test_func():
            raise ValueError("decorated_error")
        
        with pytest.raises(ValueError, match="decorated_error"):
            test_func()


class TestGlobalUtilities:
    """Test global utility functions."""
    
    def test_capture_exception(self):
        """Test capturing exception with global reporter."""
        try:
            raise ValueError("global_capture_test")
        except ValueError as e:
            report = capture_exception(e)
        
        assert report.error_type == "ValueError"
        assert report.error_message == "global_capture_test"
    
    def test_generate_diagnostics_dict(self):
        """Test generating diagnostics as dictionary."""
        diagnostics = generate_diagnostics(save_to_file=False)
        
        assert isinstance(diagnostics, dict)
        assert 'timestamp' in diagnostics
        assert 'system_info' in diagnostics
    
    def test_generate_diagnostics_file(self):
        """Test generating diagnostics and saving to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change working directory for test
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                file_path = generate_diagnostics(save_to_file=True)
                
                assert isinstance(file_path, Path)
                assert file_path.exists()
                assert file_path.name.startswith("blackholio_diagnostics_")
                assert file_path.suffix == ".json"
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    pytest.main([__file__])