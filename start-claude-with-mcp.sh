#!/bin/bash

# Load environment variables
if [ -f "/home/azureuser/mcprag/.env" ]; then
    export $(grep -v '^#' /home/azureuser/mcprag/.env | xargs)
fi

# Ensure virtual environment is activated for the MCP server
source /home/azureuser/mcprag/.venv/bin/activate

# Start Claude Code with MCP configuration
# Replace environment variables in the config file
envsubst < /home/azureuser/mcprag/claude-mcp-config.json > /tmp/claude-mcp-config-resolved.json

# Launch Claude Code with the MCP server
# Use --allowedTools to permit the MCP tools
claude-code:model-session tsei \
    --mcp-config /tmp/claude-mcp-config-resolved.json \
    --allowedTools "mcp__azure-code-search__search_code,mcp__azure-code-search__get_file_context,mcp__azure-code-search__search_similar_code"

# Alternative: If you want to use it in non-interactive mode for testing
# claude -p "Search for authentication functions in the codebase" \
#     --mcp-config /tmp/claude-mcp-config-resolved.json \
#     --allowedTools "mcp__azure-code-search__search_code"
