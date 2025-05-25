# Azure Cognitive Search + MCP Server SOTA (2025 Preview)

A state-of-the-art code search solution using Azure Cognitive Search 2025 preview features with intelligent AST-based chunking, semantic understanding, and advanced MCP (Model Context Protocol) integration optimized for Claude Code.

## SOTA Features

- **AST-Based Code Analysis** - Intelligent function/class extraction with dependency tracking
- **Semantic Context Building** - Rich context with imports, function calls, and documentation
- **Intent-Aware Search** - Query enhancement based on implementation/debug/understand/refactor intents
- **Cross-File Dependency Resolution** - Automatic inclusion of related functions and dependencies
- **MCP-Optimized Results** - Structured context specifically designed for Claude Code integration
- **2025 Preview Features** - Text-to-vector conversion, query rewrites, hybrid search

## Quick Start

### 1. Azure Setup

```bash
# Login to Azure
az login

# Create resource group
az group create --name mcprag-rg --location eastus

# Create Azure Cognitive Search service (Basic tier)
az search service create \
  --name mcprag-search \
  --resource-group mcprag-rg \
  --sku basic \
  --location eastus

# Get admin key
az search admin-key show \
  --service-name mcprag-search \
  --resource-group mcprag-rg
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Azure details
# ACS_ENDPOINT=https://mcprag-search.search.windows.net
# ACS_ADMIN_KEY=your-admin-key-from-above
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Search Index

```bash
python create_index.py
```

### 5. Index Your Code with AST Analysis

```bash
# Edit smart_indexer.py to point to your repository
# Then run:
python smart_indexer.py
```

### 6. Start SOTA MCP Server

```bash
python mcp_server_sota.py
```

## Usage

### Direct API

```bash
# Health check
curl http://localhost:8001/health

# Enhanced MCP search with intent
curl -X POST http://localhost:8001/mcp-query \
  -H "Content-Type: application/json" \
  -d '{
    "input": "authentication function",
    "intent": "implement",
    "context": {
      "current_language": "python",
      "imported_modules": ["jwt", "hashlib"]
    }
  }'
```

### Claude Code Integration

```bash
# Register with Claude Code
claude-code mcp add \
  --name azure-code-search \
  --type http \
  --url http://localhost:8001/mcp-query \
  --method POST
```

## Docker Deployment

```bash
# Build image
docker build -t mcp-server .

# Run container
docker run -p 8001:8001 --env-file .env mcp-server
```

## Customization

### Index Different Repositories

Edit `smart_indexer.py`:

```python
if __name__ == "__main__":
    chunker = CodeChunker()
    chunker.index_repository("./path/to/repo1", "project-name-1")
    chunker.index_repository("./path/to/repo2", "project-name-2")
```

### Extend Language Support

Add language-specific chunking methods to `CodeChunker` class:

```python
def chunk_javascript_file(self, content: str, file_path: str) -> List[Dict]:
    # Add JavaScript AST parsing logic
    pass
```

### Customize Search Intents

Modify intent enhancement in `mcp_server_sota.py`:

```python
intent_prefixes = {
    "implement": f"implementation example code for {query}",
    "debug": f"error handling exception catching for {query}",
    "optimize": f"performance optimization patterns for {query}",
    "test": f"unit test examples for {query}"
}
```

## Cost Estimation

- **Azure Cognitive Search (Basic)**: ~$75/month
- **API Calls**: ~$175/month (varies by usage)
- **Total**: ~$250/month

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Code Repos    │───▶│   Indexer.py     │───▶│  Azure Search   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│  Claude Code    │───▶│  MCP Server      │◀────────────┘
└─────────────────┘    └──────────────────┘
```

## Troubleshooting

### Index Creation Fails
- Verify your Azure Search service is running
- Check that you're using the correct endpoint and admin key
- Ensure you have sufficient permissions

### Search Returns No Results
- Verify documents were indexed successfully
- Check that the search query matches indexed content
- Try simpler queries first

### MCP Integration Issues
- Ensure the server is running on port 8001
- Verify Claude Code can reach the endpoint
- Check the request/response format matches expectations

## SOTA Improvements Over Basic Implementation

### 🧠 **Intelligent Code Understanding**
- **AST-Based Chunking**: Functions and classes extracted with proper context
- **Dependency Tracking**: Automatically identifies function calls and imports
- **Semantic Context**: Rich descriptions for better retrieval accuracy

### 🎯 **MCP-Optimized Integration**
- **Intent-Aware Queries**: Different search strategies for implement/debug/understand/refactor
- **Context-Aware Filtering**: Uses Claude's current file/language context
- **Cross-File Dependencies**: Automatically includes related functions

### 🚀 **2025 Preview Features**
- **Text-to-Vector Conversion**: Automatic embedding generation
- **Query Rewrites**: AI-generated query variations for better recall
- **Hybrid Search**: Combines semantic and keyword search
- **Similarity Thresholds**: Quality-based result filtering

### 📊 **Enhanced Results**
- **Structured Context**: File, function, imports, dependencies in one response
- **Relevance Scoring**: Prioritizes most relevant code snippets
- **Dependency Resolution**: Includes called functions for complete context

## License

MIT License - see LICENSE file for details.
