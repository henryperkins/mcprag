#!/bin/bash

# Claude Code UI Integration Test Script
# This script tests the various endpoints of the Claude Code Worker integration

BASE_URL="${1:-http://localhost:5173}"
echo "Testing Claude Code UI at: $BASE_URL"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local path="$3"
    local data="$4"
    local expected_status="${5:-200}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}"
    echo "Method: $method"
    echo "Path: $path"
    
    if [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            echo "Data: $data"
            response=$(curl -s -w "\n%{http_code}" -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$path")
        else
            response=$(curl -s -w "\n%{http_code}" -X POST \
                "$BASE_URL$path")
        fi
    else
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$path")
    fi
    
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ Status: $status_code (expected)${NC}"
        echo "Response: $(echo "$body" | head -c 200)..."
    else
        echo -e "${RED}✗ Status: $status_code (expected $expected_status)${NC}"
        echo "Response: $body"
    fi
}

# 1. Test health endpoint
test_endpoint "Health Check" "GET" "/api/health"

# 2. Test CORS preflight
echo -e "\n${YELLOW}Testing: CORS Preflight${NC}"
curl -s -I -X OPTIONS "$BASE_URL/api/query" | grep -i "access-control"

# 3. Test sessions endpoint
test_endpoint "Get Sessions" "GET" "/api/sessions"

# 4. Test basic query (will fail without API key in dev)
test_endpoint "Basic Query" "POST" "/api/query" \
    '{"prompt":"Hello, Claude!","outputFormat":"json"}' \
    "500"  # Expecting 500 if no API key

# 5. Test streaming query
echo -e "\n${YELLOW}Testing: Streaming Query${NC}"
echo "Sending streaming request..."
curl -N -H "Content-Type: application/json" \
    -X POST "$BASE_URL/api/query" \
    -d '{"prompt":"Test streaming","outputFormat":"stream-json"}' \
    2>/dev/null | head -n 5
echo -e "\n${GREEN}✓ Streaming test complete${NC}"

# 6. Test interrupt endpoint
test_endpoint "Interrupt Session" "POST" "/api/interrupt" \
    '{"sessionId":"test-session-123"}' \
    "404"  # Expecting 404 for non-existent session

# 7. Test with tools
test_endpoint "Query with Tools" "POST" "/api/query" \
    '{"prompt":"Create hello.txt","allowedTools":["Write"],"permissionMode":"acceptEdits"}' \
    "500"  # Expecting 500 if no API key

# 8. Test invalid request
test_endpoint "Invalid Request" "POST" "/api/query" \
    'invalid json' \
    "400"  # Expecting 400 for invalid JSON

echo -e "\n================================"
echo -e "${GREEN}Integration tests complete!${NC}"
echo ""
echo "Note: Some tests may fail if:"
echo "1. ANTHROPIC_API_KEY is not configured"
echo "2. The server is not running at $BASE_URL"
echo "3. The Claude Code SDK is not properly installed"
echo ""
echo "To set up API key for local testing:"
echo "  echo 'ANTHROPIC_API_KEY=your-key' > .dev.vars"
echo "  npm run dev"