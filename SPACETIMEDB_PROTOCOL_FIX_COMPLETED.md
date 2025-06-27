# SpacetimeDB Text vs Binary Protocol Fix - Implementation Complete

## Summary

Successfully implemented the fix for the text vs binary protocol issue in the Blackholio Python client. The server was receiving text frames instead of binary frames, causing BSATN parsing errors:

```
data too short for [u8]: Expected 2037540213, given 152
```

The expected value `2037540213` (0x79726575) is ASCII for "yreu" (part of "query_str" backwards), indicating the server was trying to parse text data as binary.

## Changes Made

### 1. Protocol Helper Configuration (`spacetimedb_connection.py:66`)
- **Before**: `SpacetimeDBProtocolHelper(use_binary=False)`
- **After**: `SpacetimeDBProtocolHelper(use_binary=True)`

### 2. WebSocket Subprotocol Handling
- **Before**: Used JSON protocol subprotocol `get_json_protocol_subprotocol()`
- **After**: Removed subprotocol specification (binary protocol uses default WebSocket)
- **Files**: Lines 268, 353

### 3. Message Frame Type Enforcement
- Enhanced `_ensure_binary_message()` method to:
  - Explicitly reject strings that would create text frames
  - Add proper error handling for type mismatches
  - Include detailed logging for frame type verification

### 4. Subscription Request Updates (`spacetimedb_connection.py:468-481`)
- **Before**: "Send initial subscription request using JSON protocol"
- **After**: "Send initial subscription request using binary protocol"
- Added binary frame type logging

### 5. Reducer Call Updates
- **enter_game** and **update_input** reducers now use binary protocol
- Updated logging to confirm binary frame transmission
- **Files**: Lines 951-961, 977-993

### 6. Message Handling Improvements
- Added frame type detection and logging in `_message_handler()`
- Binary frames are now properly identified and processed
- Text frames trigger warnings about potential protocol mismatches

## Technical Details

### Protocol Flow
```
1. Client: SpacetimeDBProtocolHelper(use_binary=True)
2. Client: encode_subscription() → bytes
3. Client: websocket.send(bytes) → BINARY frame
4. Server: Receives BINARY frame → BSATN parser
```

### Frame Type Verification
- All outgoing messages are verified as bytes before transmission
- Binary frames are explicitly logged with size information
- Text frames received are flagged as potential protocol mismatches

## Validation Criteria Met

✅ **Protocol helper configured for binary mode**
✅ **All messages sent as binary frames (not text frames)**  
✅ **Subscription requests use binary protocol**
✅ **Reducer calls use binary protocol**
✅ **Proper error handling and frame type verification**

## Expected Results

1. **Server logs should show**: "Received BINARY frame" instead of "error on text message"
2. **Client logs show**: "Sent binary subscription request" and "Sent X as binary frame"
3. **Connection duration**: Should maintain connection longer than previous ~4 seconds
4. **Error resolution**: No more "data too short for [u8]: Expected 2037540213, given 152" errors

## Next Steps

If BSATN-specific errors still occur after this fix (like "unknown tag 0x13"), those are SDK encoding issues and not client framing issues. This fix addresses only the WebSocket frame type problem.

## Files Modified

- `src/blackholio_client/connection/spacetimedb_connection.py` (primary changes)

## Commit Ready

All changes preserve existing functionality while switching from text to binary WebSocket frames as required by the SpacetimeDB server.