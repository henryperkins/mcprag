#!/bin/bash

# Script to configure Claude Code with Azure code search MCP server

echo "Adding Azure code search MCP server to Claude Code..."

claude mcp add azure-code-search \
    -e ACS_ENDPOINT=https://oairesourcesearch.search.windows.net \
    -e ACS_ADMIN_KEY=Ne3DXE0h6ZiYANoKTuJlcTP6TJaEiDOsT9iTA399nUAzSeAetXI3 \
    -e ACS_INDEX_NAME=codebase-mcp-sota \
    --transport stdio \
    -- python -m mcprag

echo "MCP server configuration complete!"