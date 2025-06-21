#!/bin/bash
# Docker Validation Test Runner for blackholio-python-client
# This script tests the package in Docker containers with different configurations

set -e

echo "🚀 BlackHolio Python Client - Docker Compatibility Validation"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create test results directory
mkdir -p test-results/{rust,python,csharp,go,production}

# Function to run tests for a specific server language
run_language_test() {
    local language=$1
    echo -e "\n${YELLOW}🔧 Testing with $language server configuration${NC}"
    echo "----------------------------------------"
    
    # Build the Docker image
    echo "📦 Building Docker image..."
    docker-compose build test-$language
    
    # Run the tests
    echo "🧪 Running tests in container..."
    if docker-compose run --rm test-$language; then
        echo -e "${GREEN}✅ $language tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $language tests failed!${NC}"
        return 1
    fi
}

# Function to run production environment test
run_production_test() {
    echo -e "\n${YELLOW}🏭 Testing production configuration${NC}"
    echo "----------------------------------------"
    
    # Build production image
    echo "📦 Building production Docker image..."
    docker-compose build test-production
    
    # Run production container
    echo "🚀 Running production container..."
    if docker-compose run --rm test-production; then
        echo -e "${GREEN}✅ Production test passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Production test failed!${NC}"
        return 1
    fi
}

# Function to run interactive validation
run_interactive_validation() {
    local language=$1
    echo -e "\n${YELLOW}🔍 Running interactive validation for $language${NC}"
    echo "----------------------------------------"
    
    # Create temporary validation script
    cat > test-results/validate-in-container.sh << 'EOF'
#!/bin/bash
echo "🐳 Container Environment Validation"
echo "==================================="
echo ""
echo "Environment Variables:"
env | grep -E "(SERVER_|BLACKHOLIO_)" | sort
echo ""
echo "Python Environment:"
python --version
pip list | grep blackholio
echo ""
echo "Running validation script..."
python /app/tests/test_docker_validation.py
EOF
    
    chmod +x test-results/validate-in-container.sh
    
    # Run validation in container
    docker run --rm \
        -e SERVER_LANGUAGE=$language \
        -e SERVER_IP=test-server-$language \
        -e SERVER_PORT=8080 \
        -e BLACKHOLIO_LOG_LEVEL=DEBUG \
        -e DOCKER_CONTAINER=true \
        -v $(pwd)/test-results:/app/test-results \
        -v $(pwd)/test-results/validate-in-container.sh:/validate.sh \
        blackholio-python-client:latest \
        bash /validate.sh
}

# Main execution
main() {
    local all_passed=true
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    
    # Clean previous test results
    echo "🧹 Cleaning previous test results..."
    rm -rf test-results/*
    
    # Test each server language configuration
    for language in rust python csharp go; do
        if ! run_language_test $language; then
            all_passed=false
        fi
    done
    
    # Test production configuration
    if ! run_production_test; then
        all_passed=false
    fi
    
    # Run interactive validation for Rust (default)
    echo -e "\n${YELLOW}🔍 Running detailed validation${NC}"
    docker-compose build dev
    run_interactive_validation rust
    
    # Generate summary report
    echo -e "\n\n${YELLOW}📊 Docker Validation Summary${NC}"
    echo "========================================"
    
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}✅ All Docker compatibility tests passed!${NC}"
        echo ""
        echo "The blackholio-python-client package is fully compatible with Docker containers:"
        echo "- ✓ Environment variable configuration works correctly"
        echo "- ✓ All server languages (Rust, Python, C#, Go) are supported"
        echo "- ✓ Production configuration validated"
        echo "- ✓ Package installs and imports correctly in containers"
        echo "- ✓ Configuration persistence and reloading works"
        echo ""
        echo "🎉 Ready for containerized deployment!"
    else
        echo -e "${RED}❌ Some Docker compatibility tests failed${NC}"
        echo ""
        echo "Please check the test results in ./test-results/ for details."
    fi
    
    # Show test result locations
    echo -e "\n📁 Test results saved in:"
    for dir in test-results/*/; do
        if [ -d "$dir" ]; then
            echo "  - $dir"
        fi
    done
    
    # Cleanup
    echo -e "\n🧹 Cleaning up Docker resources..."
    docker-compose down --remove-orphans
    
    # Return appropriate exit code
    if [ "$all_passed" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle script arguments
case "${1:-test}" in
    test)
        main
        ;;
    shell)
        # Launch interactive shell for debugging
        echo "🐚 Launching interactive Docker shell..."
        docker-compose run --rm dev
        ;;
    clean)
        # Clean all Docker resources
        echo "🧹 Cleaning Docker resources..."
        docker-compose down --rmi all --volumes --remove-orphans
        rm -rf test-results
        echo "✅ Cleanup complete"
        ;;
    *)
        echo "Usage: $0 [test|shell|clean]"
        echo "  test  - Run all Docker validation tests (default)"
        echo "  shell - Launch interactive Docker shell"
        echo "  clean - Clean all Docker resources"
        exit 1
        ;;
esac