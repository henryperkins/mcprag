#!/bin/bash

# Load environment from .env.remote
set -a
source .env.remote
set +a

# Override with Docker Redis on port 6380
export REDIS_URL=redis://localhost:6380
export MCP_PORT=8002  # Using 8002 to avoid conflicts
export MCP_HOST=0.0.0.0
export MCP_DEV_MODE=true
export MCP_BASE_URL=http://localhost:8002

echo "Starting Remote MCP Server..."
echo "Redis: $REDIS_URL"
echo "Server: http://localhost:$MCP_PORT"
echo "Dev Mode: $MCP_DEV_MODE"
echo ""

# Start the server
python -m mcprag.remote_server
