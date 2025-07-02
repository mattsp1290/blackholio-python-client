#!/bin/bash
# Script to test the subscription callback fix

echo "🚀 Testing Subscription Callback Fix"
echo "===================================="
echo ""

# First check if server is running
echo "Checking if Blackholio server is running on localhost:3000..."
nc -z localhost 3000
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Blackholio server is not running on localhost:3000"
    echo ""
    echo "Please start the server first:"
    echo "  cd ../blackholio"
    echo "  spacetime server --listen-addr 0.0.0.0:3000"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Run the test
echo "Running callback fix test..."
echo "----------------------------"
python test_callback_fix.py 2>&1 | tee test_output.log

# Check for success indicators in the output
echo ""
echo "Analyzing test results..."
echo "------------------------"

# Look for key indicators
if grep -q "Triggering event 'initial_subscription' with 0 callbacks" test_output.log; then
    echo "❌ PROBLEM: Still seeing events with 0 callbacks"
elif grep -q "Triggering event 'identity_token' with 0 callbacks" test_output.log; then
    echo "❌ PROBLEM: Still seeing identity_token with 0 callbacks"
elif grep -q "TEST PASSED: Subscription callbacks working!" test_output.log; then
    echo "✅ SUCCESS: Test passed!"
else
    echo "⚠️  WARNING: Could not determine test result"
fi

# Check for timeout warnings
if grep -q "Timeout waiting for subscription data" test_output.log; then
    echo "❌ PROBLEM: Still seeing subscription timeout"
fi

# Check callback registration
if grep -q "Registering event handlers BEFORE connection starts" test_output.log; then
    echo "✅ Callbacks registered early as expected"
fi

echo ""
echo "Full output saved to: test_output.log"