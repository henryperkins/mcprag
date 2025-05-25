# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the SOTA MCP server
python mcp_server_sota.py

# Create Azure search index
python create_index.py

# Index repository with smart chunking
python smart_indexer.py --repo-path ./path/to/repo --repo-name project-name

# Index only changed files (for CI/CD)
python smart_indexer.py --files file1.py file2.js

# Basic indexing (legacy)
python indexer.py

# Test setup
python test_setup.py

# Check status
python status.py
```

### JavaScript/TypeScript
```bash
# Parse JS/TS files for AST analysis
node parse_js.mjs path/to/file.js
```

### Docker
```bash
# Build and run
docker build -t mcp-server .
docker run -p 8001:8001 --env-file .env mcp-server
```

## Architecture Overview

This is a **state-of-the-art code search solution** that combines Azure Cognitive Search with intelligent AST-based code analysis for MCP (Model Context Protocol) integration with Claude Code.

### Core Components

1. **Smart Indexer (`smart_indexer.py`)** - AST-based code chunking system
   - Extracts semantic meaning from Python functions/classes using `ast` module
   - Parses JavaScript/TypeScript via Babel AST (`parse_js.mjs`)
   - Creates rich context: function signatures, imports, function calls, docstrings
   - Supports incremental indexing of changed files

2. **SOTA MCP Server (`mcp_server_sota.py`)** - Advanced search API
   - Intent-aware query enhancement (implement/debug/understand/refactor)
   - Multi-stage retrieval with semantic + hybrid search
   - Context-aware filtering based on current file/language
   - Cross-file dependency resolution
   - Uses Azure Cognitive Search 2025 preview features

3. **Azure Search Integration**
   - Index: `codebase-mcp-sota` (SOTA) or `codebase-search` (basic)
   - Vector search with similarity thresholds
   - Semantic configuration for better code understanding
   - Query rewrites for enhanced recall

### Key Differences from Basic Implementation

- **AST Analysis**: Extracts actual function signatures, imports, and call graphs
- **Semantic Context**: Rich descriptions for better retrieval accuracy  
- **Intent Processing**: Different search strategies based on user intent
- **Dependency Tracking**: Automatically includes related functions
- **MCP Optimization**: Structured responses designed for Claude Code integration

### File Processing Flow

```
Code Files → AST Parser → Semantic Chunks → Azure Search → MCP Server → Claude Code
```

1. **Python**: Uses `ast` module to extract functions/classes with full context
2. **JS/TS**: Uses Babel parser via Node.js subprocess for AST analysis
3. **Chunking**: Creates semantic chunks with function signatures, imports, calls
4. **Indexing**: Stores in Azure Search with vector embeddings
5. **Retrieval**: Intent-aware search with dependency resolution

### Environment Configuration

Required in `.env`:
- `ACS_ENDPOINT` - Azure Cognitive Search endpoint
- `ACS_ADMIN_KEY` - Azure admin key

### Testing

The repository includes GitHub webhook integration (`github_webhook_handler.py`) for automatic re-indexing on code changes. Azure deployment scripts are in `setup_azure.py` and `deploy.py`.