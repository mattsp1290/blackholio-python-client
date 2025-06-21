"""
Validation utilities for security and data integrity.

This module provides validation functions for file paths, data, and other
security-sensitive operations.
"""

import os
from pathlib import Path
from typing import Optional, Union


def validate_file_path(file_path: Union[str, Path], allow_absolute: bool = True) -> bool:
    """
    Validate a file path for security.
    
    Prevents path traversal attacks and ensures paths are within safe boundaries.
    
    Args:
        file_path: The file path to validate
        allow_absolute: Whether to allow absolute paths
        
    Returns:
        True if the path is safe, False otherwise
        
    Raises:
        ValueError: If the path contains dangerous patterns
    """
    if not file_path:
        return False
        
    # Convert to Path object for consistent handling
    path = Path(file_path)
    
    # Check for dangerous patterns
    dangerous_patterns = [
        '../',
        '..\\',
        '/etc/passwd',
        '\\etc\\passwd',
        '/proc/',
        '\\proc\\',
        '/sys/',
        '\\sys\\',
        '/dev/',
        '\\dev\\',
    ]
    
    path_str = str(file_path)
    for pattern in dangerous_patterns:
        if pattern in path_str:
            raise ValueError(f"Dangerous path pattern detected: {pattern}")
    
    # Check if path is trying to escape current directory
    try:
        resolved_path = path.resolve()
        
        # For absolute paths, check against common sensitive directories
        if path.is_absolute() and not allow_absolute:
            return False
            
        # Check if path is within current working directory or temp directory
        cwd = Path.cwd()
        temp_dir = Path(tempfile.gettempdir())
        
        # For relative paths, check if they're within cwd
        if not path.is_absolute():
            try:
                resolved_path.relative_to(cwd)
                return True
            except ValueError:
                return False
        
        # For absolute paths, check if they're in safe locations
        if allow_absolute and path.is_absolute():
            safe_prefixes = ['/tmp', '/var/tmp', '/private/tmp', '/private/var', str(cwd), str(temp_dir)]
            path_str = str(resolved_path)
            for prefix in safe_prefixes:
                if path_str.startswith(prefix):
                    return True
            
            # Also allow if path is within temp directory
            try:
                resolved_path.relative_to(temp_dir)
                return True
            except ValueError:
                pass
                
        return False
            
    except Exception:
        # If we can't resolve the path, it's not safe
        return False


def validate_identifier(identifier: str, max_length: int = 255) -> bool:
    """
    Validate an identifier (username, entity ID, etc.) for safety.
    
    Args:
        identifier: The identifier to validate
        max_length: Maximum allowed length
        
    Returns:
        True if the identifier is valid, False otherwise
    """
    if not identifier or not isinstance(identifier, str):
        return False
        
    if len(identifier) > max_length:
        return False
        
    # Only allow alphanumeric, underscore, hyphen
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', identifier):
        return False
        
    return True


def validate_json_data(data: dict, max_size: int = 1024 * 1024) -> bool:
    """
    Validate JSON data for safety.
    
    Args:
        data: The JSON data to validate
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if the data is safe, False otherwise
    """
    if not isinstance(data, dict):
        return False
        
    # Check size
    import json
    try:
        json_str = json.dumps(data)
        if len(json_str) > max_size:
            return False
    except Exception:
        return False
        
    return True


def validate_network_address(host: str, port: int) -> bool:
    """
    Validate network address for safety.
    
    Args:
        host: The hostname or IP address
        port: The port number
        
    Returns:
        True if the address is valid, False otherwise
    """
    if not host or not isinstance(host, str):
        return False
        
    if not isinstance(port, int) or port < 1 or port > 65535:
        return False
        
    # Check for localhost/private addresses
    private_patterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1',
        '192.168.',
        '10.',
        '172.16.',
        '172.17.',
        '172.18.',
        '172.19.',
        '172.20.',
        '172.21.',
        '172.22.',
        '172.23.',
        '172.24.',
        '172.25.',
        '172.26.',
        '172.27.',
        '172.28.',
        '172.29.',
        '172.30.',
        '172.31.',
    ]
    
    host_lower = host.lower()
    for pattern in private_patterns:
        if host_lower.startswith(pattern):
            return True  # Private addresses are safe
            
    # For public addresses, additional validation could be added
    return True


# Import tempfile for the validation function
import tempfile