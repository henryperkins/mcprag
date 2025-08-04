# Azure AI Search Integration Module

A comprehensive Python package for integrating with Azure AI Search, providing automated indexing, embedding generation, and search management capabilities.

## Overview

The `azure_integration` module provides a unified interface for working with Azure AI Search, consolidating functionality for:

- **Index Management**: Create, update, and validate search indexes with vector and semantic search capabilities
- **Document Processing**: Automated chunking and indexing of code repositories
- **Embedding Generation**: Integration with Azure OpenAI for generating text embeddings
- **Reindexing Operations**: Various strategies for updating search indexes
- **Health Monitoring**: Service health checks and operation monitoring
- **CLI Interface**: Command-line tools for common operations

## Architecture

```
azure_integration/
├── rest/                    # REST API client components
│   ├── client.py           # Low-level Azure Search REST client
│   ├── operations.py       # Search operations wrapper
│   └── models.py           # Data models
├── automation/             # High-level automation managers
│   ├── unified_manager.py  # Unified interface for all operations
│   ├── index_manager.py    # Index lifecycle management
│   ├── data_manager.py     # Document upload and management
│   ├── reindex_manager.py  # Reindexing strategies
│   ├── embedding_manager.py # Embedding generation and caching
│   ├── cli_manager.py      # CLI operations consolidation
│   ├── indexer_manager.py  # Azure indexer automation
│   └── health_monitor.py   # Service health monitoring
├── rest_index_builder.py   # Enhanced index schema builder
├── embedding_provider.py   # Embedding provider interface
├── reindex_operations.py   # Core reindexing operations
├── cli.py                  # CLI entry point
└── config.py              # Configuration management
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file with:

```bash
# Azure Search Configuration
ACS_ENDPOINT=https://your-search-service.search.windows.net
ACS_ADMIN_KEY=your-admin-key
ACS_INDEX_NAME=codebase-mcp-sota  # Optional, defaults to this

# Azure OpenAI Configuration (for embeddings)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

### Basic Usage

#### Using the Unified Interface

```python
from enhanced_rag.azure_integration import UnifiedAutomation

# Initialize the unified manager
automation = UnifiedAutomation(
    endpoint="https://your-search.search.windows.net",
    api_key="your-admin-key"
)

# Index a repository
result = await automation.index_repository(
    repo_path="./my-project",
    repo_name="my-project",
    generate_embeddings=True
)

# Get system health
health = await automation.get_system_health()

# Analyze and get recommendations
analysis = await automation.analyze_and_recommend()
```

#### Using Individual Managers

```python
from enhanced_rag.azure_integration import (
    AzureSearchClient,
    SearchOperations,
    ReindexAutomation,
    EmbeddingAutomation
)

# Initialize components
client = AzureSearchClient(endpoint, api_key)
operations = SearchOperations(client)

# Reindexing
reindex = ReindexAutomation(operations)
await reindex.perform_reindex(
    method="repository",
    repo_path="./my-project",
    repo_name="my-project"
)

# Embedding management
embeddings = EmbeddingAutomation(operations)
vector = await embeddings.generate_embedding("sample text")
```

### CLI Usage

The module provides a comprehensive CLI interface:

```bash
# Index a repository
python -m enhanced_rag.azure_integration.cli local-repo \
  --repo-path . \
  --repo-name my-project

# Create an enhanced index
python -m enhanced_rag.azure_integration.cli create-enhanced-index \
  --name codebase-mcp-sota \
  --recreate

# Reindex operations
python -m enhanced_rag.azure_integration.cli reindex \
  --method drop-rebuild

# Check index status
python -m enhanced_rag.azure_integration.cli reindex \
  --method status

# Index specific changed files
python -m enhanced_rag.azure_integration.cli changed-files \
  --files file1.py file2.js \
  --repo-name my-project
```

## Component Documentation

### 1. REST Components (`rest/`)

The REST layer provides low-level access to Azure Search APIs:

- **AzureSearchClient**: HTTP client with retry logic and error handling
- **SearchOperations**: Simplified interface for common operations

```python
from enhanced_rag.azure_integration import AzureSearchClient, SearchOperations

client = AzureSearchClient(endpoint, api_key)
ops = SearchOperations(client)

# Create an index
await ops.create_index(index_definition)

# Upload documents
await ops.upload_documents(index_name, documents)

# Search
results = await ops.search_documents(index_name, "query")
```

### 2. Embedding Provider

Supports multiple embedding providers with a common interface:

```python
from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

provider = AzureOpenAIEmbeddingProvider()

# Single embedding
embedding = provider.generate_embedding("text")

# Batch embeddings
embeddings = provider.generate_embeddings_batch(["text1", "text2"])

# Code-specific embedding with context
code_embedding = provider.generate_code_embedding(
    code="def hello(): pass",
    context="Function: hello\nPurpose: greeting"
)
```

### 3. Reindex Operations

Multiple reindexing strategies for different scenarios:

```python
from enhanced_rag.azure_integration import ReindexOperations, ReindexMethod

reindex = ReindexOperations()

# Drop and rebuild
await reindex.drop_and_rebuild(schema_path="schema.json")

# Clear documents with filter
await reindex.clear_documents("repository eq 'old-project'")

# Incremental repository reindex
await reindex.reindex_repository(
    repo_path="./project",
    repo_name="project",
    method=ReindexMethod.INCREMENTAL
)
```

### 4. Automation Managers

#### UnifiedAutomation

The main entry point consolidating all functionality:

```python
automation = UnifiedAutomation(endpoint, api_key)

# Repository indexing with progress
await automation.index_repository(
    repo_path="./project",
    repo_name="project",
    progress_callback=lambda p: print(f"Progress: {p}")
)

# Bulk document upload with embeddings
await automation.bulk_upload_documents(
    documents=document_generator(),
    enrich_embeddings=True
)

# System monitoring
health = await automation.get_system_health()
stats = await automation.get_statistics()
```

#### ReindexAutomation

Specialized reindexing operations:

```python
reindex = ReindexAutomation(operations)

# Analyze if reindexing is needed
analysis = await reindex.analyze_reindex_need()

# Perform reindex with dry run
result = await reindex.perform_reindex(
    method="drop-rebuild",
    dry_run=True  # Validate without executing
)

# Backup and restore
await reindex.backup_and_restore(
    action="backup",
    backup_path="index_backup.json"
)
```

#### EmbeddingAutomation

Advanced embedding management with caching:

```python
embeddings = EmbeddingAutomation(operations)

# Batch generation with caching
vectors = await embeddings.generate_embeddings_batch(
    texts=["text1", "text2"],
    use_cache=True
)

# Enrich documents
docs, stats = await embeddings.enrich_documents_with_embeddings(
    documents=documents,
    context_fields=["function_name", "class_name"]
)

# Validate embeddings in index
validation = await embeddings.validate_embeddings(
    index_name="my-index",
    expected_dimensions=3072
)
```

#### CLIAutomation

Repository and file processing:

```python
cli = CLIAutomation(operations)

# Process individual file
chunks = await cli.process_file(
    file_path="main.py",
    repo_path="./",
    repo_name="project"
)

# Create indexing report
report = await cli.create_indexing_report(
    index_name="my-index",
    repo_name="project"
)
```

## Advanced Features

### 1. AST-Based Code Chunking

Python files are parsed using AST to extract semantic chunks:

- Functions with signatures and docstrings
- Classes with inheritance information
- Automatic chunk boundary detection

### 2. Embedding Caching

- In-memory LRU cache with configurable TTL
- Batch optimization for API calls
- Cache statistics and management

### 3. Health Monitoring

```python
health = HealthMonitor(operations)

# Service health check
service_health = await health.check_service_health()

# Monitor long-running operations
result = await health.monitor_operation(
    operation_type="indexing",
    operation_id="op-123",
    timeout_seconds=300
)
```

### 4. Index Validation

```python
# Validate schema
validation = await reindex.validate_index_schema()

# Check vector dimensions
from enhanced_rag.azure_integration import EnhancedIndexBuilder
builder = EnhancedIndexBuilder()
result = await builder.validate_vector_dimensions(
    index_name="my-index",
    expected_dimensions=3072
)
```

## Configuration

### Index Configuration

The module uses sensible defaults for code search:

- **Vector dimensions**: 3072 (for text-embedding-3-large)
- **Semantic configuration**: Enabled by default
- **Required fields**: id, content, file_path, repository, language
- **Optional fields**: function_name, class_name, chunk_type, etc.

### Customization

Create custom index schemas:

```python
builder = EnhancedIndexBuilder()
index = await builder.create_enhanced_rag_index(
    index_name="custom-index",
    enable_vectors=True,
    enable_semantic=True,
    vector_dimensions=1536  # For ada-002
)
```

## Error Handling

The module implements comprehensive error handling:

```python
try:
    await automation.index_repository(repo_path, repo_name)
except ResourceNotFoundError:
    # Index doesn't exist
    await automation.create_or_update_index()
except Exception as e:
    logger.error(f"Indexing failed: {e}")
```

## Performance Considerations

1. **Batch Processing**: Documents are processed in configurable batches
2. **Async Operations**: All I/O operations are asynchronous
3. **Caching**: Embeddings are cached to reduce API calls
4. **Progress Callbacks**: Long operations support progress monitoring

## Migration Guide

### From Direct API Usage

```python
# Old approach
from azure.search.documents import SearchClient
client = SearchClient(endpoint, index, credential)

# New approach
from enhanced_rag.azure_integration import UnifiedAutomation
automation = UnifiedAutomation(endpoint, api_key)
```

### From CLI Scripts

```bash
# Old: Direct Python scripts
python index_repository.py --path ./project

# New: Integrated CLI
python -m enhanced_rag.azure_integration.cli local-repo --repo-path ./project --repo-name project
```

## Troubleshooting

### Common Issues

1. **Missing embeddings**: Check OpenAI configuration and API limits
2. **Schema validation failures**: Use `reindex --method validate`
3. **Empty search results**: Verify documents were indexed successfully

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Regular Backups**: Use `backup_index_schema()` before major changes
2. **Incremental Updates**: Use `index_changed_files()` for CI/CD
3. **Monitor Health**: Regularly check index health and recommendations
4. **Cache Management**: Clear embedding cache periodically
5. **Batch Operations**: Use appropriate batch sizes for your data

## Contributing

When adding new features:

1. Follow the existing architecture patterns
2. Add corresponding automation manager if needed
3. Update CLI interface for user-facing features
4. Include comprehensive error handling
5. Add logging for debugging

## License

This module is part of the Enhanced RAG project and follows the same license terms.