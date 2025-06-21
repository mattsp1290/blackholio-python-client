# Blackholio Python Client - API Reference

Complete API documentation for the Blackholio Python Client package.

## Table of Contents

- [Core Client API](#core-client-api)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Events System](#events-system)
- [Error Handling](#error-handling)
- [Utilities](#utilities)
- [Legacy Compatibility](#legacy-compatibility)

## Core Client API

### GameClient

The main unified client interface for interacting with SpacetimeDB servers.

```python
from blackholio_client import create_game_client, GameClient
```

#### Factory Function

```python
def create_game_client(
    host: str = None,
    database: str = "blackholio",
    server_language: str = "rust",
    auto_reconnect: bool = True,
    **kwargs
) -> GameClient
```

Creates a new GameClient instance with automatic configuration.

**Parameters:**
- `host` (str, optional): Server host and port (e.g., "localhost:3000")
- `database` (str): SpacetimeDB database name
- `server_language` (str): Server implementation ("rust", "python", "csharp", "go")
- `auto_reconnect` (bool): Enable automatic reconnection
- `**kwargs`: Additional configuration options

**Returns:** GameClient instance

**Example:**
```python
# Basic usage
client = create_game_client()

# Custom configuration
client = create_game_client(
    host="production-server.com:443",
    database="blackholio_prod",
    server_language="rust",
    auto_reconnect=True
)
```

#### Connection Methods

##### `async connect() -> bool`

Establishes connection to the SpacetimeDB server.

**Returns:** True if connection successful, False otherwise

**Example:**
```python
success = await client.connect()
if success:
    print("Connected successfully!")
```

##### `async disconnect() -> None`

Gracefully disconnects from the server.

**Example:**
```python
await client.disconnect()
```

##### `async reconnect() -> bool`

Attempts to reconnect to the server.

**Returns:** True if reconnection successful

##### `is_connected() -> bool`

Check current connection status.

**Returns:** True if connected

#### Game Operations

##### `async join_game(player_name: str) -> bool`

Joins the game with specified player name. This handles connection, subscription, and game entry.

**Parameters:**
- `player_name` (str): Name for the player

**Returns:** True if successfully joined

**Example:**
```python
success = await client.join_game("MyPlayer")
if success:
    print("Joined game successfully!")
```

##### `async leave_game() -> None`

Leaves the current game session.

##### `is_in_game() -> bool`

Check if currently in a game.

**Returns:** True if in game

##### `async move_player(direction: Vector2) -> bool`

Moves the player in the specified direction.

**Parameters:**
- `direction` (Vector2): Movement direction vector

**Returns:** True if move command sent successfully

**Example:**
```python
from blackholio_client import Vector2

# Move right
await client.move_player(Vector2(1.0, 0.0))

# Move diagonally
await client.move_player(Vector2(0.7, 0.7))
```

##### `async player_split() -> bool`

Attempts to split the player's entities.

**Returns:** True if split command sent successfully

#### Data Access Methods

##### `get_local_player() -> GamePlayer | None`

Get the local player object.

**Returns:** GamePlayer instance or None if not in game

##### `get_local_player_entities() -> Dict[str, GameEntity]`

Get all entities belonging to the local player.

**Returns:** Dictionary mapping entity IDs to GameEntity objects

##### `get_all_entities() -> Dict[str, GameEntity]`

Get all entities in the game.

**Returns:** Dictionary mapping entity IDs to GameEntity objects

##### `get_all_players() -> Dict[str, GamePlayer]`

Get all players in the game.

**Returns:** Dictionary mapping player IDs to GamePlayer objects

##### `get_entities_near(position: Vector2, radius: float) -> List[GameEntity]`

Get entities within specified radius of a position.

**Parameters:**
- `position` (Vector2): Center position
- `radius` (float): Search radius

**Returns:** List of nearby GameEntity objects

#### Event Handlers

##### `on_connection_state_changed(callback: Callable[[ConnectionState], None]) -> None`

Register callback for connection state changes.

**Example:**
```python
def handle_connection_change(state):
    print(f"Connection state: {state.value}")

client.on_connection_state_changed(handle_connection_change)
```

##### `on_player_joined(callback: Callable[[GamePlayer], None]) -> None`

Register callback for player join events.

##### `on_player_left(callback: Callable[[GamePlayer], None]) -> None`

Register callback for player leave events.

##### `on_entity_created(callback: Callable[[GameEntity], None]) -> None`

Register callback for entity creation events.

##### `on_entity_updated(callback: Callable[[GameEntity, GameEntity], None]) -> None`

Register callback for entity update events. Receives old and new entity states.

##### `on_entity_destroyed(callback: Callable[[GameEntity], None]) -> None`

Register callback for entity destruction events.

##### `on_error(callback: Callable[[str], None]) -> None`

Register callback for error events.

#### Authentication

##### `async authenticate(credentials: Dict[str, Any]) -> bool`

Authenticate with the server.

**Parameters:**
- `credentials` (dict): Authentication credentials

**Returns:** True if authentication successful

##### `load_token() -> bool`

Load saved authentication token.

**Returns:** True if token loaded successfully

##### `save_token() -> bool`

Save current authentication token.

**Returns:** True if token saved successfully

##### `validate_token() -> bool`

Validate current authentication token.

**Returns:** True if token is valid

#### Monitoring and Statistics

##### `get_client_statistics() -> Dict[str, Any]`

Get comprehensive client statistics.

**Returns:** Dictionary with performance metrics

**Example:**
```python
stats = client.get_client_statistics()
print(f"Reducer calls: {stats['reducer_calls']}")
print(f"Messages sent: {stats['messages_sent']}")
```

##### `get_client_state() -> Dict[str, Any]`

Get current client state summary.

**Returns:** Dictionary with client state information

##### `get_debug_info() -> Dict[str, Any]`

Get detailed debugging information.

**Returns:** Dictionary with debug data

##### `export_state(filename: str) -> bool`

Export client state to file for analysis.

**Parameters:**
- `filename` (str): Output filename

**Returns:** True if export successful

#### Configuration

##### `get_connection_info() -> Dict[str, Any]`

Get current connection configuration.

**Returns:** Dictionary with connection details

##### `enable_auto_reconnect(max_attempts: int = 5, delay: float = 2.0, exponential_backoff: bool = True) -> None`

Configure automatic reconnection behavior.

**Parameters:**
- `max_attempts` (int): Maximum reconnection attempts
- `delay` (float): Initial delay between attempts
- `exponential_backoff` (bool): Use exponential backoff

##### `async shutdown() -> None`

Gracefully shutdown the client and cleanup resources.

## Data Models

### Vector2

2D vector with mathematical operations.

```python
from blackholio_client import Vector2

# Create vectors
v1 = Vector2(1.0, 2.0)
v2 = Vector2(3.0, 4.0)

# Mathematical operations
result = v1 + v2        # Addition
result = v1 - v2        # Subtraction
result = v1 * 2.0       # Scalar multiplication
result = v1.dot(v2)     # Dot product
result = v1.cross(v2)   # Cross product

# Properties
length = v1.magnitude()
unit = v1.normalized()
distance = v1.distance_to(v2)
```

#### Properties

- `x: float` - X component
- `y: float` - Y component

#### Methods

- `magnitude() -> float` - Vector length
- `normalized() -> Vector2` - Unit vector
- `distance_to(other: Vector2) -> float` - Distance to another vector
- `dot(other: Vector2) -> float` - Dot product
- `cross(other: Vector2) -> float` - Cross product (scalar in 2D)
- `lerp(other: Vector2, t: float) -> Vector2` - Linear interpolation
- `rotate(angle: float) -> Vector2` - Rotate by angle (radians)

### GameEntity

Base class for all game entities.

```python
from blackholio_client import GameEntity

entity = GameEntity(
    entity_id="entity_123",
    position=Vector2(100.0, 200.0),
    velocity=Vector2(10.0, -5.0),
    mass=50.0,
    radius=25.0
)
```

#### Properties

- `entity_id: str` - Unique entity identifier
- `position: Vector2` - Current position
- `velocity: Vector2` - Current velocity
- `mass: float` - Entity mass
- `radius: float` - Entity radius
- `entity_type: EntityType` - Type of entity
- `created_at: datetime` - Creation timestamp

#### Methods

- `calculated_radius() -> float` - Calculate radius based on mass
- `collides_with(other: GameEntity) -> bool` - Check collision
- `distance_to(other: GameEntity) -> float` - Distance to another entity
- `to_dict() -> Dict` - Convert to dictionary
- `from_dict(data: Dict) -> GameEntity` - Create from dictionary

### GamePlayer

Player-specific entity with additional properties.

```python
from blackholio_client import GamePlayer

player = GamePlayer(
    entity_id="player_123",
    player_id="player_123",
    name="TestPlayer",
    position=Vector2(0.0, 0.0),
    score=1500,
    state=PlayerState.ACTIVE
)
```

#### Additional Properties

- `player_id: str` - Player identifier
- `name: str` - Player name
- `score: int` - Player score
- `state: PlayerState` - Player state (ACTIVE, INACTIVE, etc.)

### GameCircle

Food/collectible entities in the game.

```python
from blackholio_client import GameCircle

circle = GameCircle(
    entity_id="circle_123",
    position=Vector2(50.0, 75.0),
    mass=10.0,
    color="#FF0000"
)
```

#### Additional Properties

- `color: str` - Circle color (hex format)
- `is_food: bool` - Whether this is a food item

## Configuration

### EnvironmentConfig

Environment variable configuration management.

```python
from blackholio_client import EnvironmentConfig

# Get current configuration
config = EnvironmentConfig()

# Access configuration values
print(f"Server Language: {config.server_language}")
print(f"Server IP: {config.server_ip}")
print(f"Server Port: {config.server_port}")
```

#### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SERVER_LANGUAGE` | str | "rust" | Server implementation (rust, python, csharp, go) |
| `SERVER_IP` | str | "localhost" | Server IP address |
| `SERVER_PORT` | int | 3000 | Server port number |
| `SERVER_USE_SSL` | bool | false | Use SSL/TLS encryption |
| `SPACETIME_DB_IDENTITY` | str | "blackholio" | Database identity |
| `CONNECTION_TIMEOUT` | float | 30.0 | Connection timeout in seconds |
| `RECONNECT_ATTEMPTS` | int | 5 | Maximum reconnection attempts |
| `RECONNECT_DELAY` | float | 2.0 | Delay between reconnection attempts |
| `LOG_LEVEL` | str | "INFO" | Logging level |
| `DEBUG_MODE` | bool | false | Enable debug mode |

## Events System

### Event Types

The client provides a comprehensive event system for handling game and connection events.

#### Game Events

```python
from blackholio_client import (
    PlayerJoinedEvent, PlayerLeftEvent,
    EntityCreatedEvent, EntityUpdatedEvent, EntityDestroyedEvent,
    GameStateChangedEvent, PlayerMovedEvent
)

# Using the global event manager
from blackholio_client import get_global_event_manager

event_manager = get_global_event_manager()

def handle_player_joined(event):
    print(f"Player {event.player_name} joined!")

# Subscribe to events
event_manager.subscribe("PlayerJoined", handle_player_joined)
```

#### Connection Events

```python
from blackholio_client import (
    ConnectionEstablishedEvent, ConnectionLostEvent,
    SubscriptionStateChangedEvent, AuthenticationEvent
)

def handle_connection_lost(event):
    print(f"Connection lost: {event.reason}")
    # Handle reconnection logic

event_manager.subscribe("ConnectionLost", handle_connection_lost)
```

### Event Subscribers

#### CallbackEventSubscriber

Simple callback-based event subscriber.

```python
from blackholio_client import CallbackEventSubscriber

def my_callback(event):
    print(f"Received event: {event.get_event_name()}")

subscriber = CallbackEventSubscriber("MySubscriber", my_callback)
event_manager.add_subscriber(subscriber)
```

### Event Publishers

#### GameEventPublisher

Publishes game-related events.

```python
from blackholio_client import GameEventPublisher, PlayerJoinedEvent

publisher = GameEventPublisher()
event = PlayerJoinedEvent(
    player_id="player_123",
    player_name="TestPlayer",
    timestamp=datetime.now()
)
await publisher.publish(event)
```

## Error Handling

### Exception Hierarchy

```python
from blackholio_client import (
    BlackholioConnectionError,
    BlackholioConfigurationError,
    ServerConfigurationError,
    SpacetimeDBError
)

try:
    client = create_game_client()
    await client.connect()
except BlackholioConnectionError as e:
    print(f"Connection error: {e}")
except BlackholioConfigurationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Error Recovery

```python
from blackholio_client.utils.error_handling import RetryManager, CircuitBreaker

# Retry with exponential backoff
retry_manager = RetryManager(
    max_attempts=5,
    backoff_strategy="exponential",
    base_delay=1.0
)

async def risky_operation():
    # Some operation that might fail
    pass

result = await retry_manager.execute(risky_operation)
```

## Utilities

### Physics Calculations

```python
from blackholio_client.models.physics import (
    calculate_center_of_mass,
    find_collisions,
    calculate_movement_physics
)

# Calculate center of mass for entities
entities = client.get_local_player_entities()
center = calculate_center_of_mass(list(entities.values()))

# Find collisions
collisions = find_collisions(entities.values())
```

### Data Conversion

```python
from blackholio_client.models.data_converters import (
    EntityConverter,
    PlayerConverter,
    convert_spacetime_data
)

# Convert raw SpacetimeDB data
converter = EntityConverter()
entity = converter.from_spacetime_data(raw_data)
```

### Debugging

```python
from blackholio_client.utils.debugging import (
    DebugCapture,
    PerformanceProfiler,
    ErrorReporter
)

# Capture debug information
debug_capture = DebugCapture()
with debug_capture.capture_context():
    # Code to debug
    await client.move_player(Vector2(1.0, 0.0))

# Get captured information
debug_info = debug_capture.get_captured_data()
```

## Legacy Compatibility

For backward compatibility with existing blackholio-agent and client-pygame code:

### Legacy Client

```python
from blackholio_client import BlackholioClient

# Legacy style (still supported)
client = BlackholioClient()
await client.connect()
await client.enter_game("PlayerName")

# Get legacy-style data access
entities = client.get_entities()
players = client.get_players()
```

### Migration Helpers

```python
# Legacy function compatibility
from blackholio_client.legacy import (
    get_legacy_connection,
    convert_legacy_config,
    wrap_legacy_callbacks
)

# Convert old configuration
old_config = {"host": "localhost:3000", "db": "blackholio"}
new_client = convert_legacy_config(old_config)
```

## Best Practices

### Connection Management

```python
# Always use context managers or try/finally
async def proper_client_usage():
    client = create_game_client()
    try:
        await client.connect()
        await client.join_game("Player")
        # Game operations...
    finally:
        await client.shutdown()

# Or use as async context manager (if implemented)
async with create_game_client() as client:
    await client.join_game("Player")
    # Automatic cleanup
```

### Error Handling

```python
# Handle specific error types
try:
    await client.move_player(Vector2(1.0, 0.0))
except BlackholioConnectionError:
    # Handle connection issues
    await client.reconnect()
except Exception as e:
    # Handle other errors
    logger.error(f"Unexpected error: {e}")
```

### Performance Optimization

```python
# Use connection pooling for multiple clients
from blackholio_client.connection import get_connection_manager

connection_manager = get_connection_manager()

# Batch operations when possible
movements = [Vector2(1.0, 0.0), Vector2(0.0, 1.0)]
for movement in movements:
    await client.move_player(movement)
    await asyncio.sleep(0.1)  # Rate limiting
```

## Examples

See the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Basic client operations
- `migration_examples.py` - Migration from legacy implementations
- `environment_config_examples.py` - Environment configuration
- `event_system_examples.py` - Event handling patterns
- `data_models_examples.py` - Data model usage

## Support

For issues, questions, or contributions:

1. Check the [troubleshooting guide](TROUBLESHOOTING.md)
2. Review [existing examples](../src/blackholio_client/examples/)
3. Open an issue on GitHub
4. Consult the [development guide](../DEVELOPMENT.md)