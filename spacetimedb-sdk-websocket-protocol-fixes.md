# SpacetimeDB Python SDK WebSocket Protocol Improvements

## Context

The blackholio-python-client has been experiencing WebSocket connection failures with HTTP 400 errors when connecting to SpacetimeDB servers. Investigation revealed that the issue stems from missing or improperly specified WebSocket subprotocols in the connection handshake.

## Required SDK Improvements

### 1. Ensure Protocol Helpers Return Correct Values

**File:** `/src/spacetimedb_sdk/protocol_helpers.py`

Verify that the protocol helper functions return the correct protocol strings:
- `get_json_protocol_subprotocol()` should return `"v1.json.spacetimedb"`
- `get_binary_protocol_subprotocol()` should return `"v1.bsatn.spacetimedb"`

### 2. Add Default Protocol Configuration

**File:** `/src/spacetimedb_sdk/connection_builder.py`

Ensure the connection builder has sensible defaults:
```python
def __init__(self):
    # ... existing code ...
    self._protocol = "v1.json.spacetimedb"  # Default to JSON for compatibility
```

### 3. Improve Error Messages for Protocol Issues

**File:** `/src/spacetimedb_sdk/websocket_client.py`

When WebSocket handshake fails with HTTP 400, check if it's due to missing protocol headers and provide a more helpful error message:
```python
if response_code == 400 and "no valid protocol selected" in error_message:
    raise WebSocketException(
        "WebSocket handshake failed: No valid protocol specified. "
        "Please ensure you're using either 'v1.json.spacetimedb' or 'v1.bsatn.spacetimedb' as the subprotocol."
    )
```

### 4. Add Protocol Validation

**File:** `/src/spacetimedb_sdk/protocol.py`

Add a validation function to ensure only valid protocols are used:
```python
VALID_PROTOCOLS = ["v1.json.spacetimedb", "v1.bsatn.spacetimedb"]

def validate_protocol(protocol: str) -> bool:
    """Validate that the protocol string is supported by SpacetimeDB."""
    return protocol in VALID_PROTOCOLS
```

### 5. Update Documentation

**File:** `/src/spacetimedb_sdk/README.md` or relevant documentation

Add clear documentation about:
- The two supported protocols and their differences
- How to specify the protocol when creating connections
- Common protocol-related errors and their solutions

Example:
```markdown
## WebSocket Protocols

SpacetimeDB supports two WebSocket subprotocols:

1. **JSON Protocol** (`v1.json.spacetimedb`): 
   - Human-readable format
   - Easier debugging
   - Higher bandwidth usage
   - Default choice for development

2. **Binary Protocol** (`v1.bsatn.spacetimedb`):
   - Efficient binary encoding
   - Lower bandwidth usage
   - Better performance
   - Recommended for production

### Specifying Protocol

```python
# Using JSON protocol (default)
builder = SpacetimeDBConnectionBuilder()
    .with_host("localhost:3000")
    .with_database("mydb")
    .with_protocol("v1.json.spacetimedb")

# Using binary protocol
builder = SpacetimeDBConnectionBuilder()
    .with_host("localhost:3000")
    .with_database("mydb")
    .with_protocol("v1.bsatn.spacetimedb")
```
```

### 6. Add Connection Test Utilities

**File:** `/src/spacetimedb_sdk/connection_diagnostics.py`

Add a method to test protocol negotiation:
```python
async def test_protocol_negotiation(host: str, database: str, protocol: str) -> dict:
    """Test WebSocket protocol negotiation with the server."""
    try:
        # Attempt connection with specified protocol
        # Return detailed diagnostics about the handshake
        pass
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "protocol_used": protocol,
            "recommendation": "Try using 'v1.json.spacetimedb' if binary protocol fails"
        }
```

### 7. Ensure Binary Frame Handling

**File:** `/src/spacetimedb_sdk/websocket_client.py`

Verify that when using binary protocol (`v1.bsatn.spacetimedb`), messages are sent with the correct opcode:
```python
if self.protocol == "v1.bsatn.spacetimedb":
    # Must use OPCODE_BINARY for binary protocol
    self.ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
else:
    # JSON protocol uses text frames (default)
    self.ws.send(data)
```

## Testing Requirements

1. **Unit Tests**: Add tests for protocol validation and helper functions
2. **Integration Tests**: Test actual connections with both protocols
3. **Error Case Tests**: Verify proper error messages when protocol is missing or invalid

## Expected Outcomes

After implementing these improvements:
1. Clearer error messages when protocol issues occur
2. Better default behavior that works out of the box
3. Comprehensive documentation for protocol usage
4. Diagnostic tools to help debug connection issues
5. Robust handling of both JSON and binary protocols

## Priority

**HIGH** - These improvements will prevent connection failures and improve the developer experience for all SDK users.