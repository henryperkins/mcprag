# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Search Tool Priority

**ALWAYS use the MCP-provided `mcp__azure-code-search__search_code` tool for code searches instead of built-in Grep/Glob tools.**

When you need to search the codebase:
1. First choice: Use `mcp__azure-code-search__search_code` - it provides semantic search with better context understanding
2. Only use Grep/Glob if specifically looking for exact string matches or file patterns
3. The MCP search tool offers:
   - Intent-aware search (implement/debug/understand/refactor)
   - Semantic understanding of code
   - Cross-file dependency resolution
   - Better ranking based on code context

### Effective MCP Search Strategies

#### Query Construction Guidelines
- **USE NATURAL LANGUAGE**: Describe what the code DOES, not what text it contains
  - ✅ Good: "index schema vector field definition"
  - ✅ Good: "where are embeddings generated"
  - ✅ Good: "vector dimension configuration"
  - ❌ Bad: "vector issue problem error" (too generic)
  - ❌ Bad: "SearchField vector_field dimensions 1536" (too literal)

#### Intent Selection
- `understand`: Best for learning how features work and finding definitions
- `implement`: Finding code patterns to implement similar functionality
- `debug`: Locating error handling, validation, and troubleshooting code
- `refactor`: Finding code that needs improvement

#### Interpreting Results
- **Relevance Scores**: 0.02-0.04 are typical for semantic matches (not exact matches)
- **Low scores across all results**: Query is likely too broad or misaligned
- **File Context**: Shows imports, functions called, and purpose
- **Consider refining queries** when all results have scores < 0.05

### Common Search Patterns

```python
# Finding schema/configuration definitions
"create index schema fields"              # Find where index is created
"embedding dimension configuration"       # Find dimension settings
"{feature} configuration settings"        # Find config for specific feature

# Understanding implementation
"how does {feature} process {data}"      # Data flow understanding
"{class_name} implementation"            # Find class implementation
"where is {function} called"             # Find usage patterns

# Debugging issues
"{feature} validation"                   # Find validation logic
"error handling for {operation}"         # Find error handlers
"{component} initialization"             # Find setup/init code

# Architecture discovery
"builder pattern for {component}"        # Find builders
"handler for {event_type}"              # Find event handlers
"pipeline stages"                        # Find processing pipelines
```

### Handling Poor Search Results

When MCP returns irrelevant results:
1. **Avoid generic debugging terms**: "error", "issue", "problem", "fix"
2. **Use architectural terms**: "schema", "builder", "handler", "config", "pipeline"
3. **Try different intents**: Start with "understand" for exploration
4. **Break complex searches into steps**:
   ```
   Instead of: "vector dimension mismatch error ValueError"
   Try:
   1. "vector field schema definition"     # Find the schema
   2. "embedding dimension configuration"  # Find the config
   3. "vector search validation"          # Find validation
   ```

### Result Optimization Tips
- **Increase max_results** to 20-30 when exploring unfamiliar code
- **Use language parameter** when working in multi-language codebases
- **Include repository filter** when you know the target location
- **Combine with Grep** for verification after finding the right area

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

## Testing & Quality Assurance

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/test_mcp_tools.py

# Test MCP tools registration
python tests/test_mcp_tools.py
```

### Code Quality Tools
```bash
# Python linting
flake8

# Type checking
mypy .

# Security scanning
bandit -r .

# Check dependency vulnerabilities
safety check
```

### CI/CD Integration

The repository includes GitHub webhook integration (`github_webhook_handler.py`) for automatic re-indexing on code changes. Azure deployment scripts are in `setup_azure.py` and `deploy.py`.

## Deployment & Production

### Azure Setup
```bash
# Login to Azure
az login

# Create resources
python setup/setup_azure.py

# Deploy to Azure
python setup/deploy.py
```

### Docker Deployment
```bash
# Build image
docker build -t mcp-server .

# Run container
docker run -p 8001:8001 --env-file .env mcp-server
```

### Cleanup
```bash
# Remove local files only
python setup/cleanup_local.py

# Complete uninstall (Azure + local)
python setup/uninstall.py  # WARNING: Deletes all Azure resources
```

## Claude Code Integration

### Adding this MCP Server to Claude Code

1. **Start the MCP server**:
   ```bash
   python mcp_server_sota.py
   ```

2. **Register with Claude Code** (in a separate terminal):
   ```bash
   # Add the code search MCP server
   claude-code mcp add \
     --name azure-code-search \
     --type http \
     --url http://localhost:8001/mcp-query \
     --method POST

   # If using the config file directly, add to mcp-servers.json:
   # {
   #   "mcps": {
   #     "azure-code-search": {
   #       "command": "python",
   #       "args": ["/path/to/mcp_server_sota.py"],
   #       "env": {
   #         "ACS_ENDPOINT": "your-endpoint",
   #         "ACS_ADMIN_KEY": "your-key"
   #       }
   #     }
   #   }
   # }
   ```

3. **Using in Claude Code**:
   - The MCP tools `mcp__azure-code-search__search_code` and `mcp__azure-code-search__search_microsoft_docs` will be available
   - Example: "Search for authentication functions" will use the code search
   - Example: "Find Microsoft docs about Azure Functions" will use the docs search

### Recommended Hooks

To maintain code quality and keep the search index updated, consider adding these hooks to your Claude Code settings:

```json
{
  "hooks": {
    "post-file-change": [
      {
        "command": "python smart_indexer.py --files {files}",
        "description": "Re-index changed files for search"
      }
    ],
    "pre-commit": [
      {
        "command": "flake8 {staged_files}",
        "description": "Lint Python files before commit"
      },
      {
        "command": "mypy {staged_files}",
        "description": "Type check Python files"
      }
    ]
  }
}
```

This ensures:
- Changed files are automatically re-indexed for search
- Code quality checks run before commits
- Type safety is maintained

### Using with Claude Code SDK

This MCP server can be integrated with the Claude Code SDK for programmatic code search:

```python
from claude_code_sdk import ClaudeCodeClient

# Initialize client
client = ClaudeCodeClient()

# Ensure MCP server is running
# python mcp_server_sota.py

# Use the code search tool
results = await client.use_mcp_tool(
    server_name="azure-code-search",
    tool_name="search_code",
    arguments={
        "query": "authentication middleware",
        "intent": "implement",
        "language": "python"
    }
)

# Search Microsoft docs
docs = await client.use_mcp_tool(
    server_name="azure-code-search", 
    tool_name="search_microsoft_docs",
    arguments={
        "query": "Azure Functions triggers",
        "max_results": 5
    }
)
```

For building extensions or automated workflows, see the [Claude Code SDK documentation](https://docs.anthropic.com/en/docs/claude-code/sdk).

### Advanced SDK Integration Patterns

The codebase includes `mcp_server_sdk.py` as an example of SDK-based implementation with advanced features:

1. **Type-Safe Tool Definitions**:
   ```python
   @server.tool(input_schema=SearchCodeParams, output_schema=List[SearchResult])
   async def search_code(params: SearchCodeParams) -> List[SearchResult]:
       # Fully typed implementation with validation
   ```

2. **Resource Endpoints**:
   ```python
   @server.resource(uri="repositories")
   async def list_repositories() -> Dict[str, Any]:
       # Expose repository list as a resource
   ```

3. **Prompt Templates**:
   ```python
   @server.prompt(name="implement_feature")
   async def implement_feature_prompt(feature_description: str) -> str:
       # Reusable prompt for feature implementation
   ```

4. **Lifecycle Management**:
   ```python
   @server.on_initialize
   async def initialize():
       # Setup Azure clients, embedder, etc.
   ```

5. **Structured Output with Pydantic**:
   - `SearchResult` model for code search results
   - `DocsResult` model for documentation results
   - Automatic validation and serialization

### Client SDK Usage Examples

```python
# Advanced usage with error handling and retries
from claude_code_sdk import ClaudeCodeClient, MCPError
import asyncio

async def smart_code_search(query: str, context: dict = None):
    client = ClaudeCodeClient()
    
    try:
        # Search with context awareness
        results = await client.use_mcp_tool(
            server_name="azure-code-search",
            tool_name="search_code",
            arguments={
                "query": query,
                "intent": context.get("intent", "understand"),
                "language": context.get("language"),
                "repository": context.get("repo", "*")
            }
        )
        
        # Process results with dependency resolution
        if results and context.get("include_dependencies"):
            for result in results[:3]:  # Top 3 results
                deps = await client.use_mcp_tool(
                    server_name="azure-code-search",
                    tool_name="search_code",
                    arguments={
                        "query": f"functions called by {result['function_name']}",
                        "repository": result['repository']
                    }
                )
                result['dependencies'] = deps
                
        return results
        
    except MCPError as e:
        # Handle MCP-specific errors
        print(f"MCP Error: {e}")
        return []

# Batch operations
async def index_and_search(file_paths: List[str], search_query: str):
    # Index files
    subprocess.run(["python", "smart_indexer.py", "--files"] + file_paths)
    
    # Wait for indexing to complete
    await asyncio.sleep(2)
    
    # Search indexed content
    return await smart_code_search(search_query)

# Using prompt templates
async def get_implementation_plan(feature: str):
    client = ClaudeCodeClient()
    
    # Get prompt from template
    prompt = await client.use_mcp_prompt(
        server_name="azure-code-search",
        prompt_name="implement_feature",
        arguments={"feature_description": feature}
    )
    
    # Use Claude with the generated prompt
    response = await client.chat(prompt)
    return response
```

### Building Custom MCP Extensions

For creating your own MCP tools that integrate with this codebase:

```python
from mcp import Server

# Extend the code search with custom tools
@server.tool()
async def analyze_code_quality(file_path: str) -> dict:
    # Run static analysis
    result = subprocess.run(["flake8", file_path], capture_output=True)
    
    # Search for similar quality issues
    similar_issues = await search_code(SearchCodeParams(
        query=f"flake8 {result.stdout.decode()}",
        intent="debug"
    ))
    
    return {
        "issues": result.stdout.decode().split('\n'),
        "similar_fixes": similar_issues
    }
```

## Azure Cognitive Search Advanced Features

### Enhanced Search Implementation

The repository includes `azure_search_enhanced.py` demonstrating advanced Azure Search features:

1. **Custom Code Analyzers**:
   - CamelCase analyzer for Java/C# style code
   - Snake_case analyzer for Python style
   - Import path analyzer for package structures

2. **Scoring Profiles**:
   - `code_freshness` - Boosts recently modified code
   - `code_quality` - Prioritizes well-tested, documented code
   - `tag_boost` - Emphasizes code with specific tags

3. **Autocomplete & Suggestions**:
   ```python
   # Get function name suggestions
   suggestions = search_client.suggest("auth", "function_suggester")
   ```

4. **Faceted Search** - Filter results by language, repository, tags
5. **Hit Highlighting** - Shows matched terms in context
6. **Fuzzy Search** - Handles typos automatically
7. **Synonym Support** - Maps related programming terms

### Using Enhanced Features

```bash
# Create enhanced index with all features
python azure_search_enhanced.py

# Update indexer to include metadata
python smart_indexer.py --include-metrics --include-test-coverage
```

See `docs/AZURE_SEARCH_ADVANCED_FEATURES.md` for detailed implementation guide.

## Additional Components

### Microsoft Docs Integration

The codebase includes a Microsoft Docs search integration via MCP:
- **`microsoft_docs_mcp_client.py`** - Client for searching Microsoft documentation
- **`debug_microsoft_docs.py`** - Debugging tool for Microsoft Docs search
- Provides access to API documentation, guides, and technical references through the MCP protocol