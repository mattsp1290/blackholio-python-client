"""
Reducer Client - SpacetimeDB Reducer Call Management

Provides a high-level interface for calling SpacetimeDB reducers with
proper error handling, response validation, and type safety.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Type
from dataclasses import dataclass
from enum import Enum

from .action_formatter import ActionFormatter, GameActionFormatter, Action, ActionType
from ..connection.spacetimedb_connection import SpacetimeDBConnection
from ..models.game_entities import Vector2, GameEntity, GamePlayer, GameCircle
from ..exceptions.connection_errors import (
    SpacetimeDBError,
    DataValidationError,
    BlackholioTimeoutError,
    AuthenticationError
)


logger = logging.getLogger(__name__)


class ReducerStatus(Enum):
    """Reducer call status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ReducerResult:
    """
    Result of a reducer call.
    
    Contains the response data, status, and any error information
    from a SpacetimeDB reducer execution.
    """
    status: ReducerStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time: Optional[float] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_success(self) -> bool:
        """Check if reducer call was successful."""
        return self.status == ReducerStatus.SUCCESS
    
    @property
    def is_failed(self) -> bool:
        """Check if reducer call failed."""
        return self.status in (ReducerStatus.FAILED, ReducerStatus.TIMEOUT)
    
    def get_error_message(self) -> str:
        """Get formatted error message."""
        if self.error:
            if self.error_code:
                return f"[{self.error_code}] {self.error}"
            return self.error
        return "Unknown error"


class ReducerError(SpacetimeDBError):
    """Exception raised for reducer-specific errors."""
    
    def __init__(self, message: str, result: Optional[ReducerResult] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.result = result


class ReducerClient:
    """
    High-level client for calling SpacetimeDB reducers.
    
    Provides a convenient interface for executing reducers with proper
    error handling, response validation, and automatic retries.
    """
    
    def __init__(self, connection: SpacetimeDBConnection, 
                 default_timeout: float = 30.0,
                 auto_retry: bool = True,
                 max_retries: int = 3):
        """
        Initialize reducer client.
        
        Args:
            connection: SpacetimeDB connection instance
            default_timeout: Default timeout for reducer calls
            auto_retry: Enable automatic retries on failure
            max_retries: Maximum number of retry attempts
        """
        self.connection = connection
        self.default_timeout = default_timeout
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        
        # Formatters
        self.action_formatter = ActionFormatter()
        self.game_formatter = GameActionFormatter()
        
        # Response handlers
        self._response_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self._calls_made = 0
        self._calls_successful = 0
        self._calls_failed = 0
        
        logger.info("Reducer client initialized")
    
    async def call_reducer(self, reducer_name: str, args: Dict[str, Any], 
                          timeout: Optional[float] = None,
                          retry_count: int = 0) -> ReducerResult:
        """
        Call a SpacetimeDB reducer.
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            timeout: Call timeout (uses default if None)
            retry_count: Current retry attempt (internal use)
            
        Returns:
            ReducerResult with response data or error
        """
        timeout = timeout or self.default_timeout
        start_time = asyncio.get_event_loop().time()
        
        try:
            self._calls_made += 1
            
            # Format the action
            action_message = self.action_formatter.format_reducer_call(
                reducer_name, args
            )
            
            # Validate action
            self.action_formatter.validate_action(action_message['action'])
            
            # Send request
            logger.debug(f"Calling reducer: {reducer_name} with args: {args}")
            
            response = await self.connection.send_request(
                "call_reducer", 
                action_message,
                timeout=timeout
            )
            
            # Process response
            result = self._process_reducer_response(response, start_time)
            
            if result.is_success:
                self._calls_successful += 1
                logger.debug(f"Reducer {reducer_name} completed successfully")
            else:
                self._calls_failed += 1
                logger.warning(f"Reducer {reducer_name} failed: {result.get_error_message()}")
                
                # Retry if enabled and retries remaining
                if (self.auto_retry and 
                    retry_count < self.max_retries and 
                    self._should_retry_error(result)):
                    
                    retry_delay = min(2.0 ** retry_count, 10.0)  # Exponential backoff
                    logger.info(f"Retrying reducer {reducer_name} in {retry_delay}s (attempt {retry_count + 1})")
                    
                    await asyncio.sleep(retry_delay)
                    return await self.call_reducer(reducer_name, args, timeout, retry_count + 1)
            
            return result
            
        except BlackholioTimeoutError as e:
            self._calls_failed += 1
            return ReducerResult(
                status=ReducerStatus.TIMEOUT,
                error=str(e),
                error_code="TIMEOUT",
                execution_time=asyncio.get_event_loop().time() - start_time
            )
            
        except Exception as e:
            self._calls_failed += 1
            logger.error(f"Reducer call failed: {e}")
            return ReducerResult(
                status=ReducerStatus.FAILED,
                error=str(e),
                error_code="CALL_FAILED",
                execution_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def call_reducer_safe(self, reducer_name: str, args: Dict[str, Any], 
                               timeout: Optional[float] = None) -> Optional[Any]:
        """
        Call reducer and return data or None on error.
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            timeout: Call timeout
            
        Returns:
            Response data or None if failed
        """
        result = await self.call_reducer(reducer_name, args, timeout)
        return result.data if result.is_success else None
    
    async def call_reducer_strict(self, reducer_name: str, args: Dict[str, Any], 
                                 timeout: Optional[float] = None) -> Any:
        """
        Call reducer and raise exception on error.
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            timeout: Call timeout
            
        Returns:
            Response data
            
        Raises:
            ReducerError: If reducer call failed
        """
        result = await self.call_reducer(reducer_name, args, timeout)
        
        if result.is_failed:
            raise ReducerError(
                f"Reducer '{reducer_name}' failed: {result.get_error_message()}",
                result=result
            )
        
        return result.data
    
    def _process_reducer_response(self, response: Dict[str, Any], start_time: float) -> ReducerResult:
        """Process reducer response into ReducerResult."""
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Check for error in response
        if 'error' in response:
            error_data = response['error']
            return ReducerResult(
                status=ReducerStatus.FAILED,
                error=error_data.get('message', 'Unknown error'),
                error_code=error_data.get('code'),
                execution_time=execution_time,
                request_id=response.get('request_id'),
                metadata=response.get('metadata', {})
            )
        
        # Success response
        return ReducerResult(
            status=ReducerStatus.SUCCESS,
            data=response.get('result', response.get('data')),
            execution_time=execution_time,
            request_id=response.get('request_id'),
            metadata=response.get('metadata', {})
        )
    
    def _should_retry_error(self, result: ReducerResult) -> bool:
        """Determine if error should be retried."""
        # Don't retry validation or authentication errors
        if result.error_code in ('VALIDATION_ERROR', 'AUTH_ERROR', 'PERMISSION_DENIED'):
            return False
        
        # Retry on timeout or connection errors
        if result.status == ReducerStatus.TIMEOUT:
            return True
        
        # Retry on temporary server errors
        if result.error_code in ('SERVER_ERROR', 'TEMPORARY_ERROR', 'RATE_LIMITED'):
            return True
        
        return False
    
    def register_response_handler(self, reducer_name: str, handler: Callable):
        """
        Register custom response handler for a reducer.
        
        Args:
            reducer_name: Name of the reducer
            handler: Function to process response data
        """
        self._response_handlers[reducer_name] = handler
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reducer call statistics."""
        total_calls = self._calls_made
        success_rate = (self._calls_successful / total_calls * 100) if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'successful_calls': self._calls_successful,
            'failed_calls': self._calls_failed,
            'success_rate': success_rate,
            'connection_state': self.connection.state.value if self.connection else None
        }


# Type-safe reducer call helpers
class TypedReducerClient(ReducerClient):
    """
    Type-safe reducer client with built-in validation and conversion.
    
    Provides strongly-typed methods for common reducer patterns with
    automatic validation and response type conversion.
    """
    
    async def call_with_validation(self, reducer_name: str, args: Dict[str, Any],
                                  response_type: Optional[Type] = None,
                                  timeout: Optional[float] = None) -> Any:
        """
        Call reducer with automatic validation and type conversion.
        
        Args:
            reducer_name: Name of the reducer
            args: Reducer arguments
            response_type: Expected response type for conversion
            timeout: Call timeout
            
        Returns:
            Converted response data
        """
        # Validate arguments
        self._validate_args(reducer_name, args)
        
        # Call reducer
        result = await self.call_reducer_strict(reducer_name, args, timeout)
        
        # Convert response if type specified
        if response_type and result:
            return self._convert_response(result, response_type)
        
        return result
    
    def _validate_args(self, reducer_name: str, args: Dict[str, Any]):
        """Validate reducer arguments."""
        # TODO: Implement schema-based validation
        # For now, basic validation
        if not isinstance(args, dict):
            raise DataValidationError("Reducer args must be a dictionary")
        
        # Validate Vector2 objects
        for key, value in args.items():
            if isinstance(value, dict) and 'x' in value and 'y' in value:
                # Ensure Vector2 fields are numbers
                if not isinstance(value['x'], (int, float)) or not isinstance(value['y'], (int, float)):
                    raise DataValidationError(f"Invalid Vector2 in arg '{key}': coordinates must be numbers")
    
    def _convert_response(self, data: Any, response_type: Type) -> Any:
        """Convert response data to specified type."""
        try:
            if response_type == GameEntity and isinstance(data, dict):
                return GameEntity.from_dict(data)
            elif response_type == GamePlayer and isinstance(data, dict):
                return GamePlayer.from_dict(data)
            elif response_type == GameCircle and isinstance(data, dict):
                return GameCircle.from_dict(data)
            elif response_type == Vector2 and isinstance(data, dict):
                return Vector2.from_dict(data)
            elif isinstance(data, list) and response_type in (GameEntity, GamePlayer, GameCircle):
                return [response_type.from_dict(item) for item in data if isinstance(item, dict)]
            
            return data
            
        except Exception as e:
            logger.error(f"Response conversion failed: {e}")
            raise DataValidationError(f"Failed to convert response to {response_type.__name__}: {e}")


# Convenience functions for common reducer patterns
async def call_game_reducer(connection: SpacetimeDBConnection, 
                           action_name: str, 
                           **kwargs) -> ReducerResult:
    """
    Convenience function for calling game reducers.
    
    Args:
        connection: SpacetimeDB connection
        action_name: Game action name
        **kwargs: Action parameters
        
    Returns:
        ReducerResult
    """
    client = ReducerClient(connection)
    return await client.call_reducer(f"game_{action_name}", kwargs)


async def enter_game_safe(connection: SpacetimeDBConnection, 
                         player_name: str, 
                         identity_id: Optional[str] = None) -> bool:
    """
    Safely enter game with error handling.
    
    Args:
        connection: SpacetimeDB connection
        player_name: Player name
        identity_id: Optional identity ID
        
    Returns:
        True if successful
    """
    try:
        result = await call_game_reducer(
            connection, 
            "enter_game", 
            player_name=player_name,
            identity_id=identity_id
        )
        return result.is_success
    except Exception as e:
        logger.error(f"Failed to enter game: {e}")
        return False


async def update_player_input_safe(connection: SpacetimeDBConnection, 
                                  direction: Vector2) -> bool:
    """
    Safely update player input with error handling.
    
    Args:
        connection: SpacetimeDB connection
        direction: Movement direction
        
    Returns:
        True if successful
    """
    try:
        result = await call_game_reducer(
            connection,
            "update_player_input",
            direction=direction.to_dict()
        )
        return result.is_success
    except Exception as e:
        logger.error(f"Failed to update player input: {e}")
        return False