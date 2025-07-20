# Microsoft Docs MCP Integration

## Overview

This integration adds Microsoft Learn documentation search capabilities to your MCP server, enabling unified search across both your codebase and Microsoft's official documentation.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Claude Code /  │     │   MCP Server SOTA    │     │   Search Backends   │
│   Other MCP     │────▶│  (mcp_server_sota.py)│────▶├─────────────────────┤
│    Clients      │     │                      │     │ Azure Cognitive     │
└─────────────────┘     │  Tools:              │     │ Search (Your Code)  │
                        │  - search_code        │     ├─────────────────────┤
                        │  - search_microsoft_  │     │ Microsoft Docs MCP  │
                        │    docs               │     │ (learn.microsoft.com)│
                        └──────────────────────┘     └─────────────────────┘
```

## Components

### 1. Microsoft Docs MCP Client (`microsoft_docs_mcp_client.py`)
- Handles HTTP communication with Microsoft's MCP server
- Supports Server-Sent Events (SSE) format
- Provides async context manager for proper resource cleanup

### 2. Enhanced MCP Server (`mcp_server_sota.py`)
- Integrated Microsoft Docs search as a new tool
- Maintains existing code search functionality
- Provides unified MCP interface for both tools

### 3. Configuration (`mcp-servers.json`)
```json
{
    "mcpServers": {
        "azure-code-search": {
            // Your existing code search configuration
        },
        "microsoft-docs": {
            "type": "http",
            "url": "https://learn.microsoft.com/api/mcp"
        }
    }
}
```

## Usage

### Through MCP Protocol

1. **List available tools:**
```json
{
    "method": "tools/list"
}
```
Response will include both `search_code` and `search_microsoft_docs`.

2. **Search your codebase:**
```json
{
    "method": "tools/call",
    "params": {
        "name": "search_code",
        "arguments": {
            "query": "vector search implementation",
            "intent": "understand",
            "language": "python"
        }
    }
}
```

3. **Search Microsoft documentation:**
```json
{
    "method": "tools/call",
    "params": {
        "name": "search_microsoft_docs",
        "arguments": {
            "query": "Azure Cognitive Search vector search",
            "max_results": 5
        }
    }
}
```

### Direct Python Usage

```python
from microsoft_docs_mcp_client import MicrosoftDocsMCPClient

async with MicrosoftDocsMCPClient() as client:
    # Basic search
    results = await client.search_docs("Azure Functions Python")
    
    # Context-aware search
    results = await client.search_with_context(
        "Azure SDK",
        context={"language": "Python", "framework": "asyncio"}
    )
```

## Features

- **Unified Search**: Single interface for both code and documentation
- **Semantic Search**: Microsoft's MCP uses semantic search for better results
- **Real-time Updates**: Always gets the latest Microsoft documentation
- **Parallel Execution**: Can search both sources simultaneously
- **Error Handling**: Graceful handling of SSE format and API errors

## Testing

Run the test suite:
```bash
source venv/bin/activate
python test_microsoft_docs_search.py
```

Run the example usage:
```bash
python example_microsoft_docs_usage.py
```

## Best Practices

1. **Use specific technical terms** in queries for better results
2. **Combine searches** - search your code for implementation and Microsoft docs for API reference
3. **Use intent parameter** for code searches to optimize results
4. **Limit results** appropriately - Microsoft returns up to 10 chunks (500 tokens each)

## Troubleshooting

1. **SSE Format Issues**: The client automatically handles Server-Sent Events format
2. **Network Issues**: Ensure you can reach `https://learn.microsoft.com/api/mcp`
3. **No Results**: Try more specific technical terms in your query

## Current Status

- ✅ Integration complete and functional
- ✅ Both tools available through unified MCP interface
- ⚠️ Microsoft Docs MCP is in "Public Preview" - expect potential changes
- ⚠️ Microsoft's server may have occasional availability issues

## Future Enhancements

1. **Result Ranking**: Combine and rank results from both sources
2. **Caching**: Cache frequently searched Microsoft docs
3. **Query Enhancement**: Use code context to enhance Microsoft docs queries
4. **Filtering**: Add filters for Microsoft products/services