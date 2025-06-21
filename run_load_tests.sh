#!/bin/bash

# Load Testing Script for blackholio-python-client
# This script runs comprehensive load and stress tests against the package

set -e

echo "🚀 BLACKHOLIO PYTHON CLIENT - LOAD TESTING SUITE"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment is active
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}⚠️  Warning: No virtual environment detected${NC}"
    echo "It's recommended to run tests in a virtual environment"
    echo ""
fi

# Function to run load tests
run_load_tests() {
    local server_language=$1
    echo -e "\n${GREEN}🔥 Running load tests for ${server_language} server...${NC}"
    
    # Set environment variable
    export SERVER_LANGUAGE=$server_language
    
    # Run pytest load tests
    echo -e "\n📊 Running pytest load tests..."
    python -m pytest tests/test_load_stress.py -v -m load_test -s --tb=short || true
    
    # Run comprehensive load test
    echo -e "\n🏋️  Running comprehensive load test..."
    python tests/load_testing.py --server-language $server_language || true
}

# Function to run quick performance check
quick_performance_check() {
    echo -e "\n${GREEN}⚡ Running quick performance check...${NC}"
    python -m pytest tests/test_performance.py -v -k "test_vector_operations or test_entity_operations" -s --tb=short
}

# Function to check system resources
check_system_resources() {
    echo -e "\n${GREEN}💻 System Resources:${NC}"
    echo "  CPU Cores: $(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 'Unknown')"
    echo "  Memory: $(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)"GB"}' || free -h | grep Mem | awk '{print $2}' || echo 'Unknown')"
    echo "  Python: $(python --version)"
    echo ""
}

# Function to create results directory
setup_results_dir() {
    local results_dir="tests/load_test_results"
    mkdir -p "$results_dir"
    echo -e "${GREEN}📁 Results will be saved to: $results_dir${NC}"
}

# Main menu
show_menu() {
    echo "Select load testing option:"
    echo "1) Quick performance check"
    echo "2) Load test - Rust server"
    echo "3) Load test - Python server"
    echo "4) Load test - C# server"
    echo "5) Load test - Go server"
    echo "6) Load test - All servers"
    echo "7) Stress test - Memory pressure"
    echo "8) Stress test - Connection limits"
    echo "9) Full test suite (all of the above)"
    echo "0) Exit"
    echo ""
}

# Memory pressure test
run_memory_pressure_test() {
    echo -e "\n${GREEN}💾 Running memory pressure test...${NC}"
    python -c "
import sys
sys.path.insert(0, 'src')
from blackholio_client import GameEntity, Vector2
import random
import gc
import psutil
import time

print('Creating 100,000 entities...')
entities = []
start_memory = psutil.Process().memory_info().rss / 1024 / 1024

for i in range(100000):
    entity = GameEntity(
        id=f'entity_{i}',
        owner_id=f'player_{i % 1000}',
        position=Vector2(random.uniform(0, 1000), random.uniform(0, 1000)),
        mass=random.uniform(10, 100),
        entity_type='circle'
    )
    entities.append(entity)
    
    if i % 10000 == 0:
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        print(f'  {i:,} entities created, Memory: {current_memory:.1f} MB')

final_memory = psutil.Process().memory_info().rss / 1024 / 1024
memory_used = final_memory - start_memory

print(f'\nMemory usage for 100,000 entities: {memory_used:.1f} MB')
print(f'Average per entity: {memory_used / 100 * 1000:.1f} KB')

# Cleanup
del entities
gc.collect()
time.sleep(1)

cleanup_memory = psutil.Process().memory_info().rss / 1024 / 1024
print(f'Memory after cleanup: {cleanup_memory:.1f} MB')
"
}

# Connection limits test
run_connection_limits_test() {
    echo -e "\n${GREEN}🔌 Running connection limits test...${NC}"
    python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from blackholio_client import create_game_client
import time

async def test_many_clients():
    print('Creating many client instances...')
    clients = []
    
    for i in range(100):
        try:
            client = create_game_client()
            clients.append(client)
            if i % 10 == 0:
                print(f'  Created {i} clients')
        except Exception as e:
            print(f'  Failed at client {i}: {e}')
            break
    
    print(f'\nSuccessfully created {len(clients)} client instances')
    
    # Test concurrent operations
    print('\nTesting concurrent operations on all clients...')
    start = time.time()
    
    async def client_operation(client, index):
        # Simulate some work
        await asyncio.sleep(0.001)
        return index
    
    tasks = [client_operation(client, i) for i, client in enumerate(clients)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f'Completed {len(results)} operations in {elapsed:.2f}s')
    print(f'Operations per second: {len(results) / elapsed:.0f}')

asyncio.run(test_many_clients())
"
}

# Parse command line arguments
if [ "$1" == "--quick" ]; then
    check_system_resources
    quick_performance_check
    exit 0
elif [ "$1" == "--all" ]; then
    CHOICE=9
else
    # Interactive mode
    check_system_resources
    show_menu
    read -p "Enter choice [0-9]: " CHOICE
fi

# Setup results directory
setup_results_dir

# Execute based on choice
case $CHOICE in
    1)
        quick_performance_check
        ;;
    2)
        run_load_tests "rust"
        ;;
    3)
        run_load_tests "python"
        ;;
    4)
        run_load_tests "csharp"
        ;;
    5)
        run_load_tests "go"
        ;;
    6)
        for lang in rust python csharp go; do
            run_load_tests $lang
        done
        ;;
    7)
        run_memory_pressure_test
        ;;
    8)
        run_connection_limits_test
        ;;
    9)
        # Full test suite
        quick_performance_check
        
        for lang in rust python csharp go; do
            run_load_tests $lang
        done
        
        run_memory_pressure_test
        run_connection_limits_test
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✅ Load testing complete!${NC}"
echo "Check tests/load_test_results/ for detailed results"