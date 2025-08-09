#!/bin/bash
# Start MCP Bridge Server

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
REMOTE_URL=${MCPRAG_REMOTE_URL:-"http://localhost:8002"}
SESSION_TOKEN=${MCPRAG_SESSION_TOKEN:-"dev-mode"}

echo "Starting MCP Bridge Server..."
echo "Remote URL: $REMOTE_URL"
echo "Session Token: $SESSION_TOKEN"
echo

# Check if remote server is running
if ! curl -s "$REMOTE_URL/health" > /dev/null 2>&1; then
    echo "❌ Warning: Remote server at $REMOTE_URL appears to be down"
    echo "   Make sure to start the remote server first with: ./start-remote-server.sh"
    echo
fi

# Check if virtual environment exists and activate it
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "Activating virtual environment..."
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    echo "Activating virtual environment..."
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Install dependencies if needed
if ! python -c "import mcp.server.fastmcp" 2>/dev/null; then
    echo "Installing mcp package..."
    pip install mcp
fi

if ! python -c "import httpx" 2>/dev/null; then
    echo "Installing httpx package..."
    pip install httpx
fi

# Set environment variables
export MCPRAG_REMOTE_URL="$REMOTE_URL"
export MCPRAG_SESSION_TOKEN="$SESSION_TOKEN"

# Start the bridge server
echo "Starting bridge server..."
cd "$SCRIPT_DIR"
python mcp_bridge.py
