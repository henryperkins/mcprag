# Adding MCP Server to Claude

This guide explains how to integrate your Azure Cognitive Search MCP server with Claude.

## Option 1: HTTP API Server (Current Implementation)

Your current MCP server runs from the `mcprag` package. Here's how to use it:

### 1. Start the Server

```bash
cd /home/hperkins/mcprag
source venv/bin/activate
python -m mcprag
```

The server will start on `http://localhost:8001`

### 2. Test the Server

```bash
# Health check
curl http://localhost:8001/health

# Test search
curl -X POST http://localhost:8001/mcp-query \
  -H "Content-Type: application/json" \
  -d '{
    "input": "authentication function",
    "intent": "implement",
    "context": {
      "current_language": "python"
    }
  }'
```

### 3. Claude Desktop Configuration

Create or edit the Claude Desktop configuration file:

**File Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "azure-code-search": {
      "command": "python",
      "args": ["-m", "mcprag"],
      "env": {
        "ACS_ENDPOINT": "https://mcprag-search.search.windows.net",
        "ACS_ADMIN_KEY": "rLimu7VZq1P4j99xsStwqYjYQ4SqU9ydOK3hLVTq7qAzSeCsmXKD"
      }
    }
  }
}
```

## Option 2: MCP Protocol Compliant Server (Recommended)

For full MCP compliance, use the new `mcp_server_compliant.py`:

### 1. Claude Desktop Configuration

```json
{
  "mcpServers": {
    "azure-code-search": {
      "command": "python",
      "args": ["/home/hperkins/mcprag/mcp_server_compliant.py"],
      "env": {
        "ACS_ENDPOINT": "https://mcprag-search.search.windows.net",
        "ACS_ADMIN_KEY": "rLimu7VZq1P4j99xsStwqYjYQ4SqU9ydOK3hLVTq7qAzSeCsmXKD"
      }
    }
  }
}
```

### 2. Test MCP Server

```bash
# Test the MCP server directly
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | python mcp_server_compliant.py
```

## Usage in Claude

Once configured, you can use the MCP server in Claude:

### Example Queries

1. **Search for authentication code:**
   - "Search for authentication functions in my codebase"
   - "Find login implementation examples"

2. **Debug assistance:**
   - "Search for error handling patterns"
   - "Find exception catching examples"

3. **Implementation help:**
   - "Search for database connection code"
   - "Find API client implementations"

### Available Tools

The MCP server provides one tool:

- **search_code**: Search for code snippets with semantic understanding
  - `query` (required): Natural language search query
  - `intent` (optional): "implement", "debug", "understand", or "refactor"
  - `language` (optional): Programming language filter

## Troubleshooting

### Server Not Starting
1. Check that Azure credentials are correct in `.env`
2. Verify the search index exists: `python create_index.py`
3. Test Azure connection: `python test_setup.py`

### Claude Not Finding Server
1. Restart Claude Desktop after configuration changes
2. Check file paths in configuration are absolute
3. Verify Python environment has required packages

### No Search Results
1. Ensure code has been indexed: `python smart_indexer.py`
2. Check Azure Search service is running
3. Try simpler search queries first

## Next Steps

1. **Index your code**: Run `python smart_indexer.py` to index your repositories
2. **Customize search**: Modify intent enhancement in the server code
3. **Add more tools**: Extend the MCP server with additional capabilities

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude App    │───▶│   MCP Server     │───▶│  Azure Search   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Your Codebase  │
                       └──────────────────┘
```

The MCP server acts as a bridge between Claude and your indexed codebase in Azure Cognitive Search, providing intelligent code search capabilities directly within Claude conversations.
