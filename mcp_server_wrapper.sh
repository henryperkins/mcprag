#!/bin/bash
# MCP Server wrapper script that loads environment variables

# Load from .env file if it exists
if [ -f "/home/azureuser/mcprag/.env" ]; then
    export $(grep -v '^#' /home/azureuser/mcprag/.env | xargs)
fi

# Check if required variables are set
if [ -z "$ACS_ENDPOINT" ] || [ -z "$ACS_ADMIN_KEY" ]; then
    echo "Error: ACS_ENDPOINT and ACS_ADMIN_KEY must be set" >&2
    echo "Please create a .env file with:" >&2
    echo "ACS_ENDPOINT=your-endpoint-here" >&2
    echo "ACS_ADMIN_KEY=your-key-here" >&2
    exit 1
fi

# Run the MCP server
exec python3 /home/azureuser/mcprag/mcp_server_sota.py "$@"
