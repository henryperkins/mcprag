# Copilot Instructions for Azure Code Search MCP Server

## Project Overview

This is a **state-of-the-art code search solution** that combines Azure Cognitive Search with intelligent AST-based code analysis for MCP (Model Context Protocol) integration. The system provides semantic code search capabilities to AI coding assistants like Claude Code.

## Core Architecture

### Three-Layer Search Pipeline
```
Code Files → AST Parser → Semantic Chunks → Azure Search → MCP Server → AI Assistant
```

1. **Smart Indexer (`smart_indexer.py`)** - AST-based code chunking
   - Python: Uses `ast` module for function/class extraction with full context
   - JS/TS: Uses Babel parser via `parse_js.mjs` Node.js subprocess
   - Creates semantic chunks with signatures, imports, function calls, docstrings

2. **SOTA MCP Server (`mcp_server_sota.py`)** - Advanced search API
   - Intent-aware query enhancement (implement/debug/understand/refactor)
   - Multi-stage retrieval with semantic + hybrid search
   - Context-aware filtering based on current file/language
   - Cross-file dependency resolution

3. **Azure Search Integration** - Vector + keyword search with 2025 preview features

### Key Differences from Basic Implementations
- **AST Analysis**: Extracts actual function signatures, not just text chunks
- **Semantic Context**: Rich descriptions for better retrieval accuracy
- **Intent Processing**: Different search strategies based on user intent
- **Dependency Tracking**: Automatically includes related functions

## Essential Development Workflows

### Environment Setup
```bash
# Always activate virtual environment first
source .venv/bin/activate  # or source /home/azureuser/mcprag/.venv/bin/activate

# Install dependencies (Python + Node.js)
pip install -r requirements.txt
npm install  # For Babel AST parsing
```

### Core Commands
```bash
# Create Azure search index (run once)
python create_index.py

# Index repository with smart chunking
python smart_indexer.py --repo-path ./path/to/repo --repo-name project-name

# Start SOTA MCP server (main entry point)
python mcp_server_sota.py

# Test MCP tools registration
python tests/test_mcp_tools.py

# Run all tests
pytest
```

### Incremental Indexing Pattern
```bash
# Index only changed files (for CI/CD)
python smart_indexer.py --files file1.py file2.js

# Auto-index on file changes
python auto_index_on_change.py
```

## Project-Specific Conventions

### Graceful Degradation Pattern
All optional dependencies use try/except imports with functional stubs:
```python
try:
    from azure.search.documents import SearchClient
except ImportError:
    class _DummySearchClient:
        def upload_documents(self, *_, **__): return None
    SearchClient = _DummySearchClient
```

### AST Processing Convention
- Python files: Direct `ast` module usage in `smart_indexer.py`
- JS/TS files: Subprocess call to `parse_js.mjs` with JSON communication
- Both return standardized chunk format: `{type, name, signature, start_line, end_line}`

### MCP Integration Patterns
- Tools use Pydantic models for type safety (`SearchIntent`, `SearchCodeParams`)
- Intent-aware query enhancement with predefined prefixes
- Structured responses with file context, dependencies, and metadata

### Testing Strategy
- Unit tests use Azure SDK stubs for offline testing
- Integration tests require real Azure credentials
- MCP tools tested via JSON-RPC subprocess communication

## Critical Integration Points

### Azure Search Configuration
- Index name: `codebase-mcp-sota` (SOTA) or `codebase-search` (basic)
- Required fields: `content`, `file_path`, `function_name`, `repository`
- Vector fields: `content_vector` (1536 dimensions for OpenAI embeddings)
- Environment: `ACS_ENDPOINT`, `ACS_ADMIN_KEY` in `.env`

### MCP Server Registration
```json
{
  "mcps": {
    "azure-code-search": {
      "command": "python",
      "args": ["/path/to/mcp_server_sota.py"],
      "env": {"ACS_ENDPOINT": "...", "ACS_ADMIN_KEY": "..."}
    }
  }
}
```

### Enhanced RAG Pipeline (Optional)
- Located in `enhanced_rag/` directory
- Provides advanced search, code generation, and context-aware tools
- Gracefully degrades if not available

## Key Files for Understanding

- `mcp_server_sota.py` - Main MCP server with intent-aware search
- `smart_indexer.py` - AST-based code chunking and indexing
- `parse_js.mjs` - JavaScript/TypeScript AST parsing via Babel
- `vector_embeddings.py` - OpenAI embeddings with graceful fallback
- `tests/test_mcp_tools.py` - MCP integration testing pattern
- `CLAUDE.md` - Comprehensive usage guide for Claude Code integration

## Common Debugging Patterns

### Check Index Status
```bash
python status.py  # Shows indexed repositories and document counts
```

### Validate MCP Tools
```bash
python tests/test_mcp_tools.py  # Tests tool registration via JSON-RPC
```

### Debug Search Results
```bash
# Direct API testing
curl -X POST http://localhost:8001/mcp-query \
  -H "Content-Type: application/json" \
  -d '{"input": "authentication function", "intent": "implement"}'
```

When working with this codebase, prioritize understanding the AST-based chunking approach and intent-aware search patterns, as these differentiate it from simpler text-based search implementations.
