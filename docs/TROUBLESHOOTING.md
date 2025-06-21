# Troubleshooting Guide - Blackholio Python Client

Complete troubleshooting guide for common issues, error resolution, and debugging techniques.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Connection Issues](#connection-issues)
- [Configuration Problems](#configuration-problems)
- [Server Language Issues](#server-language-issues)
- [Authentication Errors](#authentication-errors)
- [Performance Issues](#performance-issues)
- [Environment Variables](#environment-variables)
- [Docker Issues](#docker-issues)
- [Migration Problems](#migration-problems)
- [Debug Tools](#debug-tools)
- [FAQ](#faq)

## Quick Diagnostics

### Health Check Script

First, run this diagnostic script to identify common issues:

```python
import asyncio
import os
from blackholio_client import create_game_client, EnvironmentConfig

async def health_check():
    """Comprehensive health check for the client."""
    print("🏥 Blackholio Client Health Check")
    print("=" * 40)
    
    # 1. Check environment configuration
    print("\n1. Environment Configuration:")
    try:
        config = EnvironmentConfig()
        print(f"✅ Server Language: {config.server_language}")
        print(f"✅ Server IP: {config.server_ip}")
        print(f"✅ Server Port: {config.server_port}")
        print(f"✅ SSL Enabled: {config.use_ssl}")
    except Exception as e:
        print(f"❌ Environment config error: {e}")
        return
    
    # 2. Test client creation
    print("\n2. Client Creation:")
    try:
        client = create_game_client()
        print("✅ Client created successfully")
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return
    
    # 3. Test connection
    print("\n3. Connection Test:")
    try:
        connected = await client.connect()
        if connected:
            print("✅ Connection successful")
            
            # 4. Test basic operations
            print("\n4. Basic Operations:")
            try:
                info = client.get_connection_info()
                print(f"✅ Connection info: {info}")
                
                stats = client.get_client_statistics()
                print(f"✅ Statistics available: {len(stats)} metrics")
                
            except Exception as e:
                print(f"❌ Basic operations failed: {e}")
        else:
            print("❌ Connection failed - server may not be running")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        await client.shutdown()
    
    print("\n🏥 Health check completed!")

# Run the health check
asyncio.run(health_check())
```

### Common Error Indicators

| Error Type | Symptoms | Quick Fix |
|------------|----------|-----------|
| Connection Failed | `ConnectionRefusedError`, timeout | Check server status, ports |
| Invalid Config | `ConfigurationError` | Verify environment variables |
| Auth Failed | `AuthenticationError` | Check credentials, tokens |
| Server Language | `UnsupportedServerError` | Verify server type, CLI |
| Protocol Mismatch | Data parsing errors | Check server version |

## Connection Issues

### Cannot Connect to Server

**Symptoms:**
- `ConnectionRefusedError`
- `TimeoutError`
- Connection hangs indefinitely

**Diagnosis:**
```python
import asyncio
from blackholio_client import create_game_client

async def diagnose_connection():
    client = create_game_client()
    
    # Test with verbose error handling
    try:
        print("Testing connection...")
        connected = await asyncio.wait_for(
            client.connect(), 
            timeout=10.0
        )
        print(f"Connection result: {connected}")
    except asyncio.TimeoutError:
        print("❌ Connection timed out - server may be down")
    except ConnectionRefusedError:
        print("❌ Connection refused - check server is running")
    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")
    finally:
        await client.shutdown()

asyncio.run(diagnose_connection())
```

**Solutions:**

1. **Check Server Status**
   ```bash
   # Test if server is reachable
   nc -zv localhost 3000
   
   # Check if SpacetimeDB is running
   ps aux | grep spacetime
   
   # Check server logs
   docker logs spacetime-server
   ```

2. **Verify Port Configuration**
   ```bash
   # Check what's running on the port
   lsof -i :3000
   
   # Test different ports
   export SERVER_PORT=3001
   ```

3. **Network Configuration**
   ```bash
   # For Docker environments
   docker network ls
   docker network inspect bridge
   
   # Check firewall
   sudo ufw status
   ```

### Connection Drops Frequently

**Symptoms:**
- Frequent `ConnectionLost` events
- Reconnection attempts failing
- Data not updating

**Solutions:**

1. **Enable Auto-Reconnect**
   ```python
   client = create_game_client(auto_reconnect=True)
   client.enable_auto_reconnect(
       max_attempts=10,
       delay=2.0,
       exponential_backoff=True
   )
   ```

2. **Adjust Timeouts**
   ```bash
   export CONNECTION_TIMEOUT=60.0
   export RECONNECT_DELAY=5.0
   export RECONNECT_ATTEMPTS=10
   ```

3. **Monitor Connection Health**
   ```python
   def on_connection_changed(state):
       print(f"Connection state: {state}")
       if state == ConnectionState.FAILED:
           print("Connection failed - investigating...")
   
   client.on_connection_state_changed(on_connection_changed)
   ```

### SSL/TLS Issues

**Symptoms:**
- SSL handshake failures
- Certificate verification errors
- "Protocol wrong type" errors

**Solutions:**

1. **Disable SSL for Testing**
   ```bash
   export SERVER_USE_SSL=false
   ```

2. **Configure SSL Properly**
   ```bash
   export SERVER_USE_SSL=true
   export SSL_CERT_PATH=/path/to/cert.pem
   export SSL_VERIFY=false  # For self-signed certs
   ```

3. **Test SSL Connection**
   ```bash
   openssl s_client -connect localhost:443 -servername localhost
   ```

## Configuration Problems

### Environment Variables Not Loading

**Symptoms:**
- Default values used instead of environment variables
- `ConfigurationError` exceptions
- Unexpected server selection

**Diagnosis:**
```python
import os
from blackholio_client import EnvironmentConfig

def diagnose_environment():
    print("Environment Variables Diagnosis:")
    print("=" * 40)
    
    # Check if variables are set
    env_vars = [
        'SERVER_LANGUAGE', 'SERVER_IP', 'SERVER_PORT',
        'SPACETIME_DB_IDENTITY', 'CONNECTION_TIMEOUT'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} = {value}")
        else:
            print(f"❌ {var} = NOT SET")
    
    # Test configuration loading
    try:
        config = EnvironmentConfig()
        print(f"\n✅ Configuration loaded successfully")
        print(f"Server: {config.server_language}://{config.server_ip}:{config.server_port}")
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")

diagnose_environment()
```

**Solutions:**

1. **Check Variable Export**
   ```bash
   # Verify variables are exported
   env | grep SERVER
   
   # Export missing variables
   export SERVER_LANGUAGE=rust
   export SERVER_IP=localhost
   export SERVER_PORT=3000
   ```

2. **Use .env File**
   ```bash
   # Create .env file
   cat > .env << EOF
   SERVER_LANGUAGE=rust
   SERVER_IP=localhost
   SERVER_PORT=3000
   SPACETIME_DB_IDENTITY=blackholio
   EOF
   
   # Load in Python
   from dotenv import load_dotenv
   load_dotenv()
   ```

3. **Explicit Configuration**
   ```python
   # Override environment in code
   client = create_game_client(
       host="localhost:3000",
       server_language="rust",
       database="blackholio"
   )
   ```

### Invalid Configuration Values

**Common Issues:**

1. **Invalid Server Language**
   ```bash
   # Valid options only
   export SERVER_LANGUAGE=rust    # ✅
   export SERVER_LANGUAGE=python  # ✅
   export SERVER_LANGUAGE=csharp  # ✅
   export SERVER_LANGUAGE=go      # ✅
   export SERVER_LANGUAGE=java    # ❌ Not supported
   ```

2. **Invalid Port Numbers**
   ```bash
   export SERVER_PORT=3000        # ✅
   export SERVER_PORT=abc         # ❌ Not a number
   export SERVER_PORT=99999       # ❌ Port out of range
   ```

3. **Invalid Timeout Values**
   ```bash
   export CONNECTION_TIMEOUT=30.0 # ✅
   export CONNECTION_TIMEOUT=-5   # ❌ Negative timeout
   export CONNECTION_TIMEOUT=xyz  # ❌ Not a number
   ```

## Server Language Issues

### SpacetimeDB CLI Not Found

**Symptoms:**
- `SpacetimeDBError: CLI not found`
- Client generation failures
- "spacetimedb command not found"

**Solutions:**

1. **Install SpacetimeDB CLI**
   ```bash
   # Install from releases
   curl -sSL https://github.com/clockworklabs/SpacetimeDB/releases/latest/download/install.sh | bash
   
   # Or build from source
   git clone https://github.com/clockworklabs/SpacetimeDB.git
   cd SpacetimeDB
   cargo build --release
   ```

2. **Set CLI Path**
   ```bash
   export SPACETIMEDB_CLI_PATH=/path/to/spacetimedb
   ```

3. **Verify CLI Installation**
   ```bash
   spacetimedb version
   spacetimedb help
   ```

### Server Implementation Not Found

**Symptoms:**
- `ServerNotFoundError`
- "No server found for language X"
- Client generation errors

**Solutions:**

1. **Check Server Directory Structure**
   ```bash
   # Expected structure
   /path/to/servers/
   ├── server-rust/
   ├── server-python/
   ├── server-csharp/
   └── server-go/
   ```

2. **Set Server Paths**
   ```python
   from blackholio_client.factory import set_server_path
   
   set_server_path("rust", "/path/to/rust-server")
   set_server_path("python", "/path/to/python-server")
   ```

3. **Verify Server Files**
   ```bash
   # Rust server
   ls /path/to/server-rust/Cargo.toml
   
   # Python server
   ls /path/to/server-python/requirements.txt
   
   # C# server
   ls /path/to/server-csharp/*.csproj
   
   # Go server
   ls /path/to/server-go/go.mod
   ```

### Client Generation Failures

**Symptoms:**
- "Failed to generate client"
- Module import errors
- Protocol mismatch errors

**Diagnosis:**
```bash
# Test client generation manually
spacetimedb generate client-python \
  --out-dir /tmp/test-client \
  --host localhost:3000 \
  --db-name blackholio

# Check generated files
ls -la /tmp/test-client/
```

**Solutions:**

1. **Clear Generated Clients**
   ```python
   from blackholio_client.integration import clear_generated_clients
   clear_generated_clients()
   ```

2. **Regenerate Clients**
   ```python
   from blackholio_client.integration import SpacetimeDBClientGenerator
   
   generator = SpacetimeDBClientGenerator()
   await generator.generate_client("rust", force=True)
   ```

3. **Check Server Version Compatibility**
   ```bash
   spacetimedb version
   # Ensure server and CLI versions match
   ```

## Authentication Errors

### Token Authentication Failures

**Symptoms:**
- `AuthenticationError`
- "Invalid token" errors
- Permission denied

**Solutions:**

1. **Check Token Validity**
   ```python
   if not client.validate_token():
       print("Token is invalid - re-authenticating")
       await client.authenticate(credentials)
   ```

2. **Clear Saved Tokens**
   ```python
   from blackholio_client.auth import clear_saved_tokens
   clear_saved_tokens()
   ```

3. **Debug Authentication**
   ```python
   client.on_authentication_changed(
       lambda authenticated: print(f"Auth status: {authenticated}")
   )
   ```

### Identity Management Issues

**Symptoms:**
- "No identity found"
- Identity conflicts
- Permission errors

**Solutions:**

1. **Reset Identity**
   ```python
   from blackholio_client.auth import IdentityManager
   
   identity_manager = IdentityManager()
   identity_manager.reset_identity()
   ```

2. **Check Identity Files**
   ```bash
   # Check identity storage
   ls ~/.blackholio/identity/
   
   # Clear if corrupted
   rm -rf ~/.blackholio/identity/
   ```

## Performance Issues

### Slow Connection/Operations

**Symptoms:**
- Long connection times
- Slow game operations
- High latency

**Diagnosis:**
```python
import time
from blackholio_client import create_game_client, Vector2

async def performance_test():
    client = create_game_client()
    
    # Test connection time
    start = time.time()
    await client.connect()
    connect_time = time.time() - start
    print(f"Connection time: {connect_time:.3f}s")
    
    # Test operation time
    await client.join_game("PerfTest")
    
    start = time.time()
    for i in range(10):
        await client.move_player(Vector2(0.1, 0.1))
    operation_time = time.time() - start
    print(f"10 operations time: {operation_time:.3f}s")
    
    await client.shutdown()

asyncio.run(performance_test())
```

**Solutions:**

1. **Optimize Connection Settings**
   ```bash
   export CONNECTION_TIMEOUT=15.0  # Reduce timeout
   export SPACETIME_PROTOCOL=v1.binary.spacetimedb  # Faster protocol
   ```

2. **Enable Connection Pooling**
   ```python
   from blackholio_client.connection import get_connection_manager
   
   manager = get_connection_manager()
   manager.configure_pool(min_connections=2, max_connections=10)
   ```

3. **Monitor Performance**
   ```python
   stats = client.get_client_statistics()
   print(f"Average response time: {stats['avg_response_time']}")
   print(f"Connection pool usage: {stats['pool_usage']}")
   ```

### Memory Usage Issues

**Symptoms:**
- Increasing memory usage
- Out of memory errors
- Slow performance over time

**Solutions:**

1. **Monitor Memory Usage**
   ```python
   import psutil
   import asyncio
   
   async def monitor_memory():
       while True:
           process = psutil.Process()
           memory_mb = process.memory_info().rss / 1024 / 1024
           print(f"Memory usage: {memory_mb:.1f} MB")
           await asyncio.sleep(10)
   ```

2. **Clean Up Resources**
   ```python
   # Always shutdown clients
   await client.shutdown()
   
   # Clear caches periodically
   from blackholio_client.integration import clear_generated_clients
   clear_generated_clients()
   ```

3. **Optimize Entity Management**
   ```python
   # Limit entity storage
   entities = client.get_all_entities()
   if len(entities) > 1000:
       # Process in batches
       pass
   ```

## Environment Variables

### Complete Environment Variable Reference

```bash
# Server Configuration
export SERVER_LANGUAGE=rust              # rust|python|csharp|go
export SERVER_IP=localhost               # Server IP address
export SERVER_PORT=3000                  # Server port
export SERVER_USE_SSL=false              # Enable SSL/TLS

# SpacetimeDB Configuration
export SPACETIME_DB_IDENTITY=blackholio  # Database identity
export SPACETIME_PROTOCOL=v1.json.spacetimedb  # Protocol version

# Connection Settings
export CONNECTION_TIMEOUT=30.0           # Connection timeout (seconds)
export RECONNECT_ATTEMPTS=5              # Max reconnection attempts
export RECONNECT_DELAY=2.0               # Delay between reconnects (seconds)
export ENABLE_AUTO_RECONNECT=true        # Enable auto-reconnect

# Authentication
export AUTH_TOKEN_PATH=~/.blackholio/tokens  # Token storage path
export IDENTITY_PATH=~/.blackholio/identity  # Identity storage path

# Performance
export CONNECTION_POOL_SIZE=5            # Connection pool size
export MAX_CONCURRENT_OPERATIONS=10      # Max concurrent ops
export OPERATION_TIMEOUT=10.0            # Operation timeout

# Logging and Debug
export LOG_LEVEL=INFO                    # DEBUG|INFO|WARN|ERROR
export DEBUG_MODE=false                  # Enable debug mode
export LOG_FILE=blackholio.log           # Log file path

# Development
export SPACETIMEDB_CLI_PATH=/usr/local/bin/spacetimedb  # CLI path
export DEVELOPMENT_MODE=false            # Development mode
export MOCK_SERVERS=false                # Use mock servers
```

### Environment Variable Validation

```python
def validate_environment():
    """Validate all environment variables."""
    import os
    
    validators = {
        'SERVER_LANGUAGE': lambda x: x in ['rust', 'python', 'csharp', 'go'],
        'SERVER_PORT': lambda x: 1 <= int(x) <= 65535,
        'CONNECTION_TIMEOUT': lambda x: float(x) > 0,
        'RECONNECT_ATTEMPTS': lambda x: int(x) >= 0,
        'SERVER_USE_SSL': lambda x: x.lower() in ['true', 'false'],
        'LOG_LEVEL': lambda x: x.upper() in ['DEBUG', 'INFO', 'WARN', 'ERROR']
    }
    
    errors = []
    for var, validator in validators.items():
        value = os.getenv(var)
        if value:
            try:
                if not validator(value):
                    errors.append(f"{var}={value} is invalid")
            except ValueError:
                errors.append(f"{var}={value} has wrong type")
    
    if errors:
        print("❌ Environment validation errors:")
        for error in errors:
            print(f"  {error}")
    else:
        print("✅ All environment variables are valid")

validate_environment()
```

## Docker Issues

### Container Connection Problems

**Symptoms:**
- Cannot connect between containers
- "Host not found" errors
- Network isolation issues

**Solutions:**

1. **Check Docker Network**
   ```bash
   # List networks
   docker network ls
   
   # Inspect network
   docker network inspect bridge
   
   # Check container IPs
   docker inspect container_name | grep IPAddress
   ```

2. **Use Service Names**
   ```yaml
   # docker-compose.yml
   services:
     client:
       environment:
         - SERVER_IP=rust-server  # Use service name, not localhost
     rust-server:
       ports:
         - "3000:3000"
   ```

3. **Test Connectivity**
   ```bash
   # Inside client container
   docker exec -it client_container ping rust-server
   docker exec -it client_container nc -zv rust-server 3000
   ```

### Volume and Permission Issues

**Symptoms:**
- Cannot write to volumes
- Permission denied errors
- Missing configuration files

**Solutions:**

1. **Fix Volume Permissions**
   ```bash
   # Set correct ownership
   sudo chown -R 1000:1000 ./data
   
   # Use correct volume mapping
   docker run -v $(pwd)/data:/app/data blackholio-client
   ```

2. **Check File Permissions**
   ```bash
   # Inside container
   docker exec -it container ls -la /app/
   ```

### Image Build Issues

**Common Problems:**

1. **Missing Dependencies**
   ```dockerfile
   # Add missing system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       libssl-dev \
       pkg-config
   ```

2. **Python Package Issues**
   ```dockerfile
   # Install specific versions
   RUN pip install --no-cache-dir blackholio-client==0.1.0
   
   # Or install from git
   RUN pip install git+https://github.com/blackholio/blackholio-python-client.git
   ```

## Migration Problems

### Blackholio-Agent Migration Issues

**Common Issues:**

1. **API Method Changes**
   ```python
   # OLD: Direct connection access
   connection._entities
   
   # NEW: Client methods
   client.get_all_entities()
   ```

2. **Event Handling Changes**
   ```python
   # OLD: Manual subscription
   connection._subscribe_to_tables()
   
   # NEW: Automatic subscription
   client.join_game("Player")
   ```

3. **Configuration Changes**
   ```python
   # OLD: Hardcoded configuration
   BlackholioConnectionV112(host="localhost:3000")
   
   # NEW: Environment-based
   create_game_client()  # Uses environment variables
   ```

### Client-Pygame Migration Issues

**Common Issues:**

1. **Data Access Patterns**
   ```python
   # OLD: Direct data access
   for entity_id, entity_data in connection._entities.items():
       pos = entity_data['position']
   
   # NEW: Typed objects
   for entity in client.get_all_entities().values():
       pos = entity.position  # Vector2 object
   ```

2. **Event Callbacks**
   ```python
   # OLD: Manual polling
   if new_entities:
       for entity in new_entities:
           render_entity(entity)
   
   # NEW: Event-driven
   client.on_entity_created(render_entity)
   ```

## Debug Tools

### Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or set via environment
import os
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['DEBUG_MODE'] = 'true'
```

### Debug Connection Issues

```python
from blackholio_client.utils.debugging import DebugCapture

async def debug_connection():
    debug = DebugCapture()
    
    with debug.capture_context():
        client = create_game_client()
        await client.connect()
    
    # Analyze captured data
    debug_data = debug.get_captured_data()
    print("Debug information:")
    for key, value in debug_data.items():
        print(f"  {key}: {value}")
```

### Performance Profiling

```python
from blackholio_client.utils.debugging import PerformanceProfiler

async def profile_operations():
    profiler = PerformanceProfiler()
    
    profiler.start_checkpoint("connection")
    client = create_game_client()
    await client.connect()
    profiler.end_checkpoint("connection")
    
    profiler.start_checkpoint("game_join")
    await client.join_game("TestPlayer")
    profiler.end_checkpoint("game_join")
    
    # Get performance report
    report = profiler.get_report()
    print("Performance Report:")
    for operation, time_taken in report.items():
        print(f"  {operation}: {time_taken:.3f}s")
```

### Network Traffic Analysis

```bash
# Monitor network traffic
sudo tcpdump -i any port 3000

# Use netstat to check connections
netstat -an | grep 3000

# Monitor WebSocket traffic
websocat -t ws://localhost:3000 --ping-interval 10
```

## FAQ

### Q: Why can't I connect to the server?

**A:** Most connection issues are due to:
1. Server not running - check `ps aux | grep spacetime`
2. Wrong port - verify `SERVER_PORT` environment variable
3. Firewall blocking - check `sudo ufw status`
4. Docker network issues - use service names instead of localhost

### Q: The client keeps reconnecting - what's wrong?

**A:** Frequent reconnections usually indicate:
1. Unstable network connection
2. Server overload or crashes
3. Incorrect timeout settings
4. SSL/TLS configuration issues

### Q: Environment variables aren't working

**A:** Check:
1. Variables are exported: `export VAR=value`
2. Spelling is correct: `SERVER_LANGUAGE` not `SERVER_LANG`
3. Values are valid: `rust|python|csharp|go` for `SERVER_LANGUAGE`
4. Using `.env` file: ensure `python-dotenv` is installed

### Q: Getting "Server language not supported" error

**A:** Ensure:
1. SpacetimeDB CLI is installed and in PATH
2. Server implementation exists in expected directory
3. `SERVER_LANGUAGE` is one of: `rust`, `python`, `csharp`, `go`
4. Generated client matches server version

### Q: Performance is slower than expected

**A:** Try:
1. Use binary protocol: `SPACETIME_PROTOCOL=v1.binary.spacetimedb`
2. Enable connection pooling
3. Reduce timeout values for faster operations
4. Use Rust server for best performance

### Q: How do I migrate from the old blackholio-agent code?

**A:** See the migration examples:
1. Replace `BlackholioConnectionV112` with `create_game_client()`
2. Use `client.join_game()` instead of manual connection + subscription
3. Replace direct data access (`connection._entities`) with client methods (`client.get_all_entities()`)
4. Update event handling to use callbacks

### Q: Docker containers can't communicate

**A:** Common Docker issues:
1. Use service names in `SERVER_IP`, not `localhost`
2. Ensure containers are on the same network
3. Check port mapping in `docker-compose.yml`
4. Verify firewall isn't blocking container communication

### Q: Getting SSL/TLS errors

**A:** For SSL issues:
1. Set `SERVER_USE_SSL=false` for testing
2. For production, ensure valid certificates
3. Use `SSL_VERIFY=false` for self-signed certificates
4. Check server SSL configuration

### Q: Memory usage keeps increasing

**A:** Prevent memory leaks:
1. Always call `await client.shutdown()`
2. Clear generated clients periodically
3. Monitor entity count - process in batches if needed
4. Use context managers where available

### Q: Tests are failing in CI/CD

**A:** Common CI issues:
1. Install SpacetimeDB CLI in CI environment
2. Use mock servers for testing: `MOCK_SERVERS=true`
3. Set appropriate timeouts for CI: `CONNECTION_TIMEOUT=60.0`
4. Ensure all dependencies are installed

---

## Getting Help

If this troubleshooting guide doesn't solve your issue:

1. **Enable debug logging** and check the logs
2. **Run the health check script** to identify the problem area
3. **Check GitHub issues** for similar problems
4. **Create a minimal reproduction case**
5. **Open a new issue** with full details and logs

### Information to Include in Bug Reports

- Blackholio client version
- Python version and OS
- Environment variable configuration
- Full error messages and stack traces
- Steps to reproduce the issue
- Expected vs actual behavior

For urgent issues, include the output of the health check script and full debug logs.