# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Index Creation and Management

**Always use the canonical index creation path to avoid schema drift:**

```bash
# Create/recreate the canonical index with all features
python index/create_enhanced_index.py

# Validate index configuration
python scripts/validate_index_canonical.py

# Check detailed schema (alternative validation)
python scripts/check_index_schema_v2.py
```

The canonical index uses:
- Index name: `codebase-mcp-sota` (set via `ACS_INDEX_NAME` env var)
- Vector dimensions: 3072 (matching text-embedding-3-large)
- Semantic config: `semantic-config`
- Required fields: content, function_name, repository, language, content_vector
- Enhanced features: vector search, semantic search, scoring profiles

## Quick Start: Index Your Repository

```bash
# 1. Check current index status
python -m enhanced_rag.azure_integration.cli reindex --method status

# 2. Index your repository (recommended)
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name your-project

# 3. Verify indexing worked
python -m enhanced_rag.azure_integration.cli reindex --method status

# If you need to start fresh:
python -m enhanced_rag.azure_integration.cli reindex --method drop-rebuild
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name your-project
```

## IMPORTANT: Search Tool Priority

**ALWAYS use the MCP-provided `mcp__azure-search__search_code` tool for code searches instead of built-in Grep/Glob tools.**

When you need to search the codebase:
1. First choice: Use `mcp__azure-search__search_code` - it provides semantic search with better context understanding
2. For exact matches: Use `mcp__azure-search__search_code_raw` when searching for specific values, variable names, or exact code snippets
3. Only use Grep/Glob if specifically looking for exact string matches or file patterns when MCP tools are unavailable

The MCP search tool offers:
- Intent-aware search (implement/debug/understand/refactor)
- Semantic understanding of code
- Automatic exact term filtering for quoted phrases and numbers
- Hybrid BM25 + semantic search with tunable weights
- Smart caching with 60s TTL and LRU eviction
- Detailed performance diagnostics and timing breakdowns

### Effective MCP Search Strategies

#### Query Construction Guidelines
- **For semantic search (`search_code`)**: Use natural language to describe what the code DOES
  - ✅ Good: "index schema vector field definition"
  - ✅ Good: "where are embeddings generated"
  - ✅ Good: "vector dimension configuration"
  - ❌ Bad: "vector issue problem error" (too generic)
  - ❌ Bad: "SearchField vector_field dimensions 1536" (too literal - use search_code_raw instead)

- **For exact matches (`search_code_raw`)**: Use specific code snippets or values
  - ✅ Good: "dimensions = 3072"
  - ✅ Good: "Field(default=3072)"
  - ✅ Good: "def create_index_schema"
  - ❌ Bad: "find the dimension setting" (too vague - use search_code instead)

#### Intent Selection
- `understand`: Best for learning how features work and finding definitions
- `implement`: Finding code patterns to implement similar functionality (adds boost terms)
- `debug`: Locating error handling, validation, and troubleshooting code (adds error-related terms)
- `refactor`: Finding code that needs improvement
- **Note**: Intent primarily adds query boost terms but doesn't fundamentally change search behavior

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

### Enhanced Search Features

#### Exact Term Filtering
The search tools support automatic extraction and filtering of exact terms:

```python
# Automatic extraction from queries - multiple patterns supported:
"parse 'HTTP/1.1' headers"         # Quoted phrases
"dimension 3072 configuration"      # Numbers (including versions like 3.14.2)
"authenticate_user()"              # Function calls (extracts 'authenticate')
"getUserData method"               # camelCase identifiers
"parse_json function"              # snake_case identifiers

# Manual exact terms specification
results = await client.use_mcp_tool(
    server_name="azure-code-search",
    tool_name="search_code",
    arguments={
        "query": "error handling",
        "exact_terms": ["ValueError", "TypeError"]  # Must contain these exact strings
    }
)
```

**How it works**:
- Multiple pattern detection: quotes, numbers, function calls, camelCase, snake_case
- Enhanced validation and escaping for special characters
- Fallback to query enhancement if filter application fails
- Check response fields: `applied_exact_terms`, `exact_terms_fallback_used`, `exact_terms_error`

#### BM25-Only Search
For keyword-based search without semantic understanding, use the `bm25_only` parameter:

```python
# Pure keyword search
results = await client.use_mcp_tool(
    server_name="azure-code-search",
    tool_name="search_code",
    arguments={
        "query": "def authenticate_user",
        "bm25_only": true  # Disable semantic search
    }
)
```

**Note**: Hybrid search functionality is integrated into the main `search_code` tool. Use `bm25_only: true` for pure keyword search or leave it as default for semantic search.

#### Timing Diagnostics
All search tools include timing information:

```python
# Regular search includes timings
results = await client.use_mcp_tool(
    server_name="azure-code-search",
    tool_name="search_code",
    arguments={
        "query": "parse json",
        "include_timings": true
    }
)
# Check results["data"]["timings_ms"] for performance metrics
```

#### Result Explanations
Use `explain_ranking` to understand why results were ranked:

```python
explanations = await client.use_mcp_tool(
    server_name="azure-code-search",
    tool_name="explain_ranking",
    arguments={
        "query": "authentication middleware",
        "mode": "base"  # or "enhanced" if available
    }
)

# Returns ranking factors for each result:
# - term_overlap: Query term matches
# - signature_match: Function name relevance
# - base_score: Azure Search score
# - Additional factors when enhanced mode available
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

### Troubleshooting Guide

#### Search Not Finding Expected Results
- **Check exact term extraction**: Look for `exact_terms` in response to see what was auto-detected
- **Verify filter application**: Check `applied_exact_terms` and `exact_terms_fallback_used` flags
- **Try keyword search**: Use `search_code` with `bm25_only: true` for literal matches

#### Performance Issues  
- **Check cache hit**: Look for `cache_status.hit` in results
- **Analyze bottlenecks**: Use `search_code` with `include_timings: true` to see timing information
- **Bypass cache**: Set `disable_cache: true` for testing

#### Understanding Results
- **Ranking factors**: Use `explain_ranking` to see why results were ranked
- **Score breakdown**: In hybrid search, check `bm25_score`, `semantic_score`, and `hybrid_score`
- **Timing details**: Check `server_timings_ms` for internal operation breakdown

## Development Commands

### Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the SOTA MCP server
python mcp_server_sota.py
```

### Index Management and Reindexing
```bash
# Check index status
python -m enhanced_rag.azure_integration.cli reindex --method status

# Validate index schema
python -m enhanced_rag.azure_integration.cli reindex --method validate

# Backup current index schema
python -m enhanced_rag.azure_integration.cli reindex --method backup --output schema_backup.json

# Drop and rebuild index (CAUTION: deletes all data)
python -m enhanced_rag.azure_integration.cli reindex --method drop-rebuild
python -m enhanced_rag.azure_integration.cli reindex --method drop-rebuild --schema custom_schema.json

# Clear documents (with optional filter)
python -m enhanced_rag.azure_integration.cli reindex --method clear
python -m enhanced_rag.azure_integration.cli reindex --method clear --filter "repository eq 'old-repo'"

# Reindex repository
python -m enhanced_rag.azure_integration.cli reindex --method repository --repo-path . --repo-name mcprag
python -m enhanced_rag.azure_integration.cli reindex --method repository --repo-path . --repo-name mcprag --clear-first
```

### Repository Indexing
```bash
# Index local repository (recommended method)
python -m enhanced_rag.azure_integration.cli local-repo --repo-path ./path/to/repo --repo-name project-name

# Index with specific patterns
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag --patterns "*.py" "*.js"

# Index without embeddings (faster)
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag --no-embed-vectors

# Index only changed files (for CI/CD)
python -m enhanced_rag.azure_integration.cli changed-files --files file1.py file2.js --repo-name mcprag
```

### Azure Indexer Management
```bash
# Create an indexer for automated updates from blob storage
python -m enhanced_rag.azure_integration.cli create-indexer \
  --name my-indexer \
  --source azureblob \
  --conn "DefaultEndpointsProtocol=https;AccountName=..." \
  --container my-container \
  --index codebase-mcp-sota \
  --schedule-minutes 120

# Check indexer status
python -m enhanced_rag.azure_integration.cli indexer-status --name my-indexer
```

### Index Creation and Validation
```bash
# Create enhanced index with all features
python -m enhanced_rag.azure_integration.cli create-enhanced-index --name codebase-mcp-sota

# Validate vector dimensions
python -m enhanced_rag.azure_integration.cli validate-index --name codebase-mcp-sota --check-dimensions 3072
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

1. **Enhanced RAG Azure Integration (`enhanced_rag/azure_integration/`)** - Comprehensive indexing system
   - **Unified Architecture**:
     - `UnifiedAutomation` - Single entry point for all operations
     - `ReindexAutomation` - Advanced reindexing strategies with health monitoring
     - `EmbeddingAutomation` - Batch embedding generation with caching
     - `CLIAutomation` - Repository indexing and file processing
   - **Core Components**:
     - **ReindexOperations** - Complete reindexing strategies (drop/rebuild, incremental, clear)
     - **EmbeddingProvider** - Pluggable embedding generation (Azure OpenAI, null provider)
     - **REST API Layer** - Low-level Azure Search operations
   - **Features**:
     - AST-based code chunking for Python (built-in) and JS/TS (via Babel)
     - Rich context extraction: function signatures, imports, docstrings
     - Incremental indexing of changed files
     - Embedding cache with TTL and LRU eviction

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

### Key Features

- **AST Analysis**: Extracts actual function signatures, imports, and call graphs
- **Semantic Context**: Rich descriptions for better retrieval accuracy  
- **Intent Processing**: Different search strategies based on user intent
- **Smart Exact Term Filtering**: Automatic detection with fallback mechanisms
- **Hybrid Search**: Configurable BM25/semantic blending for optimal results
- **Performance Monitoring**: Detailed timing diagnostics for all operations
- **Intelligent Caching**: TTL-based cache with LRU eviction

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
- `ACS_INDEX_NAME` - Optional, defaults to `codebase-mcp-sota`

For embedding generation (optional):
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_KEY` or `AZURE_OPENAI_API_KEY` - API key
- `AZURE_OPENAI_EMBEDDING_MODEL` - Model name (defaults to `text-embedding-3-large`)

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
   - The MCP tools `mcp__azure-search__search_code` and `mcp__azure-search__search_microsoft_docs` will be available
   - Example: "Search for authentication functions" will use the code search
   - **Note**: Microsoft Docs search is currently non-functional (returns empty results) as Microsoft Learn doesn't provide a public MCP endpoint

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
        "command": "bash scripts/pre-commit-index-check.sh",
        "description": "Check for prohibited index creator files"
      },
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

### Unified Automation API

The enhanced_rag module now provides a unified interface for all Azure Search operations:

```python
from enhanced_rag.azure_integration import UnifiedAutomation
import asyncio

async def use_unified_api():
    # Initialize unified automation
    automation = UnifiedAutomation(
        endpoint="https://your-search.search.windows.net",
        api_key="your-admin-key"
    )
    
    # Index a repository with progress tracking
    result = await automation.index_repository(
        repo_path="./my-project",
        repo_name="my-project",
        generate_embeddings=True,
        progress_callback=lambda p: print(f"Progress: {p}")
    )
    
    # Get comprehensive system health
    health = await automation.get_system_health()
    print(f"Service health: {health['service']}")
    print(f"Index health: {health['default_index']}")
    
    # Analyze and get recommendations
    analysis = await automation.analyze_and_recommend()
    for action in analysis['suggested_actions']:
        print(f"{action['priority']}: {action['action']} - {action['reason']}")
    
    # Perform smart reindexing
    await automation.reindex(
        method="repository",
        repo_path="./my-project",
        repo_name="my-project"
    )

# Run the async function
asyncio.run(use_unified_api())
```

### Programmatic Reindexing API

The enhanced_rag module also provides direct access to individual components:

```python
from enhanced_rag.azure_integration import (
    ReindexOperations, 
    ReindexMethod,
    EmbeddingAutomation,
    CLIAutomation
)
import asyncio

async def manage_components():
    # Direct component usage
    reindex_ops = ReindexOperations()
    
    # Get index status
    info = await reindex_ops.get_index_info()
    print(f"Documents: {info['document_count']}")
    
    # Validate schema
    validation = await reindex_ops.validate_index_schema()
    if not validation['valid']:
        print(f"Schema issues: {validation['issues']}")
    
    # Backup schema before changes
    await reindex_ops.backup_index_schema("backup.json")
    
    # Clear old documents
    deleted = await reindex_ops.clear_documents("repository eq 'old-project'")
    print(f"Deleted {deleted} documents")
    
    # Reindex repository
    success = await reindex_ops.reindex_repository(
        repo_path="./my-project",
        repo_name="my-project",
        method=ReindexMethod.INCREMENTAL
    )

# Run the async function
asyncio.run(manage_components())
```

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

## Index Schema Documentation

For detailed information about Azure AI Search index configuration:
- [`docs/createindex.md`](docs/createindex.md) - Schema and index creation fundamentals
- [`docs/createRESTapi.md`](docs/createRESTapi.md) - REST API structure reference
- [`docs/createavectorindex.md`](docs/createavectorindex.md) - Vector index design and configuration
- [`docs/updateindex.md`](docs/updateindex.md) - **Primary guide for updates and MCP canonical fields** (see lines 398-449)
- [`docs/sharesearchresults.md`](docs/sharesearchresults.md) - Result composition and query shaping
- [`docs/index-plan.md`](docs/index-plan.md) - Comprehensive standardization plan

**Important**: Always use `index/create_enhanced_index.py` for production index creation. The EnhancedIndexBuilder is the single source of truth for schema configuration.

## Additional Components

### Microsoft Docs Integration

The codebase includes a Microsoft Docs search integration via MCP:
- **`microsoft_docs_mcp_client.py`** - Client for searching Microsoft documentation
- **`debug_microsoft_docs.py`** - Debugging tool for Microsoft Docs search
- **Important**: Currently non-functional as Microsoft Learn doesn't provide a public MCP endpoint
- The system defaults to disabled network mode and returns empty results

## Troubleshooting

### Common Indexing Issues

1. **"The property 'file_name' does not exist" error**
   - **Issue**: Field name mismatch between indexer and schema
   - **Fix**: Already fixed in `enhanced_rag/azure_integration/indexer_integration.py`
   - **If persists**: Check that you're using the latest code

2. **Empty search results after indexing**
   - **Check index status**: `python -m enhanced_rag.azure_integration.cli reindex --method status`
   - **Validate schema**: `python -m enhanced_rag.azure_integration.cli reindex --method validate`
   - **Verify documents exist**: Check the document count in status output
   - **Try reindexing**: `python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag`

3. **Import errors with Azure SDK**
   - **Issue**: Missing or outdated Azure Search SDK
   - **Fix**: `pip install --upgrade azure-search-documents==11.6.0b1`

4. **Configuration errors**
   - **Issue**: Missing environment variables
   - **Fix**: Ensure `.env` file contains:
     ```
     ACS_ENDPOINT=https://your-search-service.search.windows.net
     ACS_ADMIN_KEY=your-admin-key
     AZURE_OPENAI_KEY=your-openai-key (optional for embeddings)
     ```

### Reindexing Best Practices

1. **Before major changes**: Always backup your schema
   ```bash
   python -m enhanced_rag.azure_integration.cli reindex --method backup --output backup_$(date +%Y%m%d).json
   ```

2. **For schema changes**: Use drop-rebuild method
   ```bash
   python -m enhanced_rag.azure_integration.cli reindex --method drop-rebuild
   python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag
   ```

3. **For content updates**: Use incremental indexing
   ```bash
   python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag
   ```

4. **For cleanup**: Clear specific repositories
   ```bash
   python -m enhanced_rag.azure_integration.cli reindex --method clear --filter "repository eq 'old-repo'"
   ```

## Known Issues and Limitations

Based on testing and recent improvements, the following issues have been identified and addressed:

### Recently Fixed Issues

1. **Field name mismatch (`file_name` vs `file_path`)** - ✅ FIXED
   - The indexer was using `file_name` but schema expects `file_path`
   - Fixed in `enhanced_rag/azure_integration/indexer_integration.py`

2. **Missing reindexing tools** - ✅ FIXED
   - Added comprehensive reindexing operations module
   - Integrated with CLI for easy access
   - Full programmatic API available

3. **No index management utilities** - ✅ FIXED
   - Added index statistics, duplicate detection, optimization recommendations
   - Export functionality for data analysis
   - Stale document detection

4. **Fragmented automation components** - ✅ FIXED
   - Created unified automation architecture
   - `UnifiedAutomation` provides single entry point
   - All managers (reindex, embedding, CLI) now integrated
   - Consistent patterns across all automation components

### Current Status

### Tool Functionality Status

#### ✅ **Fully Functional**:
- `search_code` - Semantic search with automatic exact term filtering, timing diagnostics, and cache status
- `search_code_raw` - Direct Azure Search results for exact code matches
- `preview_query_processing` - Shows query enhancements and intent detection
- `explain_ranking` - Ranking factor explanations with fallback handling
- `cache_stats` / `cache_clear` - TTL cache management with LRU eviction
- `index_rebuild` - Indexer operations with method existence checking

#### ⚠️ **Partially Functional**:
- `search_microsoft_docs` - Returns structured JSON but requires Microsoft endpoint
- `search_code_then_docs` - Code search works; docs fallback depends on availability
- Dependency resolution - Limited to top result's 3 dependencies
- `search_code_pipeline` - Config object compatibility issue

#### ❌ **Non-Functional**:
- Microsoft Docs endpoints - No public MCP endpoint from Microsoft Learn
- Resource endpoints (`runtime_diagnostics`, `pipeline_status`) - Async handling issues
- Cross-file dependency graph - Not implemented

### Common Issues and Workarounds

1. **Exact Match Search**: Automatic extraction handles quotes, numbers, function calls, camelCase, and snake_case. Falls back to query enhancement if filters fail.

2. **Cache Behavior**: 60s TTL with 500 entry limit. Set `disable_cache: true` to bypass.

3. **Intent Usage**: Adds boost terms - `implement` boosts function/class, `debug` boosts error handling.

4. **Performance**: Use `include_timings: true` in search queries for performance analysis.

## Future Enhancement Discussions

### Schema Versioning and Webhook Support (2025-01-15)

We discussed two potential enhancements to the MCP server architecture:

1. **Schema Versioning**: Would enable API evolution while maintaining backward compatibility. Benefits include:
   - Gradual migration paths for breaking changes
   - Progressive enhancement with opt-in for new features
   - Clear deprecation communication
   - Support for A/B testing of new schemas

2. **Webhook Support**: Would enable event-driven architectures and real-time notifications. Benefits include:
   - Real-time index update notifications
   - CI/CD integration for automatic reindexing
   - Reduced polling and better resource utilization
   - Support for monitoring and alerting systems

These features would transform the MCP server from a request-response system into a more dynamic, event-driven platform that can evolve gracefully over time while maintaining compatibility with existing clients.