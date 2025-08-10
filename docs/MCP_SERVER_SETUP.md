# Setting up MCPRAG as an MCP Server

This guide explains how to configure the MCPRAG (Model Context Protocol - Retrieval Augmented Generation) server to work with Claude Desktop or other MCP clients.

## Overview

MCPRAG is a powerful MCP server that provides advanced code search and retrieval capabilities using Azure AI Search. It offers:
- Semantic code search with multi-factor ranking
- Code generation with context
- Repository indexing and management
- Azure service integration
- Feedback-based learning system

## Prerequisites

1. **Python 3.12+** installed
2. **Azure AI Search** service configured with:
   - Admin API key
   - Search endpoint URL
   - Index created (default: `codebase-mcp-sota`)
3. **Azure OpenAI** (optional, for embeddings):
   - API endpoint
   - API key
   - Deployment for `text-embedding-3-large`

## Installation

### 1. Clone and Setup the Repository

```bash
# Clone the repository
git clone <your-repo-url> mcprag
cd mcprag

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required: Azure Search Configuration
ACS_ENDPOINT=https://<your-search-service>.search.windows.net
ACS_ADMIN_KEY=<your-admin-key>
ACS_INDEX_NAME=codebase-mcp-sota  # or your custom index name
AZURE_RESOURCE_GROUP=<your-resource-group>

# Optional: Azure OpenAI for embeddings
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com
AZURE_OPENAI_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT=text-embedding-3-large

# Optional: MCP Configuration
MCP_LOG_LEVEL=INFO  # DEBUG for troubleshooting
MCP_ADMIN_MODE=true  # Enable admin operations
MCP_CACHE_TTL_SECONDS=60
MCP_CACHE_MAX_ENTRIES=500
```

## Running the MCP Server

### Standalone Mode (stdio)

The default mode uses stdio for communication:

```bash
# Run the server
python -m mcprag
```

### Test the Server

Verify the server is working:

```bash
# Test basic functionality
python -c "import asyncio; from mcprag.mcp.tools.search import search_code; print(asyncio.run(search_code(query='server', max_results=3)))"
```

## Adding to Claude Desktop

### Method 1: Local Python Installation

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcprag": {
      "command": "python",
      "args": ["-m", "mcprag"],
      "cwd": "/path/to/mcprag",
      "env": {
        "ACS_ENDPOINT": "https://<your-search-service>.search.windows.net",
        "ACS_ADMIN_KEY": "<your-admin-key>",
        "ACS_INDEX_NAME": "codebase-mcp-sota",
        "AZURE_RESOURCE_GROUP": "<your-resource-group>",
        "AZURE_OPENAI_ENDPOINT": "https://<your-openai>.openai.azure.com",
        "AZURE_OPENAI_KEY": "<your-api-key>",
        "AZURE_OPENAI_DEPLOYMENT": "text-embedding-3-large",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_ADMIN_MODE": "true"
      }
    }
  }
}
```

### Method 2: Using Virtual Environment

If you're using a virtual environment:

```json
{
  "mcpServers": {
    "mcprag": {
      "command": "/path/to/mcprag/venv/bin/python",
      "args": ["-m", "mcprag"],
      "cwd": "/path/to/mcprag",
      "env": {
        "ACS_ENDPOINT": "https://<your-search-service>.search.windows.net",
        "ACS_ADMIN_KEY": "<your-admin-key>",
        "ACS_INDEX_NAME": "codebase-mcp-sota",
        "AZURE_RESOURCE_GROUP": "<your-resource-group>",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Method 3: Using Environment Variables

If you have environment variables already configured in your shell:

```json
{
  "mcpServers": {
    "mcprag": {
      "command": "python",
      "args": ["-m", "mcprag"],
      "cwd": "/path/to/mcprag"
    }
  }
}
```

## Adding to Claude Code

You can also add MCPRAG to Claude Code using the CLI:

```bash
# First, navigate to your mcprag directory
cd /path/to/mcprag

# Add as a local stdio server (will use .env file in the mcprag directory)
claude mcp add mcprag -- python -m mcprag

# With environment variables from .env file (one-liner)
claude mcp add mcprag $(grep -v '^#' .env | xargs -I {} echo --env {}) -- python -m mcprag

# Or use a helper script to load .env and add the server
cat << 'EOF' > add_mcprag.sh
#!/bin/bash
# Load environment variables from .env file
set -a
source .env
set +a

# Add mcprag with all environment variables
claude mcp add mcprag \
  --env ACS_ENDPOINT="$ACS_ENDPOINT" \
  --env ACS_ADMIN_KEY="$ACS_ADMIN_KEY" \
  --env ACS_INDEX_NAME="$ACS_INDEX_NAME" \
  --env AZURE_RESOURCE_GROUP="$AZURE_RESOURCE_GROUP" \
  --env AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
  --env AZURE_OPENAI_KEY="$AZURE_OPENAI_KEY" \
  --env AZURE_OPENAI_DEPLOYMENT="$AZURE_OPENAI_DEPLOYMENT" \
  --env MCP_LOG_LEVEL="$MCP_LOG_LEVEL" \
  --env MCP_ADMIN_MODE="$MCP_ADMIN_MODE" \
  -- python -m mcprag
EOF
chmod +x add_mcprag.sh
./add_mcprag.sh

# Add to project scope (shared with team via .mcp.json)
claude mcp add mcprag --scope project -- python -m mcprag

# Or use absolute path to Python in virtual environment
claude mcp add mcprag -- /path/to/mcprag/venv/bin/python -m mcprag
```

## Available MCP Tools

Once connected, you'll have access to these tools:

### Search Tools
- **search_code**: Advanced code search with semantic ranking
- **search_code_raw**: Raw search results without formatting
- **search_microsoft_docs**: Search Microsoft Learn documentation

### Code Generation
- **generate_code**: Generate code using RAG context

### Analysis Tools
- **analyze_context**: Analyze file context with dependencies
- **explain_ranking**: Understand search result ranking
- **preview_query_processing**: Preview query enhancements

### Admin Tools (require MCP_ADMIN_MODE=true)
- **index_rebuild**: Rebuild search indexer
- **github_index_repo**: Index GitHub repository
- **manage_index**: Index lifecycle management
- **manage_documents**: Document operations
- **manage_indexer**: Indexer operations
- **index_status**: Get index status
- **index_repository**: Index local repository

### Cache Management
- **cache_stats**: View cache statistics
- **cache_clear**: Clear cache entries

### Feedback Tools
- **submit_feedback**: Submit user feedback
- **track_search_click**: Track search result clicks
- **track_search_outcome**: Track search outcomes

## Using the MCP Server

Once configured, you can use MCPRAG in Claude Desktop or Claude Code by:

1. **Search for code**: "Search for the implementation of the RAG pipeline"
2. **Generate code**: "Generate a function to process Azure search results"
3. **Analyze context**: "Show me the dependencies of the server.py file"
4. **Index repositories**: "Index the current repository for searching"
5. **Manage index**: "Show the status of the search index"

## Troubleshooting

### Server Won't Start

1. Check Python version: `python --version` (must be 3.12+)
2. Verify environment variables are set correctly
3. Test Azure connection:
   ```python
   import os
   print(os.getenv("ACS_ENDPOINT"))
   print(os.getenv("ACS_ADMIN_KEY"))
   ```
4. Enable debug logging: Set `MCP_LOG_LEVEL=DEBUG`

### Connection Issues in Claude Desktop

1. Verify the path to Python is correct
2. Check the working directory (cwd) exists
3. Review Claude Desktop logs for error messages
4. Test the server runs standalone first

### Search Not Working

1. Verify index exists and has documents:
   ```bash
   python -c "from mcprag.mcp.tools.admin import index_status; import asyncio; print(asyncio.run(index_status()))"
   ```
2. Check Azure Search service is running
3. Verify API keys have proper permissions

### Windows-Specific Issues

On Windows (not WSL), you may need to use the `cmd /c` wrapper:

```json
{
  "mcpServers": {
    "mcprag": {
      "command": "cmd",
      "args": ["/c", "python", "-m", "mcprag"],
      "cwd": "C:\\path\\to\\mcprag"
    }
  }
}
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Admin Mode**: Only enable `MCP_ADMIN_MODE` when needed
3. **Network Access**: Ensure your Azure services are properly secured
4. **Index Access**: Use read-only keys for production search operations

## Advanced Configuration

### Custom Index Schema

To use a custom index schema, update the `azure_search_index_schema.json` file and ensure your index matches the expected fields.

### Performance Tuning

Adjust these environment variables for performance:

```bash
MCP_CACHE_TTL_SECONDS=300  # Increase cache TTL
MCP_CACHE_MAX_ENTRIES=1000  # Increase cache size
MCP_MAX_INDEX_FILES=10000  # Limit files during indexing
MCP_DEBUG_TIMINGS=true  # Enable performance logging
```

### Multi-Repository Support

MCPRAG supports indexing and searching across multiple repositories. Use the `repository` parameter in search queries to filter results.

## Getting Help

- Check the [CLAUDE.md](../CLAUDE.md) file for detailed project information
- Review logs with `MCP_LOG_LEVEL=DEBUG` for detailed error messages
- Consult the MCP documentation at https://modelcontextprotocol.io