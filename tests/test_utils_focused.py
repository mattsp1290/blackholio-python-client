"""
Focused test suite for blackholio_client.utils modules.

Tests the actual available utilities based on the __init__.py imports.
"""

import pytest
import asyncio
import logging
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

# Import available utils modules
from blackholio_client.utils import (
    # Async helpers
    TaskManager, timeout_context, run_with_timeout, gather_with_limit,
    run_in_executor, get_global_task_manager, shutdown_global_task_manager,
    
    # Data converters
    DataConverter, JsonConverter, MessageConverter,
    convert_to_json, convert_from_json, validate_data,
    
    # Debugging
    DebugCapture, PerformanceProfiler, ErrorReporter, DiagnosticCollector,
    debug_context, get_error_reporter, get_diagnostic_collector,
    
    # Error handling
    RetryManager, CircuitBreaker, ErrorRecoveryManager,
    with_retry, with_circuit_breaker, with_error_recovery,
    
    # Logging
    setup_logging, get_logger, StructuredLogger, LoggingConfig
)

from blackholio_client.models import Vector2, GameEntity, GamePlayer, GameCircle


class TestAsyncHelpers:
    """Test async helper utilities."""
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test run_with_timeout with successful operation."""
        async def quick_operation():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await run_with_timeout(quick_operation(), timeout=1.0)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_failure(self):
        """Test run_with_timeout with timeout exceeded."""
        async def slow_operation():
            await asyncio.sleep(2.0)
            return "too_slow"
        
        with pytest.raises(asyncio.TimeoutError):
            await run_with_timeout(slow_operation(), timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_gather_with_limit(self):
        """Test gather_with_limit function."""
        async def task(n):
            await asyncio.sleep(0.01)
            return f"task_{n}"
        
        tasks = [task(i) for i in range(5)]
        results = await gather_with_limit(tasks, limit=3)
        assert len(results) == 5
        assert all(f"task_{i}" in results for i in range(5))
    
    @pytest.mark.asyncio
    async def test_run_in_executor(self):
        """Test run_in_executor function."""
        def blocking_operation(value):
            time.sleep(0.01)
            return value * 2
        
        result = await run_in_executor(blocking_operation, 5)
        assert result == 10
    
    def test_task_manager(self):
        """Test TaskManager."""
        manager = TaskManager()
        assert manager is not None
        
        # Test basic functionality
        assert hasattr(manager, 'create_task')
    
    def test_global_task_manager(self):
        """Test global task manager functions."""
        manager = get_global_task_manager()
        assert manager is not None
        
        # Test shutdown (should not raise)
        shutdown_global_task_manager()
    
    def test_timeout_context(self):
        """Test timeout_context."""
        context = timeout_context(1.0)
        assert context is not None


class TestDataConverters:
    """Test data converter utilities."""
    
    def test_convert_to_json(self):
        """Test convert_to_json function."""
        data = {"test": "value", "number": 42}
        json_str = convert_to_json(data)
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["test"] == "value"
        assert parsed["number"] == 42
    
    def test_convert_from_json(self):
        """Test convert_from_json function."""
        json_str = '{"test": "value", "number": 42}'
        data = convert_from_json(json_str)
        
        assert isinstance(data, dict)
        assert data["test"] == "value"
        assert data["number"] == 42
    
    def test_validate_data(self):
        """Test validate_data function."""
        valid_data = {"required_field": "value"}
        
        # Should not raise for basic validation
        result = validate_data(valid_data)
        assert result is not None
    
    def test_data_converter(self):
        """Test DataConverter class."""
        converter = DataConverter()
        assert converter is not None
        
        # Test basic conversion methods exist
        assert hasattr(converter, 'convert')
    
    def test_json_converter(self):
        """Test JsonConverter class."""
        converter = JsonConverter()
        assert converter is not None
        
        # Test conversion
        data = {"test": "json_conversion"}
        converted = converter.convert(data)
        assert converted is not None
    
    def test_message_converter(self):
        """Test MessageConverter class."""
        converter = MessageConverter()
        assert converter is not None
        
        # Test message conversion methods exist
        assert hasattr(converter, 'convert_message')


class TestDebugging:
    """Test debugging utilities."""
    
    def test_debug_capture(self):
        """Test DebugCapture."""
        capture = DebugCapture()
        assert capture is not None
        
        # Test basic functionality
        assert hasattr(capture, 'start')
        assert hasattr(capture, 'stop')
    
    def test_performance_profiler(self):
        """Test PerformanceProfiler."""
        profiler = PerformanceProfiler()
        assert profiler is not None
        
        # Test basic functionality
        assert hasattr(profiler, 'start')
        assert hasattr(profiler, 'stop')
    
    def test_error_reporter(self):
        """Test ErrorReporter."""
        reporter = ErrorReporter()
        assert reporter is not None
        
        # Test basic functionality
        assert hasattr(reporter, 'report_error')
    
    def test_diagnostic_collector(self):
        """Test DiagnosticCollector."""
        collector = DiagnosticCollector()
        assert collector is not None
        
        # Test basic functionality
        assert hasattr(collector, 'collect')
    
    def test_debug_context(self):
        """Test debug_context function."""
        with debug_context("test_operation") as ctx:
            assert ctx is not None
            # Should complete without error
    
    def test_get_error_reporter(self):
        """Test get_error_reporter function."""
        reporter = get_error_reporter()
        assert reporter is not None
        assert isinstance(reporter, ErrorReporter)
    
    def test_get_diagnostic_collector(self):
        """Test get_diagnostic_collector function."""
        collector = get_diagnostic_collector()
        assert collector is not None
        assert isinstance(collector, DiagnosticCollector)


class TestErrorHandling:
    """Test error handling utilities."""
    
    def test_retry_manager(self):
        """Test RetryManager."""
        manager = RetryManager()
        assert manager is not None
        
        # Test basic functionality
        assert hasattr(manager, 'execute')
    
    def test_circuit_breaker(self):
        """Test CircuitBreaker."""
        breaker = CircuitBreaker()
        assert breaker is not None
        
        # Test basic functionality
        assert hasattr(breaker, 'execute')
    
    def test_error_recovery_manager(self):
        """Test ErrorRecoveryManager."""
        manager = ErrorRecoveryManager()
        assert manager is not None
        
        # Test basic functionality
        assert hasattr(manager, 'execute_with_recovery')
    
    def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        @with_retry(max_retries=2)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_with_circuit_breaker_decorator(self):
        """Test with_circuit_breaker decorator."""
        @with_circuit_breaker()
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_with_error_recovery_decorator(self):
        """Test with_error_recovery decorator."""
        @with_error_recovery()
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"


class TestLogging:
    """Test logging utilities."""
    
    def test_setup_logging(self):
        """Test setup_logging function."""
        logger = setup_logging("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_structured_logger(self):
        """Test StructuredLogger class."""
        logger = StructuredLogger("structured_test")
        assert logger is not None
        
        # Test basic functionality
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_logging_config(self):
        """Test LoggingConfig class."""
        config = LoggingConfig()
        assert config is not None
        
        # Test basic functionality
        assert hasattr(config, 'configure')


class TestUtilsIntegration:
    """Test utils module integration."""
    
    @pytest.mark.asyncio
    async def test_async_with_error_handling(self):
        """Test async helpers with error handling."""
        @with_retry(max_retries=2)
        async def async_operation():
            await asyncio.sleep(0.01)
            return "async_success"
        
        result = await async_operation()
        assert result == "async_success"
    
    def test_data_conversion_with_validation(self):
        """Test data conversion with validation."""
        data = {"test": "integration", "value": 123}
        
        # Convert to JSON
        json_str = convert_to_json(data)
        assert isinstance(json_str, str)
        
        # Convert back
        restored_data = convert_from_json(json_str)
        assert restored_data == data
        
        # Validate
        validation_result = validate_data(restored_data)
        assert validation_result is not None
    
    def test_debugging_with_logging(self):
        """Test debugging with logging integration."""
        logger = get_logger("debug_test")
        
        with debug_context("test_operation") as ctx:
            logger.info("Test log message")
            # Should complete without error
            assert ctx is not None
    
    def test_error_handling_with_logging(self):
        """Test error handling with logging."""
        logger = get_logger("error_test")
        
        @with_error_recovery()
        def operation_with_logging():
            logger.info("Operation started")
            return "logged_success"
        
        result = operation_with_logging()
        assert result == "logged_success"