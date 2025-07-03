# ML Training Connection Issue Summary

## Problem
The ML training fails with "No initial game state received" due to multiple interconnected issues:

1. **Protocol Mismatch** (Critical):
   - Connection negotiates JSON protocol (`v1.json.spacetimedb`)
   - But sends binary frames instead of TEXT frames
   - Server rejects with error: `unknown tag 0x7b for sum type ClientMessage`
   - This prevents ALL communication with the server

2. **Empty Tables on Initial Connection**:
   - When ML training connects, server returns current state (which is empty)
   - Unlike the test script which connects to a server with existing game data
   - The ML training needs to wait for data AFTER calling enter_game

3. **Connection Pool Issues**:
   - ML training uses connection pool that creates binary protocol connections
   - Different code path than test scripts which work correctly

## Root Cause Analysis

### Working Path (test_ml_training_integration.py):
```
GameClient -> direct connection -> JSON protocol -> receives data
```

### Broken Path (ML training):
```
GameClient -> connection pool -> binary protocol mismatch -> connection fails
```

## Evidence from Logs

### Protocol Mismatch:
```
WARNING - Received TEXT frame with binary protocol - this may indicate protocol mismatch
WARNING - WebSocket connection closed: received 1011 (internal error) unknown tag 0x7b
```

### Connection Pool Creating Binary Protocol:
```
INFO:blackholio_client.connection.spacetimedb_connection:Sent binary subscription request (178 bytes) - frame type: BINARY
```

## Solution

The ML training needs to:

1. **Use direct connection without connection pool** (like the test script)
2. **Ensure JSON protocol is used consistently**
3. **Wait for transaction updates after enter_game to get game data**

## Implementation Steps

1. Modify ML training environment to bypass connection pool
2. Force JSON protocol in all connection paths
3. Add proper waiting mechanism for game data after enter_game
4. Handle the case where initial subscription returns empty tables

## Temporary Workaround

Until the connection pool is fixed, ML training should create direct connections like:
```python
client = GameClient("localhost:3000", "blackholio")
# Don't use connection manager/pool
await client.connect()  # Direct connection
```