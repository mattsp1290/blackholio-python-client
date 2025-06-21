"""
Utils Module - Utility Functions and Helpers

Provides utility functions, async helpers, logging configuration,
and data conversion utilities for the blackholio client.
"""

from .async_helpers import (
    TaskManager,
    AsyncEventEmitter,
    AsyncThrottle,
    AsyncDebounce,
    AsyncRetry,
    timeout_context,
    run_with_timeout,
    gather_with_limit,
    run_in_executor,
    async_cached,
    get_global_task_manager,
    shutdown_global_task_manager,
    # Legacy compatibility
    run_async,
    create_task_with_error_handling,
    wait_for_condition
)

from .logging_config import (
    LoggingConfig,
    ColoredFormatter,
    JsonFormatter,
    PerformanceLogger,
    StructuredLogger,
    setup_logging,
    get_logger,
    log_performance,
    enable_debug_logging,
    enable_production_logging,
    configure_third_party_loggers,
    log_connection_event,
    log_game_event,
    LogLevel
)

from .data_converters import (
    DataConverter,
    JsonConverter,
    MessageConverter,
    ValidationHelper,
    TypeCoercion,
    get_data_converter,
    get_json_converter,
    get_message_converter,
    convert_to_json,
    convert_from_json,
    convert_entities,
    convert_players,
    validate_data
)

from .error_handling import (
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

from .debugging import (
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

from .validation import (
    validate_file_path,
    validate_identifier,
    validate_json_data,
    validate_network_address
)

__all__ = [
    # Async helpers
    "TaskManager",
    "AsyncEventEmitter", 
    "AsyncThrottle",
    "AsyncDebounce",
    "AsyncRetry",
    "timeout_context",
    "run_with_timeout",
    "gather_with_limit",
    "run_in_executor",
    "async_cached",
    "get_global_task_manager",
    "shutdown_global_task_manager",
    "run_async",
    "create_task_with_error_handling",
    "wait_for_condition",
    
    # Logging
    "LoggingConfig",
    "ColoredFormatter",
    "JsonFormatter",
    "PerformanceLogger",
    "StructuredLogger",
    "setup_logging",
    "get_logger",
    "log_performance",
    "enable_debug_logging",
    "enable_production_logging",
    "configure_third_party_loggers",
    "log_connection_event",
    "log_game_event",
    "LogLevel",
    
    # Data conversion
    "DataConverter",
    "JsonConverter",
    "MessageConverter",
    "ValidationHelper",
    "TypeCoercion",
    "get_data_converter",
    "get_json_converter",
    "get_message_converter",
    "convert_to_json",
    "convert_from_json",
    "convert_entities",
    "convert_players",
    "validate_data",
    
    # Error handling
    "RetryStrategy",
    "CircuitState",
    "RetryConfig",
    "CircuitBreakerConfig",
    "ErrorContext",
    "RetryManager",
    "CircuitBreaker",
    "ErrorRecoveryManager",
    "with_retry",
    "with_circuit_breaker",
    "with_error_recovery",
    "handle_errors",
    "handle_errors_async",
    "get_global_error_manager",
    "configure_global_error_handling",
    "execute_with_retry",
    "execute_with_retry_async",
    
    # Debugging
    "DebugContext",
    "ErrorReport",
    "DebugCapture",
    "PerformanceProfiler",
    "ErrorReporter",
    "DiagnosticCollector",
    "debug_context",
    "debug_function",
    "get_error_reporter",
    "get_diagnostic_collector",
    "capture_exception",
    "generate_diagnostics",
    
    # Validation
    "validate_file_path",
    "validate_identifier",
    "validate_json_data",
    "validate_network_address"
]