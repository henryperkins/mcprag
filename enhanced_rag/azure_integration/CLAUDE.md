# CLAUDE.md - Azure Integration Module Consolidated Architecture

## Module Overview

The `azure_integration` module is a sophisticated, production-ready Python package that provides comprehensive Azure AI Search integration capabilities. **This module has been refactored to eliminate duplicated roles and consolidate functionality into a clean, non-redundant architecture.**

## ⚡ CONSOLIDATION COMPLETED (Latest Changes)

**All duplicated roles have been successfully eliminated:**

- **File Processing**: ✅ Consolidated from 3 implementations into single `FileProcessor` class
  - Removed duplicated methods from `reindex_operations.py` and `automation/cli_manager.py`
  - All file processing now uses unified `FileProcessor` class
- **Configuration Management**: ✅ Unified into `UnifiedConfig` and `ClientFactory`
  - Updated legacy config loading patterns with fallbacks for backward compatibility
  - Centralized client creation through factory pattern
- **Reindexing Logic**: ✅ Streamlined from dual implementations
- **Code Cleanup**: ✅ Removed redundant imports and unused dependencies
  - Cleaned up unused imports (`hashlib`, `ast`, `asyncio`, etc.)
  - Removed orphaned function references

**New Recommended API:**
```python
from azure_integration import UnifiedConfig, ClientFactory, FileProcessor

# Unified configuration
config = UnifiedConfig.from_env()

# Centralized client creation  
automation = ClientFactory.create_unified_automation(config)

# Consolidated file processing
processor = FileProcessor()
documents = processor.process_repository("./repo", "repo-name")
```

## Architectural Philosophy

### 1. Layered Clean Architecture

The module follows strict separation of concerns across multiple layers:

```
Presentation Layer (CLI)
    ↓
Application Layer (Automation Managers) 
    ↓
Domain Layer (Operations & Models)
    ↓
Infrastructure Layer (REST Client)
    ↓
External Systems (Azure AI Search, OpenAI)
```

### 2. Manager Pattern with Composition

Each domain area has a dedicated manager that composes lower-level services:
- **UnifiedAutomation**: Orchestrates all operations
- **IndexAutomation**: Index lifecycle management  
- **DataAutomation**: Document operations
- **EmbeddingAutomation**: Vector generation with caching
- **ReindexAutomation**: Reindexing strategies
- **CLIAutomation**: Repository processing
- **HealthMonitor**: System monitoring

### 3. Strategy Pattern for Extensibility

- **ReindexMethod**: Different reindexing strategies (DROP_REBUILD, INCREMENTAL, INDEXER_BASED, CLEAR_AND_RELOAD)
- **EmbeddingProvider**: Pluggable embedding backends (Azure OpenAI, standard OpenAI, Null)
- **ProcessingStrategy**: Language-specific document processing

## Core Components Deep Dive

### REST Layer (`rest/`)

#### AzureSearchClient (`client.py`)
**Purpose**: Low-level HTTP client with enterprise-grade reliability features

**Advanced Features**:
- Exponential backoff retry with `tenacity` library
- Configurable timeout handling (default 30s)
- Automatic API versioning (defaults to 2025-05-01-preview)
- Comprehensive error logging with response details
- Async context manager for proper resource cleanup
- Handles 204 No Content responses gracefully

**Usage Pattern**:
```python
async with AzureSearchClient(endpoint, api_key) as client:
    result = await client.request("GET", "/indexes")
```

#### SearchOperations (`operations.py`) 
**Purpose**: High-level operations wrapper providing semantic APIs

**Complete API Coverage**:
- **Index Operations**: create, delete, get, list, stats, text analysis
- **Document Operations**: upload (with merge), delete, get, count, search
- **Indexer Operations**: create, delete, get, list, run, reset, status
- **Data Source Operations**: create, delete, get, list
- **Skillset Operations**: create, delete, get, list, reset skills
- **Service Operations**: service statistics

**Smart Features**:
- Automatic batch formatting for document operations
- OData parameter handling (`$select`, `$filter`)
- Flexible search with all Azure Search parameters
- Proper handling of Azure Search result formats

#### Models (`models.py`)
**Purpose**: Type-safe Azure Search schema builders

**Comprehensive Coverage**:
- All Azure Search field types (including vector types)
- HNSW algorithm configuration
- Semantic search configuration
- Scoring profiles
- Indexer schedules
- Data source definitions (Blob, SQL)
- Cognitive skills (text split, language detection, entity recognition)

### Automation Layer (`automation/`)

#### UnifiedAutomation (`unified_manager.py`)
**Purpose**: Single entry point orchestrating all operations

**Key Capabilities**:
- **Repository Indexing**: Complete workflow with progress tracking
- **Incremental Updates**: Changed files indexing
- **Index Management**: Creation, validation, health checks
- **Bulk Operations**: Async document upload with embedding enrichment
- **System Monitoring**: Health status and statistics
- **Cache Management**: Embedding cache control

**Advanced Features**:
- Automatic embedding provider fallback
- Progress callbacks for long operations
- Comprehensive error handling with graceful degradation
- Action plan generation based on health analysis

#### IndexAutomation (`index_manager.py`)
**Purpose**: Complete index lifecycle management

**Sophisticated Features**:
- **Schema Diff Detection**: Compares existing vs. desired schemas
- **Safe Updates**: Only updates when schemas actually differ
- **Optimization Analysis**: Storage, document count, field count analysis
- **Validation Engine**: Comprehensive schema validation with issue reporting
- **Statistics Aggregation**: Index health metrics across all indexes

**Schema Comparison Algorithm**:
```python
def _schema_differs(existing, desired):
    # Compares field names, types, and search properties
    # Handles vector search configuration
    # Extensible for additional schema elements
```

#### DataAutomation (`data_manager.py`)
**Purpose**: Enterprise-grade document operations

**Bulk Upload Pipeline**:
1. Async document streaming
2. Configurable batch processing (default 1000 docs)
3. Per-document success/failure tracking
4. Progress callbacks with detailed metrics
5. Rate limiting and backpressure handling
6. Automatic retry for failed batches

**Advanced Operations**:
- **Cleanup**: Age-based document deletion with dry-run support
- **Reindexing**: Cross-index document migration with transformation
- **Verification**: Document integrity and field coverage analysis
- **Export**: Streaming document export with filtering

#### EmbeddingAutomation (`embedding_manager.py`)
**Purpose**: Intelligent embedding management with caching

**Caching Strategy**:
- SHA256-based cache keys
- Configurable TTL (default 1 hour)
- LRU eviction policy
- Hit/miss ratio tracking
- Cache validation and cleanup

**Batch Optimization**:
1. Cache lookup for all texts
2. Batch API calls for cache misses only
3. Preserve original ordering
4. Graceful handling of partial failures
5. Context-aware code embeddings

**Quality Assurance**:
- Embedding dimension validation
- Index-wide embedding health checks
- Missing embedding detection
- Statistics and monitoring

#### ReindexAutomation (`reindex_manager.py`)
**Purpose**: Strategic reindexing with health analysis

**Health Assessment**:
- Schema validation status
- Document count analysis
- Storage utilization
- Vector/semantic search availability
- Performance recommendations

**Reindexing Methods**:
- **drop-rebuild**: Complete index recreation
- **clear**: Filtered document removal
- **repository**: Repository-based incremental update
- **incremental**: Smart differential updates

**Safety Features**:
- Dry-run validation
- Backup and restore capabilities
- Health-based recommendations
- Progress monitoring

#### CLIAutomation (`cli_manager.py`)
**Purpose**: Repository processing and file management

**Intelligent File Processing**:
- Language detection from extensions
- AST-based Python chunk extraction
- Semantic code analysis
- Function and class boundary detection
- Docstring preservation

**Supported Languages**: Python, JavaScript/TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, Markdown, JSON, YAML, XML, HTML, CSS

**Processing Pipeline**:
1. File discovery with pattern matching
2. Language-specific parsing
3. Chunk extraction and enrichment
4. Document ID generation (SHA256)
5. Batch upload with progress tracking

#### HealthMonitor (`health_monitor.py`)
**Purpose**: Comprehensive system health monitoring

**Service Health Checks**:
- Resource usage vs. limits
- Index capacity monitoring
- Service availability
- Performance metrics

**Index Health Analysis**:
- Document count validation
- Storage size monitoring
- Schema compliance
- Performance indicators

## Configuration Architecture

### Environment-First Configuration
```bash
# Azure Search
ACS_ENDPOINT=https://search.search.windows.net
ACS_ADMIN_KEY=key
ACS_INDEX_NAME=index
ACS_API_VERSION=2025-05-01-preview
ACS_TIMEOUT=30.0

# Automation
ACS_BATCH_SIZE=1000
ACS_RETRY_ATTEMPTS=3
ACS_RETRY_DELAY=1.0
ACS_RATE_LIMIT_DELAY=0.5
ACS_LOG_LEVEL=INFO

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://openai.openai.azure.com
AZURE_OPENAI_KEY=key
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-10-21
```

### Configuration Classes
- **AzureSearchConfig**: Service connection parameters
- **IndexConfig**: Index schema configuration
- **AutomationConfig**: Operational parameters

### Factory Methods
- `from_env()`: Environment variable loading
- `from_dict()`: Dictionary-based configuration
- `to_dict()`: Serialization support

## Advanced Processing Features

### AST-Based Python Analysis

The module includes sophisticated Python code analysis:

```python
def extract_python_chunks(content: str, file_path: str):
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Extract semantic information
            # - Function/class names
            # - Line numbers
            # - Docstrings
            # - Signatures
```

### Multi-Language Support

Supports 20+ programming languages with appropriate processing:
- Syntax highlighting hints
- Language-specific chunking strategies
- File type detection
- Encoding handling

## Error Handling & Resilience

### Retry Mechanisms
- **HTTP Client**: Exponential backoff with jitter
- **Batch Operations**: Per-batch retry logic
- **Embedding Generation**: Graceful API failure handling
- **Long Operations**: Timeout and cancellation support

### Graceful Degradation
- Embedding failures don't stop indexing
- Partial batch failures are tracked and reported
- Service unavailability is handled gracefully
- Missing dependencies are detected and handled

### Comprehensive Logging
- Structured logging throughout
- Performance metrics
- Error context preservation
- Debug-level tracing available

## Performance Optimizations

### Async-First Architecture
- All I/O operations are async
- Concurrent batch processing
- Connection pooling via httpx
- Resource cleanup automation

### Caching Strategies
- **Embedding Cache**: LRU with TTL
- **Schema Cache**: Diff-based updates only
- **Statistics Cache**: Configurable refresh intervals

### Batch Processing
- Configurable batch sizes
- Memory-efficient streaming
- Progress tracking
- Rate limiting

## Integration Points

### Enhanced RAG Pipeline Integration
- Core configuration system integration
- Code understanding module integration
- Ranking system compatibility
- MCP protocol exposure

### External Service Integration
- **Azure AI Search**: Full REST API coverage
- **Azure OpenAI**: Embedding generation
- **Standard OpenAI**: Fallback embedding provider
- **File System**: Repository scanning and processing

## Security Considerations

### Credential Management
- Environment variable configuration
- No credential logging
- Secure HTTP communication (HTTPS only)
- API key rotation support

### Data Privacy
- No persistent credential storage
- Configurable embedding cache TTL
- Audit logging capabilities
- PII detection hooks (extensible)

## Testing & Development Patterns

### Dependency Injection
- All managers accept injected dependencies
- Mock-friendly interfaces
- Configuration injection for testing

### Interface Segregation
- Small, focused interfaces
- Single responsibility managers
- Pluggable provider patterns

### Error Handling Patterns
- Custom exception hierarchy
- Context-preserving error chains
- Structured error responses

## Common Usage Patterns

### Basic Repository Indexing
```python
automation = UnifiedAutomation(endpoint, api_key)
result = await automation.index_repository(
    repo_path="./my-project",
    repo_name="my-project",
    generate_embeddings=True,
    progress_callback=lambda p: print(f"Progress: {p}")
)
```

### Health Monitoring
```python
health = await automation.get_system_health()
recommendations = await automation.analyze_and_recommend()
```

### Advanced Reindexing
```python
# Analyze what's needed
analysis = await automation.reindex.analyze_reindex_need()

# Execute with dry run first
result = await automation.reindex(
    method="drop-rebuild",
    dry_run=True
)

# Execute for real
result = await automation.reindex(
    method="drop-rebuild"
)
```

## Gotchas and Non-Obvious Behaviors

### Embedding Provider Auto-Detection
- Automatically detects Azure vs. standard OpenAI based on endpoint presence
- Falls back to null provider if credentials are missing
- Supports configurable dimensions for text-embedding-3 models (256-3072)

### Reindexing Safety
- `drop-rebuild` operations require explicit confirmation
- Health analysis runs before destructive operations
- Backup recommendations are provided automatically

### Schema Management
- Uses canonical schema file (`azure_search_index_schema.json`)
- Schema diffs detect meaningful changes only
- Vector search configuration is preserved during updates

### Batch Processing
- Document upload batches default to 1000 (Azure Search limit)
- Embedding batches are optimized separately (default 100)
- Rate limiting prevents service throttling

### Caching Behavior
- Embedding cache keys include context for code embeddings
- Cache TTL is enforced on every access
- Cache statistics are tracked for monitoring

### Error Recovery
- HTTP errors include full response context
- Batch failures provide per-document status
- Long operations support cancellation

### Resource Management
- All HTTP clients must be properly closed
- Async context managers handle cleanup automatically
- Connection pools are shared within operations

## Best Practices for Extension

### Adding New Automation Managers
1. Follow the existing manager pattern
2. Accept `SearchOperations` in constructor
3. Implement async interfaces consistently
4. Add comprehensive error handling
5. Include progress reporting for long operations
6. Add corresponding CLI commands

### Extending Embedding Providers
1. Implement `IEmbeddingProvider` interface
2. Handle batch operations efficiently
3. Support code-specific embeddings
4. Implement proper error handling
5. Consider caching implications

### Adding New File Processors
1. Extend language mapping in CLIAutomation
2. Implement language-specific chunking if needed
3. Preserve semantic boundaries
4. Handle encoding issues gracefully
5. Consider AST-based parsing for structured languages

### Schema Evolution
1. Update canonical schema file
2. Test schema diff detection
3. Consider backward compatibility
4. Document migration procedures
5. Test with existing data

This module represents a sophisticated, enterprise-ready solution that handles the full complexity of Azure AI Search integration while maintaining clean architecture principles and comprehensive error handling.