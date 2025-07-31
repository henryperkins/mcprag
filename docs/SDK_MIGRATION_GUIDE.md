# SDK Migration Guide: From Manual MCP to SDK-based Implementation

This guide explains how to migrate from the manual JSON-RPC MCP implementation to the official SDK-based approach.

## Overview of Changes

### Current Implementation (Manual)
- Direct JSON-RPC protocol handling
- Manual request/response formatting  
- Static tool definitions as dictionaries
- Custom error handling
- Manual transport management

### SDK-Based Implementation
- Declarative tool definitions with decorators
- Automatic protocol handling
- Type-safe parameters with Pydantic
- Built-in error handling
- Multiple transport options

## Migration Steps

### 1. Update Dependencies

Add the MCP SDK to requirements.txt:
```txt
mcp-sdk>=1.0.0  # Replace with actual package name when available
pydantic>=2.0.0
```

### 2. Replace Manual Protocol Handling

**Before (Manual):**
```python
async def handle_request(request: dict):
    method = request.get("method")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}}
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {"tools": tools}
        }
```

**After (SDK):**
```python
from mcp import Server

server = Server(name="azure-code-search", version="2.0.0")

# Protocol handling is automatic
# Capabilities are determined from registered tools
```

### 3. Convert Tool Definitions

**Before (Manual):**
```python
tools = [
    {
        "name": "search_code",
        "description": "Search for code snippets",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "intent": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]
```

**After (SDK):**
```python
from pydantic import BaseModel

class SearchCodeParams(BaseModel):
    query: str
    intent: Optional[str] = None

@server.tool(description="Search for code snippets")
async def search_code(params: SearchCodeParams) -> List[SearchResult]:
    # Implementation
```

### 4. Update Tool Implementations

**Before (Manual):**
```python
if method == "tools/call":
    tool_name = request["params"]["name"]
    arguments = request["params"]["arguments"]
    
    if tool_name == "search_code":
        result = await search_code_impl(arguments["query"])
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "content": [{
                    "type": "text",
                    "text": format_results(result)
                }]
            }
        }
```

**After (SDK):**
```python
@server.tool()
async def search_code(params: SearchCodeParams) -> List[SearchResult]:
    # Direct implementation, no manual formatting needed
    results = await search_code_impl(params.query)
    return results  # SDK handles serialization
```

### 5. Add Lifecycle Management

**New with SDK:**
```python
@server.on_initialize
async def initialize():
    # Setup resources
    server.search_client = SearchClient(...)
    server.embedder = VectorEmbedder()

@server.on_shutdown  
async def cleanup():
    # Cleanup resources
    await server.search_client.close()
```

### 6. Enhance with SDK Features

**Add Resources:**
```python
@server.resource(uri="repositories")
async def list_repositories():
    return {"repositories": [...]}
```

**Add Prompts:**
```python
@server.prompt(name="debug_assistance")
async def debug_prompt(error: str):
    return f"Help debug: {error}"
```

**Add Structured Output:**
```python
class SearchResult(BaseModel):
    file_path: str
    score: float
    content: str

@server.tool(output_schema=List[SearchResult])
async def search_code(...) -> List[SearchResult]:
    # Returns validated data
```

### 7. Update Transport Layer

**Before (Manual):**
```python
# Custom stdio handling
async def main():
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(
        lambda: protocol, sys.stdin
    )
    # Complex message parsing...
```

**After (SDK):**
```python
from mcp.server.stdio import StdioServer

async def main():
    transport = StdioServer()
    await server.run(transport)
```

### 8. Testing the Migration

1. **Parallel Testing**: Run both servers side-by-side
2. **Compare Outputs**: Ensure responses match
3. **Performance Testing**: SDK should have similar or better performance
4. **Feature Testing**: Test new SDK features (resources, prompts)

### 9. Update Client Integration

**Update MCP Configuration:**
```json
{
  "mcps": {
    "azure-code-search": {
      "command": "python",
      "args": ["mcp_server_sdk.py"],
      "env": {
        "ACS_ENDPOINT": "...",
        "ACS_ADMIN_KEY": "..."
      }
    }
  }
}
```

## Benefits After Migration

1. **Less Code**: ~50% reduction in boilerplate
2. **Type Safety**: Full IDE support and validation
3. **Better Errors**: Automatic error handling and reporting
4. **More Features**: Resources, prompts, structured output
5. **Future Proof**: Automatic protocol updates
6. **Testing**: Built-in testing utilities
7. **Documentation**: Auto-generated from decorators

## Common Pitfalls

1. **Async/Await**: Ensure all tool functions are async
2. **Return Types**: Must match output_schema if specified
3. **Error Handling**: Use ToolError for tool-specific errors
4. **Resource URIs**: Must be unique across resources
5. **Transport Selection**: Choose appropriate transport for deployment

## Rollback Plan

If issues arise:
1. Keep the original manual implementation as backup
2. Use feature flags to switch between implementations
3. Gradual migration: Convert one tool at a time
4. Monitor error rates and performance

## Next Steps

1. Test the SDK implementation thoroughly
2. Update documentation and examples
3. Plan deployment with gradual rollout
4. Monitor metrics and user feedback
5. Remove manual implementation after stability confirmed