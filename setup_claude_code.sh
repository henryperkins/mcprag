#!/bin/bash
# Setup script to add the mcprag server to Claude Code

set -e

echo "Setting up Azure Code Search MCP server for Claude Code..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Claude Code config directory exists
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
if [ ! -d "$CLAUDE_CONFIG_DIR" ] && [ ! -d "$HOME/.config/claude" ]; then
    # Try Linux path
    CLAUDE_CONFIG_DIR="$HOME/.config/claude"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# Determine the correct config directory
if [ -d "$HOME/Library/Application Support/Claude" ]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
elif [ -d "$HOME/.config/claude" ]; then
    CLAUDE_CONFIG_DIR="$HOME/.config/claude"
else
    echo "Error: Could not find Claude Code configuration directory"
    echo "Please ensure Claude Code is installed"
    exit 1
fi

echo "Using Claude config directory: $CLAUDE_CONFIG_DIR"

# Check if mcp-servers.json exists
MCP_CONFIG_FILE="$CLAUDE_CONFIG_DIR/mcp-servers.json"

if [ ! -f "$MCP_CONFIG_FILE" ]; then
    echo "Creating new mcp-servers.json..."
    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {}
}
EOF
fi

# Check if required environment variables are set
if [ -z "$ACS_ENDPOINT" ] || [ -z "$ACS_ADMIN_KEY" ]; then
    echo "Warning: ACS_ENDPOINT and ACS_ADMIN_KEY environment variables are not set"
    echo "You'll need to set these in your environment or update the config file manually"
fi

# Create a Python script to update the JSON properly
cat > /tmp/update_mcp_config.py << EOF
import json
import sys
import os

config_file = sys.argv[1]
script_dir = sys.argv[2]

# Read existing config
with open(config_file, 'r') as f:
    config = json.load(f)

# Ensure mcpServers key exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add or update azure-code-search-enhanced server
config['mcpServers']['azure-code-search-enhanced'] = {
    "command": "python3",
    "args": [
        "-m",
        "mcprag"
    ],
    "cwd": script_dir,
    "env": {
        "ACS_ENDPOINT": os.environ.get('ACS_ENDPOINT', '\${ACS_ENDPOINT}'),
        "ACS_ADMIN_KEY": os.environ.get('ACS_ADMIN_KEY', '\${ACS_ADMIN_KEY}'),
        "ACS_INDEX_NAME": os.environ.get('ACS_INDEX_NAME', 'codebase-mcp-sota'),
        "PYTHONPATH": script_dir
    }
}

# Write updated config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Successfully updated {config_file}")
EOF

# Run the Python script to update the config
python3 /tmp/update_mcp_config.py "$MCP_CONFIG_FILE" "$SCRIPT_DIR"

# Clean up
rm /tmp/update_mcp_config.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "The Azure Code Search Enhanced MCP server has been added to Claude Code."
echo ""
echo "Make sure to:"
echo "1. Set the following environment variables in your shell profile:"
echo "   export ACS_ENDPOINT='https://your-search-service.search.windows.net'"
echo "   export ACS_ADMIN_KEY='your-admin-key'"
echo ""
echo "2. Restart Claude Code for the changes to take effect"
echo ""
echo "3. The MCP tools will be available with the prefix 'mcp__azure-code-search-enhanced__'"
echo ""
echo "Available tools:"
echo "  - mcp__azure-code-search-enhanced__search_code"
echo "  - mcp__azure-code-search-enhanced__search_code_raw"
echo "  - mcp__azure-code-search-enhanced__search_microsoft_docs"
echo "  - mcp__azure-code-search-enhanced__explain_ranking"
echo "  - mcp__azure-code-search-enhanced__cache_stats"
echo "  - mcp__azure-code-search-enhanced__cache_clear"
echo "  - mcp__azure-code-search-enhanced__index_rebuild"
echo "  - mcp__azure-code-search-enhanced__github_index_repo"