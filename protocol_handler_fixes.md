# Protocol Handler Fixes for DatabaseUpdate AttributeError

## Problem
The `_handle_database_update` method in `protocol_handlers.py` was causing an AttributeError: `'DatabaseUpdate' object has no attribute 'get'`. This occurred because the method was expecting a dictionary but sometimes received a DatabaseUpdate object directly.

## Root Cause
The SpacetimeDB SDK can decode messages in different formats:
1. As dictionaries (JSON format)
2. As objects (when using enhanced protocol decoders)

The protocol handlers were only designed to handle dictionary format, using `.get()` method calls that don't exist on objects.

## Solution
Updated all message handler methods in `V112ProtocolHandler` to handle both dictionary and object formats:

### Methods Updated:
1. `_handle_database_update()` - Primary fix for the reported error
2. `_handle_identity_token()` - Handle IdentityToken objects
3. `_handle_transaction_commit()` - Handle TransactionCommit objects
4. `_handle_subscription_update()` - Handle SubscriptionUpdate objects
5. `_handle_error()` - Handle Error objects
6. `_handle_connected()` - Handle Connected objects
7. `_handle_disconnected()` - Handle Disconnected objects
8. `_handle_unknown_message()` - Handle any object type gracefully

### Pattern Applied:
Each handler now follows this pattern:
1. Check if data is an object with the expected class name
2. Check if data is a dictionary with a 'data' key containing the object
3. Fall back to original dictionary handling
4. Provide error handling for unexpected data types

### Key Changes:
- Added object detection using `hasattr(data, '__class__')`
- Used `getattr()` instead of `.get()` for object attribute access
- Added fallback handling for unexpected data types
- Enhanced error logging for debugging

## Files Modified:
- `/Users/punk1290/git/blackholio-python-client/src/blackholio_client/connection/protocol_handlers.py`

## Benefits:
- Eliminates AttributeError for DatabaseUpdate and other SpacetimeDB message objects
- Maintains backward compatibility with dictionary format
- Improves robustness of protocol handling
- Better error reporting and debugging capabilities
- Consistent handling across all message types

## Testing:
- File compiles successfully with Python
- All handlers now support both object and dictionary formats
- Graceful degradation for unexpected data types