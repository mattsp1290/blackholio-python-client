# Subscription Callback Fix Implementation

## Problem Summary
The blackholio-python-client was experiencing a critical timing issue where SpacetimeDB events (`IdentityToken` and `DatabaseUpdate`) were firing before event callbacks were registered, resulting in:
- Events showing "0 callbacks" in logs
- Empty player/entity lists after connection
- ML training failures due to missing game state

## Root Cause
The connection process was:
1. Establishing WebSocket connection
2. Server immediately sending `IdentityToken` and `InitialSubscription` events
3. Client registering callbacks AFTER these events were already processed
4. Result: Critical initial data was lost

## Solution Implemented

### Key Changes in `src/blackholio_client/client.py`:

1. **Direct Connection Creation** (lines 170-192):
   - Create `SpacetimeDBConnection` object directly before connecting
   - Register event handlers on the connection object BEFORE calling `connect()`
   - This ensures callbacks are ready when the server sends initial events

2. **Early Event Handler Registration** (lines 730-749):
   - New `_register_early_event_handlers()` method
   - Registers handlers for critical events:
     - `initial_subscription` - Initial game state data
     - `transaction_update` - Game state updates
     - `identity_token` - Authentication data
     - `raw_message` - Debug fallback

3. **Stored Subscription Data Processing** (lines 744-749):
   - The connection stores `InitialSubscription` data when received
   - Client checks for stored data after connection completes
   - Processes any data that arrived before handlers were fully set up

### Key Changes in `src/blackholio_client/connection/spacetimedb_connection.py`:

1. **Data Storage** (line 135):
   - Added `_last_initial_subscription` field to store initial data

2. **Event Storage** (lines 897-899):
   - When `InitialSubscription` arrives, it's stored for later retrieval
   - This handles cases where data arrives between connection and handler setup

## Testing

### Test Script (`test_callback_fix.py`):
```python
# Connects to server
# Verifies callbacks are registered before events fire
# Checks that initial data is received
# Joins game and verifies player/entity data flows
```

### Running the Test:
```bash
# Make sure Blackholio server is running on localhost:3000
./run_fix_test.sh
```

### Expected Results:
- ✅ Events show "1+ callbacks" instead of "0 callbacks"
- ✅ No timeout waiting for subscription data
- ✅ `get_all_players()` returns data immediately after connection
- ✅ `get_all_entities()` returns data after joining game
- ✅ ML training can proceed without "No initial game state" errors

## Verification for ML Training

After implementing this fix, the ML training should work:

```bash
cd ../blackholio-agent
python scripts/train_agent.py --total-timesteps 100 --n-envs 1
```

The training should now:
- Connect successfully
- Receive initial game state
- Not show "Episode is done. Call reset()" errors
- Proceed with actual training steps

## Technical Details

The fix follows "Option 1" from the original issue document - registering callbacks before connection. This is the cleanest approach that ensures no events are missed.

The implementation maintains backward compatibility while fixing the critical timing issue that was blocking ML training.