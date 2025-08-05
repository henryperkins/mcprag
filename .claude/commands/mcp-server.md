# MCP Server Operations

Run and manage the MCP (Model Context Protocol) server for Azure Search integration.

## Purpose

This command helps you start, test, and debug the MCP server that provides intelligent code search capabilities to Claude.

## Usage

```
/mcp-server
```

## Starting the Server

### Run the MCP Server
```bash
# Start the production server (recommended)
python -m mcprag

# Run the wrapper script (loads environment variables)
./mcp_server_wrapper.sh

# Run with debug logging
PYTHONPATH=. python -m mcprag
```

### Alternative Server Modes
```bash
# Run from package
python -m mcprag

# Run with specific config
python -m mcprag.server --config mcp_config.json
```

## Testing the Server

### Test MCP Protocol
```bash
# Basic protocol test
python test_mcp_protocol.py

# Test search functionality
python test_mcp_search_debug.py

# Test all MCP tools
python test_mcp_tools.py

# Run comprehensive test suite
python test_framework/mcp_test_runner.py
```

### Debug Search Issues
```bash
# Debug search directly
python scripts/debug_search.py

# Test single search query
python test_single_search.py

# Check search with timing
python tests/test_timing_enhancement.py
```

## MCP Tool Testing

### Available MCP Tools
- `search_code` - Semantic code search
- `search_code_raw` - Exact match search
- `preview_query_processing` - Query enhancement preview
- `explain_ranking` - Result ranking explanation
- `cache_stats` / `cache_clear` - Cache management
- `index_rebuild` - Trigger reindexing

### Test Individual Tools
```bash
# Test search tool
python -c "from mcprag.mcp.tools.search import search_code; import asyncio; asyncio.run(search_code({'query': 'authentication'}))"

# Test cache operations
python -c "from mcprag.mcp.tools.cache import cache_stats; import asyncio; asyncio.run(cache_stats())"
```

## Configuration

### MCP Server Config (`mcp_config.json`)
```json
{
  "server": {
    "host": "localhost",
    "port": 8001
  },
  "azure": {
    "endpoint": "${ACS_ENDPOINT}",
    "key": "${ACS_ADMIN_KEY}",
    "index": "codebase-mcp-sota"
  }
}
```

### Environment Variables
```bash
export ACS_ENDPOINT="https://your-search.search.windows.net"
export ACS_ADMIN_KEY="your-admin-key"
export ACS_INDEX_NAME="codebase-mcp-sota"
export AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
export AZURE_OPENAI_KEY="your-openai-key"
```

## Monitoring & Debugging

### Check Server Logs
```bash
# Tail server logs
tail -f mcp_server.log

# Check for errors
grep ERROR mcp_server.log

# Monitor performance
grep "Search completed in" mcp_server.log
```

### Health Checks
```bash
# Check Azure Search connection
python -m enhanced_rag.azure_integration.cli health-check

# Verify index health
python scripts/verify_index_health.py
```

## Best Practices

1. **Always check logs** when debugging issues
2. **Test tools individually** before full integration
3. **Monitor cache hit rates** for performance
4. **Validate index** before starting server
5. **Use wrapper script** for production deployment