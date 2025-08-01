# Claude Code MCP Setup Instructions

## Quick Setup

1. **Add the MCP server to Claude Code:**
```bash
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -e ACS_ENDPOINT="${ACS_ENDPOINT}" \
  -e ACS_ADMIN_KEY="${ACS_ADMIN_KEY}"
```

2. **Verify the server is added:**
```bash
claude mcp list
```

3. **Test the server in Claude Code:**
Type in Claude Code:
```
search for vector dimension configuration
```

## Alternative Setup Methods

### Method 1: Local Scope (Default)
```bash
# Add for current project only
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -s local \
  -e ACS_ENDPOINT="${ACS_ENDPOINT}" \
  -e ACS_ADMIN_KEY="${ACS_ADMIN_KEY}"
```

### Method 2: User Scope (All Projects)
```bash
# Add for all your projects
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -s user \
  -e ACS_ENDPOINT="${ACS_ENDPOINT}" \
  -e ACS_ADMIN_KEY="${ACS_ADMIN_KEY}"
```

### Method 3: Project Scope (Team Sharing)
```bash
# Add to .mcp.json for team sharing
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -s project
```

This creates `.mcp.json` in your project root:
```json
{
  "mcpServers": {
    "azure-search": {
      "command": "python",
      "args": ["/home/azureuser/mcprag/mcp_server_sota.py"],
      "env": {
        "ACS_ENDPOINT": "${ACS_ENDPOINT}",
        "ACS_ADMIN_KEY": "${ACS_ADMIN_KEY}"
      }
    }
  }
}
```

## Available Tools

Once configured, you'll have access to these tools in Claude Code:

1. **search_code** - Advanced code search with filtering
   - Parameters: query, intent, language, repository, max_results, include_dependencies
   - Example: `search for authentication functions with intent='implement'`

2. **search_microsoft_docs** - Search Microsoft documentation
   - Parameters: query, max_results
   - Example: `search Microsoft docs for Azure Functions`

## Available Resources

The server provides these resources you can reference with `@`:

- `@azure-search:resource://repositories` - List all indexed repositories
- `@azure-search:resource://statistics` - Get search statistics

## Available Prompts

Use these slash commands:

- `/mcp__azure-search__implement_feature` - Generate implementation plan
- `/mcp__azure-search__debug_error` - Get debugging assistance

## Troubleshooting

### Check Server Status
In Claude Code, type:
```
/mcp
```

### View Server Logs
```bash
claude mcp get azure-search
```

### Remove and Re-add
```bash
claude mcp remove azure-search
# Then add again with the command above
```

### Common Issues

1. **"Connection closed" error**: Make sure environment variables are set
2. **"No results found"**: Check if your codebase is indexed
3. **Tool not available**: Restart Claude Code after adding the server

## API Mode (Optional)

The server also supports API mode for direct HTTP access:
```bash
python /home/azureuser/mcprag/mcp_server_sota.py --api
```

This starts a FastAPI server on http://localhost:8001 with Swagger docs at http://localhost:8001/docs