"""
Connection and system event types for the Blackholio event system.

Defines all connection-related events including network state changes,
authentication events, subscription updates, and reducer executions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from .base import Event, EventType, EventPriority


@dataclass
class ConnectionEvent(Event):
    """Base class for all connection-related events."""
    
    event_type: EventType = field(default=EventType.CONNECTION)
    
    def validate(self) -> None:
        """Validate connection event data."""
        # Base validation is sufficient for most connection events
        pass


@dataclass
class ConnectionEstablishedEvent(ConnectionEvent):
    """Event fired when a connection to SpacetimeDB is established."""
    
    connection_info: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.CONNECTION)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "ConnectionEstablished"
    
    def validate(self) -> None:
        """Validate connection established event."""
        if not self.connection_info:
            raise ValueError("ConnectionEstablishedEvent requires connection_info")
        
        # Add connection data to event data for easy access
        self.data.update({
            'server_host': self.connection_info.get('host'),
            'server_port': self.connection_info.get('port'),
            'server_language': self.connection_info.get('server_language'),
            'protocol_version': self.connection_info.get('protocol'),
            'database_name': self.connection_info.get('database'),
            'connection_timestamp': self.timestamp,
            'connection_attempt': self.connection_info.get('attempt_number', 1)
        })


@dataclass
class ConnectionLostEvent(ConnectionEvent):
    """Event fired when connection to SpacetimeDB is lost."""
    
    error_info: Dict[str, Any] = field(default_factory=dict)
    was_expected: bool = field(default=False)
    event_type: EventType = field(default=EventType.CONNECTION)
    priority: EventPriority = field(default=EventPriority.CRITICAL)
    
    def get_event_name(self) -> str:
        return "ConnectionLost"
    
    def validate(self) -> None:
        """Validate connection lost event."""
        # Add error data to event data for easy access
        self.data.update({
            'error_type': self.error_info.get('error_type'),
            'error_message': self.error_info.get('message'),
            'error_code': self.error_info.get('code'),
            'was_expected': self.was_expected,
            'connection_duration': self.error_info.get('connection_duration'),
            'last_activity': self.error_info.get('last_activity'),
            'disconnect_timestamp': self.timestamp
        })


@dataclass
class ConnectionReconnectingEvent(ConnectionEvent):
    """Event fired when attempting to reconnect to SpacetimeDB."""
    
    attempt_info: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.CONNECTION)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return "ConnectionReconnecting"
    
    def validate(self) -> None:
        """Validate connection reconnecting event."""
        if not self.attempt_info:
            raise ValueError("ConnectionReconnectingEvent requires attempt_info")
        
        # Add reconnection data to event data for easy access
        self.data.update({
            'attempt_number': self.attempt_info.get('attempt_number', 1),
            'max_attempts': self.attempt_info.get('max_attempts'),
            'delay_seconds': self.attempt_info.get('delay_seconds'),
            'backoff_multiplier': self.attempt_info.get('backoff_multiplier'),
            'last_error': self.attempt_info.get('last_error'),
            'reconnect_timestamp': self.timestamp
        })


@dataclass
class ConnectionFailedEvent(ConnectionEvent):
    """Event fired when connection attempts have been exhausted."""
    
    failure_info: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.CONNECTION)
    priority: EventPriority = field(default=EventPriority.CRITICAL)
    
    def get_event_name(self) -> str:
        return "ConnectionFailed"
    
    def validate(self) -> None:
        """Validate connection failed event."""
        if not self.failure_info:
            raise ValueError("ConnectionFailedEvent requires failure_info")
        
        # Add failure data to event data for easy access
        self.data.update({
            'total_attempts': self.failure_info.get('total_attempts'),
            'total_duration': self.failure_info.get('total_duration'),
            'final_error': self.failure_info.get('final_error'),
            'error_history': self.failure_info.get('error_history', []),
            'failure_timestamp': self.timestamp
        })


@dataclass
class AuthenticationEvent(ConnectionEvent):
    """Event fired during authentication processes."""
    
    auth_data: Dict[str, Any] = field(default_factory=dict)
    auth_status: str = field(default="unknown")  # "started", "success", "failed", "expired"
    event_type: EventType = field(default=EventType.AUTHENTICATION)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return f"Authentication{self.auth_status.title()}"
    
    def validate(self) -> None:
        """Validate authentication event."""
        valid_statuses = ["started", "success", "failed", "expired", "refresh"]
        if self.auth_status not in valid_statuses:
            raise ValueError(f"auth_status must be one of {valid_statuses}")
        
        # Add auth data to event data for easy access
        self.data.update({
            'auth_status': self.auth_status,
            'user_id': self.auth_data.get('user_id'),
            'identity': self.auth_data.get('identity'),
            'token_type': self.auth_data.get('token_type'),
            'expires_at': self.auth_data.get('expires_at'),
            'auth_method': self.auth_data.get('method'),
            'auth_timestamp': self.timestamp
        })


@dataclass
class SubscriptionStateChangedEvent(ConnectionEvent):
    """Event fired when table subscription state changes."""
    
    table_name: str = field(default="")
    old_state: str = field(default="inactive")
    new_state: str = field(default="inactive")
    subscription_info: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.SUBSCRIPTION)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return "SubscriptionStateChanged"
    
    def validate(self) -> None:
        """Validate subscription state changed event."""
        if not self.table_name:
            raise ValueError("SubscriptionStateChangedEvent requires table_name")
        
        valid_states = ["inactive", "subscribing", "active", "failed", "unsubscribing"]
        if self.old_state not in valid_states or self.new_state not in valid_states:
            raise ValueError(f"States must be one of {valid_states}")
        
        # Add subscription data to event data for easy access
        self.data.update({
            'table_name': self.table_name,
            'old_state': self.old_state,
            'new_state': self.new_state,
            'state_change': f"{self.old_state} -> {self.new_state}",
            'subscription_id': self.subscription_info.get('subscription_id'),
            'error_info': self.subscription_info.get('error'),
            'subscription_timestamp': self.timestamp
        })


@dataclass
class TableDataReceivedEvent(ConnectionEvent):
    """Event fired when table data is received from SpacetimeDB."""
    
    table_name: str = field(default="")
    operation: str = field(default="unknown")  # "insert", "update", "delete", "initial"
    row_data: Dict[str, Any] = field(default_factory=dict)
    old_row_data: Optional[Dict[str, Any]] = field(default=None)
    event_type: EventType = field(default=EventType.SUBSCRIPTION)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return f"TableData{self.operation.title()}"
    
    def validate(self) -> None:
        """Validate table data received event."""
        if not self.table_name:
            raise ValueError("TableDataReceivedEvent requires table_name")
        
        valid_operations = ["insert", "update", "delete", "initial"]
        if self.operation not in valid_operations:
            raise ValueError(f"operation must be one of {valid_operations}")
        
        if self.operation == "update" and self.old_row_data is None:
            raise ValueError("update operation requires old_row_data")
        
        # Add table data to event data for easy access
        self.data.update({
            'table_name': self.table_name,
            'operation': self.operation,
            'row_id': self.row_data.get('id'),
            'has_old_data': self.old_row_data is not None,
            'data_timestamp': self.timestamp
        })


@dataclass
class ReducerExecutedEvent(ConnectionEvent):
    """Event fired when a reducer is executed."""
    
    reducer_name: str = field(default="")
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = field(default=None)
    execution_status: str = field(default="unknown")  # "started", "success", "failed", "timeout"
    execution_time: Optional[float] = field(default=None)
    event_type: EventType = field(default=EventType.REDUCER)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    
    def get_event_name(self) -> str:
        return f"Reducer{self.execution_status.title()}"
    
    def validate(self) -> None:
        """Validate reducer executed event."""
        if not self.reducer_name:
            raise ValueError("ReducerExecutedEvent requires reducer_name")
        
        valid_statuses = ["started", "success", "failed", "timeout"]
        if self.execution_status not in valid_statuses:
            raise ValueError(f"execution_status must be one of {valid_statuses}")
        
        # Add reducer data to event data for easy access
        self.data.update({
            'reducer_name': self.reducer_name,
            'execution_status': self.execution_status,
            'execution_time_ms': self.execution_time * 1000 if self.execution_time else None,
            'has_result': self.result is not None,
            'argument_count': len(self.arguments),
            'reducer_timestamp': self.timestamp
        })


@dataclass
class SystemErrorEvent(Event):
    """Event fired when system errors occur."""
    
    error_type: str = field(default="unknown")
    error_message: str = field(default="")
    error_details: Dict[str, Any] = field(default_factory=dict)
    component: Optional[str] = field(default=None)
    is_recoverable: bool = field(default=True)
    event_type: EventType = field(default=EventType.ERROR)
    priority: EventPriority = field(default=EventPriority.HIGH)
    
    def get_event_name(self) -> str:
        return f"SystemError_{self.error_type}"
    
    def validate(self) -> None:
        """Validate system error event."""
        if not self.error_message:
            raise ValueError("SystemErrorEvent requires error_message")
        
        # Add error data to event data for easy access
        self.data.update({
            'error_type': self.error_type,
            'error_message': self.error_message,
            'component': self.component,
            'is_recoverable': self.is_recoverable,
            'stack_trace': self.error_details.get('stack_trace'),
            'error_context': self.error_details.get('context'),
            'error_timestamp': self.timestamp
        })


@dataclass
class SystemDebugEvent(Event):
    """Event fired for debugging and development purposes."""
    
    debug_category: str = field(default="general")
    debug_message: str = field(default="")
    debug_data: Dict[str, Any] = field(default_factory=dict)
    component: Optional[str] = field(default=None)
    event_type: EventType = field(default=EventType.DEBUG)
    priority: EventPriority = field(default=EventPriority.LOW)
    
    def get_event_name(self) -> str:
        return f"Debug_{self.debug_category}"
    
    def validate(self) -> None:
        """Validate system debug event."""
        if not self.debug_message:
            raise ValueError("SystemDebugEvent requires debug_message")
        
        # Add debug data to event data for easy access
        self.data.update({
            'debug_category': self.debug_category,
            'debug_message': self.debug_message,
            'component': self.component,
            'debug_timestamp': self.timestamp
        })


@dataclass
class PerformanceMetricEvent(Event):
    """Event fired for performance monitoring."""
    
    metric_name: str = field(default="")
    metric_value: Union[int, float] = field(default=0)
    metric_unit: str = field(default="")
    metric_context: Dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.SYSTEM)
    priority: EventPriority = field(default=EventPriority.LOW)
    
    def get_event_name(self) -> str:
        return f"Metric_{self.metric_name}"
    
    def validate(self) -> None:
        """Validate performance metric event."""
        if not self.metric_name:
            raise ValueError("PerformanceMetricEvent requires metric_name")
        
        # Add metric data to event data for easy access
        self.data.update({
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'metric_timestamp': self.timestamp
        })


# Convenience factory functions for common connection events
def create_connection_established_event(host: str, port: int, server_language: str, database: str, **kwargs) -> ConnectionEstablishedEvent:
    """Create a ConnectionEstablishedEvent with the given data."""
    connection_info = {
        'host': host,
        'port': port,
        'server_language': server_language,
        'database': database,
        **kwargs
    }
    return ConnectionEstablishedEvent(connection_info=connection_info)


def create_connection_lost_event(error_message: str, error_type: str = "unknown", was_expected: bool = False, **kwargs) -> ConnectionLostEvent:
    """Create a ConnectionLostEvent with the given data."""
    error_info = {
        'message': error_message,
        'error_type': error_type,
        **kwargs
    }
    return ConnectionLostEvent(error_info=error_info, was_expected=was_expected)


def create_connection_reconnecting_event(attempt_number: int, delay_seconds: float, **kwargs) -> ConnectionReconnectingEvent:
    """Create a ConnectionReconnectingEvent with the given data."""
    attempt_info = {
        'attempt_number': attempt_number,
        'delay_seconds': delay_seconds,
        **kwargs
    }
    return ConnectionReconnectingEvent(attempt_info=attempt_info)


def create_authentication_event(status: str, user_id: Optional[str] = None, **kwargs) -> AuthenticationEvent:
    """Create an AuthenticationEvent with the given data."""
    auth_data = {'user_id': user_id, **kwargs}
    return AuthenticationEvent(auth_data=auth_data, auth_status=status)


def create_subscription_state_changed_event(table_name: str, old_state: str, new_state: str, **kwargs) -> SubscriptionStateChangedEvent:
    """Create a SubscriptionStateChangedEvent with the given data."""
    return SubscriptionStateChangedEvent(
        table_name=table_name,
        old_state=old_state,
        new_state=new_state,
        subscription_info=kwargs
    )


def create_table_data_received_event(table_name: str, operation: str, row_data: Dict[str, Any], old_row_data: Optional[Dict[str, Any]] = None, **kwargs) -> TableDataReceivedEvent:
    """Create a TableDataReceivedEvent with the given data."""
    return TableDataReceivedEvent(
        table_name=table_name,
        operation=operation,
        row_data=row_data,
        old_row_data=old_row_data,
        **kwargs
    )


def create_reducer_executed_event(reducer_name: str, status: str, arguments: Optional[Dict[str, Any]] = None, result: Optional[Dict[str, Any]] = None, execution_time: Optional[float] = None, **kwargs) -> ReducerExecutedEvent:
    """Create a ReducerExecutedEvent with the given data."""
    return ReducerExecutedEvent(
        reducer_name=reducer_name,
        execution_status=status,
        arguments=arguments or {},
        result=result,
        execution_time=execution_time,
        **kwargs
    )


def create_system_error_event(error_type: str, error_message: str, component: Optional[str] = None, is_recoverable: bool = True, **kwargs) -> SystemErrorEvent:
    """Create a SystemErrorEvent with the given data."""
    return SystemErrorEvent(
        error_type=error_type,
        error_message=error_message,
        component=component,
        is_recoverable=is_recoverable,
        error_details=kwargs
    )