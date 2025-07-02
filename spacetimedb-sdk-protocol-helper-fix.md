# SpacetimeDB Python SDK Protocol Helper Fix

## Issue Summary

The `SpacetimeDBProtocolHelper` in the SpacetimeDB Python SDK has a fundamental flaw where it always returns `bytes` regardless of the `use_binary` parameter setting. This causes WebSocket frame type mismatches when clients attempt to use the JSON protocol (`v1.json.spacetimedb`), leading to binary frames being sent when text frames are expected.

## Context: blackholio-python-client Issue

The blackholio-python-client project has been experiencing protocol mismatch warnings from SpacetimeDB servers:
- Client negotiates JSON protocol (`v1.json.spacetimedb`) successfully
- Client sends binary WebSocket frames instead of text frames
- Server logs show: "Received TEXT frame with binary protocol" warnings
- Connection works but generates protocol mismatches and inefficiencies

## Root Cause Analysis

### Current SDK Implementation Problem

**File:** `/src/spacetimedb_sdk/protocol_helpers.py`

**Issue:** All encoding methods always return `bytes`, even when `use_binary=False`:

```python
# Lines around 46-47
self.use_binary = use_binary
self.encoder = ProtocolEncoder(use_binary=use_binary)

# Lines 56-57 - Subprotocol selection works correctly
def get_subprotocol(self) -> str:
    return BIN_PROTOCOL if self.use_binary else TEXT_PROTOCOL
    # TEXT_PROTOCOL = "v1.json.spacetimedb" ✅
    # BIN_PROTOCOL = "v1.bsatn.spacetimedb" ✅

# BUT encoding methods always return bytes ❌
def encode_subscription(self, tables: List[str]) -> bytes:  # Should be Union[bytes, str]
def encode_reducer_call(self, reducer: str, args: Dict[str, Any]) -> bytes:  # Should be Union[bytes, str]
```

**The Core Problem in ProtocolEncoder (lines 585-675):**
```python
def _encode_json(self, message: ClientMessage) -> bytes:
    # ... creates proper JSON structure ...
    data = {"CallReducer": {...}}  # Correct JSON format
    return json.dumps(data).encode('utf-8')  # ❌ Always returns bytes!
```

**Expected Behavior for JSON Protocol:**
```python
def _encode_json(self, message: ClientMessage) -> str:
    # ... creates proper JSON structure ...
    data = {"CallReducer": {...}}
    return json.dumps(data)  # ✅ Should return str for text frames
```

## Required Fixes

### 1. Fix Protocol Helper Return Types

**File:** `/src/spacetimedb_sdk/protocol_helpers.py`

Update method signatures to return proper types based on protocol:

```python
from typing import Union

class SpacetimeDBProtocolHelper:
    def encode_subscription(self, tables: List[str]) -> Union[bytes, str]:
        """Encode subscription message in the configured protocol format."""
        if self.use_binary:
            return self._encode_binary_subscription(tables)
        else:
            return self._encode_json_subscription(tables)
    
    def encode_reducer_call(self, reducer: str, args: Dict[str, Any]) -> Union[bytes, str]:
        """Encode reducer call in the configured protocol format."""
        if self.use_binary:
            return self._encode_binary_reducer_call(reducer, args)
        else:
            return self._encode_json_reducer_call(reducer, args)
    
    def encode_single_subscription(self, table: str) -> Union[bytes, str]:
        """Encode single table subscription in the configured protocol format."""
        if self.use_binary:
            return self._encode_binary_single_subscription(table)
        else:
            return self._encode_json_single_subscription(table)
    
    def encode_one_off_query(self, query: str) -> Union[bytes, str]:
        """Encode one-off query in the configured protocol format."""
        if self.use_binary:
            return self._encode_binary_query(query)
        else:
            return self._encode_json_query(query)
```

### 2. Fix ProtocolEncoder Implementation

**File:** `/src/spacetimedb_sdk/protocol_helpers.py` (ProtocolEncoder class)

Split the encoding logic to return proper types:

```python
class ProtocolEncoder:
    def encode_client_message(self, message: ClientMessage) -> Union[bytes, str]:
        """Encode message in the configured protocol format."""
        if self.use_binary:
            return self._encode_bsatn(message)  # Returns bytes
        else:
            return self._encode_json_string(message)  # Returns str
    
    def _encode_json_string(self, message: ClientMessage) -> str:
        """Encode message as JSON string for text frames."""
        # ... existing JSON encoding logic ...
        if isinstance(message, Subscribe):
            data = {
                "Subscribe": {
                    "table_updates": [{"table_name": table} for table in message.table_names]
                }
            }
        elif isinstance(message, CallReducer):
            data = {
                "CallReducer": {
                    "reducer": message.reducer,
                    "args": message.args.decode('utf-8') if isinstance(message.args, bytes) else message.args,
                    "request_id": message.request_id,
                    "flags": message.flags.value
                }
            }
        # ... other message types ...
        
        return json.dumps(data)  # ✅ Return str, not bytes
    
    def _encode_bsatn(self, message: ClientMessage) -> bytes:
        """Encode message as BSATN bytes for binary frames."""
        # ... existing binary encoding logic unchanged ...
        return encoded_bytes
```

### 3. Add Protocol Validation

Add validation to ensure protocol consistency:

```python
def validate_protocol_consistency(self) -> None:
    """Validate that protocol configuration is consistent."""
    subprotocol = self.get_subprotocol()
    
    if self.use_binary and "json" in subprotocol:
        raise ValueError(f"Protocol mismatch: use_binary=True but subprotocol is {subprotocol}")
    
    if not self.use_binary and "bsatn" in subprotocol:
        raise ValueError(f"Protocol mismatch: use_binary=False but subprotocol is {subprotocol}")

def get_expected_frame_type(self) -> str:
    """Get the expected WebSocket frame type for this protocol."""
    return "BINARY" if self.use_binary else "TEXT"
```

### 4. Update Helper Methods

Create protocol-specific helper methods:

```python
def _encode_json_subscription(self, tables: List[str]) -> str:
    """Create JSON subscription message."""
    message = Subscribe(table_names=tables)
    return self.encoder._encode_json_string(message)

def _encode_binary_subscription(self, tables: List[str]) -> bytes:
    """Create binary subscription message."""
    message = Subscribe(table_names=tables)
    return self.encoder._encode_bsatn(message)

def _encode_json_reducer_call(self, reducer: str, args: Dict[str, Any]) -> str:
    """Create JSON reducer call message."""
    message = CallReducer(
        reducer=reducer,
        args=json.dumps(args).encode('utf-8'),
        request_id=None,
        flags=RequestFlags.NONE
    )
    return self.encoder._encode_json_string(message)

def _encode_binary_reducer_call(self, reducer: str, args: Dict[str, Any]) -> bytes:
    """Create binary reducer call message."""
    message = CallReducer(
        reducer=reducer,
        args=json.dumps(args).encode('utf-8'),
        request_id=None,
        flags=RequestFlags.NONE
    )
    return self.encoder._encode_bsatn(message)
```

## Testing Requirements

### 1. Unit Tests for Protocol Consistency

```python
def test_json_protocol_returns_string():
    """Test that JSON protocol returns strings for text frames."""
    helper = SpacetimeDBProtocolHelper(use_binary=False)
    
    # Test subscription
    result = helper.encode_subscription(["test_table"])
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    
    # Test reducer call
    result = helper.encode_reducer_call("test_reducer", {"arg": "value"})
    assert isinstance(result, str), f"Expected str, got {type(result)}"

def test_binary_protocol_returns_bytes():
    """Test that binary protocol returns bytes for binary frames."""
    helper = SpacetimeDBProtocolHelper(use_binary=True)
    
    # Test subscription
    result = helper.encode_subscription(["test_table"])
    assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"
    
    # Test reducer call
    result = helper.encode_reducer_call("test_reducer", {"arg": "value"})
    assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"

def test_protocol_subprotocol_consistency():
    """Test that protocol setting matches subprotocol."""
    # JSON protocol
    helper = SpacetimeDBProtocolHelper(use_binary=False)
    assert helper.get_subprotocol() == "v1.json.spacetimedb"
    assert helper.get_expected_frame_type() == "TEXT"
    
    # Binary protocol
    helper = SpacetimeDBProtocolHelper(use_binary=True)
    assert helper.get_subprotocol() == "v1.bsatn.spacetimedb"
    assert helper.get_expected_frame_type() == "BINARY"
```

### 2. Integration Tests with WebSocket Frames

```python
async def test_websocket_frame_types():
    """Test that correct WebSocket frame types are used."""
    # JSON protocol should send text frames
    json_helper = SpacetimeDBProtocolHelper(use_binary=False)
    json_message = json_helper.encode_subscription(["test"])
    
    # Simulate websocket send
    if isinstance(json_message, str):
        frame_type = "TEXT"
    elif isinstance(json_message, bytes):
        frame_type = "BINARY"
    
    assert frame_type == "TEXT", f"JSON protocol should use TEXT frames, got {frame_type}"
    
    # Binary protocol should send binary frames
    binary_helper = SpacetimeDBProtocolHelper(use_binary=True)
    binary_message = binary_helper.encode_subscription(["test"])
    
    if isinstance(binary_message, str):
        frame_type = "TEXT"
    elif isinstance(binary_message, bytes):
        frame_type = "BINARY"
    
    assert frame_type == "BINARY", f"Binary protocol should use BINARY frames, got {frame_type}"
```

## Documentation Updates

### 1. Update Protocol Usage Examples

```python
# Example: Using JSON Protocol (Text Frames)
helper = SpacetimeDBProtocolHelper(use_binary=False)
subprotocol = helper.get_subprotocol()  # "v1.json.spacetimedb"
message = helper.encode_subscription(["players", "entities"])  # Returns str
await websocket.send(message)  # Sends TEXT frame

# Example: Using Binary Protocol (Binary Frames)  
helper = SpacetimeDBProtocolHelper(use_binary=True)
subprotocol = helper.get_subprotocol()  # "v1.bsatn.spacetimedb"
message = helper.encode_subscription(["players", "entities"])  # Returns bytes
await websocket.send(message)  # Sends BINARY frame
```

### 2. Add Protocol Selection Guidelines

```markdown
## Protocol Selection Guidelines

### JSON Protocol (`v1.json.spacetimedb`)
- **Use Case**: Debugging, development, human-readable logs
- **Performance**: Higher bandwidth usage, slower parsing
- **Frame Type**: TEXT frames (strings)
- **Configuration**: `SpacetimeDBProtocolHelper(use_binary=False)`

### Binary Protocol (`v1.bsatn.spacetimedb`)
- **Use Case**: Production, high-performance applications
- **Performance**: Lower bandwidth usage, faster parsing
- **Frame Type**: BINARY frames (bytes)
- **Configuration**: `SpacetimeDBProtocolHelper(use_binary=True)`

### Protocol Consistency Rules
1. Always match `use_binary` setting with appropriate subprotocol
2. Ensure WebSocket frame type matches protocol choice
3. Use validation methods to catch configuration errors
```

## Backwards Compatibility

### Maintaining Existing API

Ensure existing code continues to work:

```python
# Existing code that uses default behavior
helper = SpacetimeDBProtocolHelper()  # Defaults to use_binary=True
message = helper.encode_subscription(["test"])  # Still returns bytes
# ✅ No breaking changes for existing binary protocol users

# New capability for JSON protocol
helper = SpacetimeDBProtocolHelper(use_binary=False)
message = helper.encode_subscription(["test"])  # Now returns str
# ✅ Enables proper JSON protocol usage
```

## Performance Considerations

### JSON Protocol Optimization

When implementing JSON protocol:
- Use efficient JSON serialization
- Consider message size implications
- Maintain streaming capabilities for large messages
- Ensure UTF-8 encoding is handled properly

### Binary Protocol Preservation

Ensure binary protocol performance isn't affected:
- Keep existing BSATN encoding optimizations
- Maintain zero-copy operations where possible
- Preserve compression capabilities

## Expected Outcomes

After implementing these fixes:

1. **For blackholio-python-client:**
   - Can choose JSON protocol without frame type mismatches
   - No more "Received TEXT frame with binary protocol" warnings
   - Proper protocol negotiation end-to-end

2. **For all SDK users:**
   - Clear protocol selection with proper frame types
   - Better debugging with JSON protocol option
   - Maintained performance with binary protocol
   - Proper WebSocket standards compliance

3. **For SDK maintainability:**
   - Clear separation between protocol types
   - Better error messages for configuration issues
   - Comprehensive test coverage for both protocols
   - Future-proof protocol extension capabilities

## Priority and Impact

- **Priority**: High - Affects all users of JSON protocol
- **Impact**: Medium - Enables proper protocol choice, fixes standards compliance
- **Effort**: Medium - Requires careful refactoring but clear scope
- **Risk**: Low - Backwards compatible, well-tested changes

This fix will enable the blackholio-python-client to use either protocol correctly and eliminate the underlying SDK issue that forces workarounds in client applications.