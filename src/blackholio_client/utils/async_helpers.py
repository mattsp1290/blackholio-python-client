"""
Async Helpers - Utility Functions for Asyncio Operations

Provides helper functions and utilities for async operations, task management,
and concurrent programming patterns commonly used in the blackholio client.
"""

import asyncio
import functools
import logging
import time
import weakref
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TaskManager:
    """
    Manages asyncio tasks with automatic cleanup and monitoring.
    
    Provides utilities for task creation, cancellation, and lifecycle management
    with proper error handling and resource cleanup.
    """
    
    def __init__(self, name: str = "TaskManager"):
        """
        Initialize task manager.
        
        Args:
            name: Name for this task manager instance
        """
        self.name = name
        self._tasks: Set[asyncio.Task] = set()
        self._task_names: Dict[asyncio.Task, str] = {}
        self._shutdown = False
        
        logger.debug(f"Task manager '{name}' initialized")
    
    def create_task(self, coro: Awaitable[T], name: Optional[str] = None) -> asyncio.Task[T]:
        """
        Create and track an asyncio task.
        
        Args:
            coro: Coroutine to run
            name: Optional name for the task
            
        Returns:
            Created asyncio.Task
        """
        if self._shutdown:
            raise RuntimeError("TaskManager is shut down")
        
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        
        if name:
            self._task_names[task] = name
        
        # Add done callback for cleanup
        task.add_done_callback(self._task_done_callback)
        
        logger.debug(f"Created task: {name or 'unnamed'}")
        return task
    
    def create_background_task(self, coro: Awaitable[T], name: Optional[str] = None) -> asyncio.Task[T]:
        """
        Create a background task that logs exceptions but doesn't propagate them.
        
        Args:
            coro: Coroutine to run
            name: Optional name for the task
            
        Returns:
            Created asyncio.Task
        """
        async def wrapper():
            try:
                return await coro
            except asyncio.CancelledError:
                logger.debug(f"Background task {name or 'unnamed'} was cancelled")
                raise
            except Exception as e:
                logger.error(f"Background task {name or 'unnamed'} failed: {e}")
                raise
        
        return self.create_task(wrapper(), name=name)
    
    def cancel_task(self, task: asyncio.Task) -> bool:
        """
        Cancel a specific task.
        
        Args:
            task: Task to cancel
            
        Returns:
            True if task was cancelled
        """
        if task in self._tasks and not task.done():
            task.cancel()
            return True
        return False
    
    def cancel_all(self):
        """Cancel all managed tasks."""
        cancelled_count = 0
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} tasks")
    
    async def shutdown(self, timeout: float = 10.0):
        """
        Shutdown task manager and wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        self._shutdown = True
        
        if not self._tasks:
            return
        
        logger.info(f"Shutting down task manager '{self.name}' with {len(self._tasks)} tasks")
        
        # Cancel all tasks
        self.cancel_all()
        
        # Wait for tasks to complete
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for tasks to complete in {timeout}s")
        
        self._tasks.clear()
        self._task_names.clear()
        logger.info(f"Task manager '{self.name}' shutdown complete")
    
    def _task_done_callback(self, task: asyncio.Task):
        """Callback for when a task completes."""
        self._tasks.discard(task)
        name = self._task_names.pop(task, "unnamed")
        
        if task.cancelled():
            logger.debug(f"Task {name} was cancelled")
        elif task.exception():
            logger.error(f"Task {name} failed with exception: {task.exception()}")
        else:
            logger.debug(f"Task {name} completed successfully")
    
    @property
    def task_count(self) -> int:
        """Get number of active tasks."""
        return len(self._tasks)
    
    @property
    def is_shutdown(self) -> bool:
        """Check if task manager is shut down."""
        return self._shutdown
    
    def get_task_info(self) -> List[Dict[str, Any]]:
        """Get information about all managed tasks."""
        info = []
        for task in self._tasks:
            name = self._task_names.get(task, "unnamed")
            info.append({
                'name': name,
                'done': task.done(),
                'cancelled': task.cancelled(),
                'exception': str(task.exception()) if task.exception() else None
            })
        return info


class AsyncEventEmitter:
    """
    Async event emitter for decoupled communication.
    
    Provides a way to emit and listen for events asynchronously
    with proper error handling and cleanup.
    """
    
    def __init__(self):
        """Initialize async event emitter."""
        self._listeners: Dict[str, List[Callable]] = {}
        self._once_listeners: Dict[str, List[Callable]] = {}
        
    def on(self, event: str, callback: Callable):
        """
        Register a persistent event listener.
        
        Args:
            event: Event name
            callback: Callback function (can be async)
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def once(self, event: str, callback: Callable):
        """
        Register a one-time event listener.
        
        Args:
            event: Event name
            callback: Callback function (can be async)
        """
        if event not in self._once_listeners:
            self._once_listeners[event] = []
        self._once_listeners[event].append(callback)
    
    def off(self, event: str, callback: Optional[Callable] = None):
        """
        Remove event listener(s).
        
        Args:
            event: Event name
            callback: Specific callback to remove (removes all if None)
        """
        if callback is None:
            # Remove all listeners for event
            self._listeners.pop(event, None)
            self._once_listeners.pop(event, None)
        else:
            # Remove specific callback
            if event in self._listeners:
                try:
                    self._listeners[event].remove(callback)
                except ValueError:
                    pass
            if event in self._once_listeners:
                try:
                    self._once_listeners[event].remove(callback)
                except ValueError:
                    pass
    
    async def emit(self, event: str, *args, **kwargs):
        """
        Emit an event to all listeners.
        
        Args:
            event: Event name
            *args: Positional arguments for callbacks
            **kwargs: Keyword arguments for callbacks
        """
        # Get all listeners
        persistent = self._listeners.get(event, []).copy()
        once = self._once_listeners.pop(event, [])
        
        all_listeners = persistent + once
        
        if not all_listeners:
            return
        
        # Execute all callbacks
        tasks = []
        for callback in all_listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(asyncio.create_task(callback(*args, **kwargs)))
                else:
                    # Run sync callback in executor
                    loop = asyncio.get_event_loop()
                    tasks.append(loop.run_in_executor(None, callback, *args, **kwargs))
            except Exception as e:
                logger.error(f"Error calling event listener for {event}: {e}")
        
        # Wait for all callbacks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class AsyncThrottle:
    """
    Async throttling utility to limit function call frequency.
    
    Ensures a function is not called more frequently than specified,
    useful for rate limiting API calls or expensive operations.
    """
    
    def __init__(self, rate: float):
        """
        Initialize throttle.
        
        Args:
            rate: Minimum time between calls in seconds
        """
        self.rate = rate
        self._last_call = 0
        self._lock = asyncio.Lock()
    
    async def __call__(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Call function with throttling.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            
            if elapsed < self.rate:
                wait_time = self.rate - elapsed
                await asyncio.sleep(wait_time)
            
            self._last_call = time.time()
            return await func(*args, **kwargs)


class AsyncDebounce:
    """
    Async debouncing utility to delay function execution.
    
    Ensures a function is only called after a specified delay
    with no additional calls, useful for handling user input.
    """
    
    def __init__(self, delay: float):
        """
        Initialize debounce.
        
        Args:
            delay: Delay in seconds before calling function
        """
        self.delay = delay
        self._task: Optional[asyncio.Task] = None
    
    async def __call__(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> Optional[T]:
        """
        Call function with debouncing.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if cancelled
        """
        # Cancel previous task
        if self._task and not self._task.done():
            self._task.cancel()
        
        # Create new delayed task
        async def delayed_call():
            await asyncio.sleep(self.delay)
            return await func(*args, **kwargs)
        
        self._task = asyncio.create_task(delayed_call())
        
        try:
            return await self._task
        except asyncio.CancelledError:
            return None


class AsyncRetry:
    """
    Async retry utility with exponential backoff.
    
    Automatically retries failed async operations with configurable
    retry logic and backoff strategies.
    """
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """
        Initialize retry utility.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    async def __call__(self, 
                      func: Callable[..., Awaitable[T]], 
                      *args, 
                      retry_on: Optional[Union[Exception, tuple]] = None,
                      **kwargs) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            retry_on: Exception types to retry on
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if retry_on and not isinstance(e, retry_on):
                    raise
                
                # Don't retry on last attempt
                if attempt == self.max_attempts - 1:
                    raise
                
                # Calculate delay
                delay = min(
                    self.base_delay * (self.exponential_base ** attempt),
                    self.max_delay
                )
                
                # Add jitter
                if self.jitter:
                    import random
                    import secrets
                    delay *= (0.5 + random.random() * 0.5)
                
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


@asynccontextmanager
async def timeout_context(timeout: float):
    """
    Async context manager for timeout operations.
    
    Args:
        timeout: Timeout in seconds
    """
    try:
        async with asyncio.timeout(timeout):
            yield
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout}s")
        raise


async def run_with_timeout(coro: Awaitable[T], timeout: float) -> T:
    """
    Run coroutine with timeout.
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        
    Returns:
        Coroutine result
        
    Raises:
        asyncio.TimeoutError: If operation times out
    """
    return await asyncio.wait_for(coro, timeout=timeout)


async def gather_with_limit(coroutines: List[Awaitable], limit: int = 10) -> List[Any]:
    """
    Gather coroutines with concurrency limit.
    
    Args:
        coroutines: List of coroutines to execute
        limit: Maximum concurrent executions
        
    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(limit)
    
    async def limited_coro(coro):
        async with semaphore:
            return await coro
    
    limited_coroutines = [limited_coro(coro) for coro in coroutines]
    return await asyncio.gather(*limited_coroutines, return_exceptions=True)


def run_in_executor(func: Callable, *args, executor: Optional[ThreadPoolExecutor] = None) -> Awaitable:
    """
    Run sync function in executor.
    
    Args:
        func: Sync function to run
        *args: Function arguments
        executor: Optional thread pool executor
        
    Returns:
        Awaitable that will complete when function finishes
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args)


def async_cached(ttl_seconds: float = 300):
    """
    Decorator for caching async function results with TTL.
    
    Args:
        ttl_seconds: Time to live for cached results
    """
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = (args, tuple(sorted(kwargs.items())))
            
            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache[key] = (result, time.time())
            
            return result
        
        return wrapper
    return decorator


# Legacy compatibility functions (keeping existing interface)
def run_async(coro: Awaitable[Any]) -> Any:
    """
    Run an async coroutine in a sync context.
    
    Args:
        coro: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            task = asyncio.create_task(coro)
            return task
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(coro)


async def create_task_with_error_handling(coro: Awaitable[Any], 
                                        error_callback: Optional[Callable[[Exception], None]] = None,
                                        task_name: Optional[str] = None) -> asyncio.Task:
    """
    Create an async task with error handling.
    
    Args:
        coro: Coroutine to run as task
        error_callback: Optional callback for handling errors
        task_name: Optional name for the task
        
    Returns:
        Created task
    """
    async def wrapped_coro():
        try:
            return await coro
        except Exception as e:
            logger.error(f"Error in task {task_name or 'unnamed'}: {e}")
            if error_callback:
                try:
                    error_callback(e)
                except Exception as callback_error:
                    logger.error(f"Error in error callback: {callback_error}")
            raise
    
    task = asyncio.create_task(wrapped_coro())
    if task_name:
        task.set_name(task_name)
    
    return task


async def wait_for_condition(condition: Callable[[], bool],
                           timeout: float = 30.0,
                           check_interval: float = 0.1) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        check_interval: How often to check the condition in seconds
        
    Returns:
        True if condition was met, False if timeout occurred
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition():
                return True
        except Exception as e:
            logger.warning(f"Error checking condition: {e}")
        
        await asyncio.sleep(check_interval)
    
    return False


# Global task manager for convenience
_global_task_manager: Optional[TaskManager] = None


def get_global_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager("global")
    return _global_task_manager


async def shutdown_global_task_manager():
    """Shutdown the global task manager."""
    global _global_task_manager
    if _global_task_manager:
        await _global_task_manager.shutdown()
        _global_task_manager = None