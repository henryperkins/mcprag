# Azure Integration Migration Plan

This document outlines the plan to migrate from the old Azure integration modules to the new REST API-based implementation.

## Overview

The goal is to replace complex SDK-based implementations with simple, direct REST API calls that are easier to maintain and automate.

## Module Migration Mapping

### 1. Keep As-Is (Not Azure Search Management)
- **AzureOpenAIEmbeddingProvider** - This is for OpenAI integration, not Azure Search
- **Custom skills** - These are specific implementations for cognitive enrichment
- **Standard skills** - Cognitive service integrations

### 2. Direct Replacements

#### IndexOperations → SearchOperations (REST)
**Old Usage:**
```python
from enhanced_rag.azure_integration.index_operations import IndexOperations
index_ops = IndexOperations(endpoint, admin_key)
await index_ops.create_or_update_index(index_def)
```

**New Usage:**
```python
from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
client = AzureSearchClient(endpoint, admin_key)
ops = SearchOperations(client)
await ops.create_index(index_def)
```

#### IndexerIntegration → IndexerAutomation
**Old Usage:**
```python
from enhanced_rag.azure_integration.indexer_integration import IndexerIntegration
indexer_int = IndexerIntegration()
await indexer_int.run_indexer(name)
```

**New Usage:**
```python
from enhanced_rag.azure_integration.automation import IndexerAutomation
indexer_auto = IndexerAutomation(ops)
await indexer_auto.reset_and_run_indexer(name)
```

#### DocumentOperations → DataAutomation
**Old Usage:**
```python
from enhanced_rag.azure_integration.document_operations import DocumentOperations
doc_ops = DocumentOperations(endpoint, admin_key)
await doc_ops.bulk_upload_documents(index_name, documents)
```

**New Usage:**
```python
from enhanced_rag.azure_integration.automation import DataAutomation
data_auto = DataAutomation(ops)
await data_auto.bulk_upload(index_name, documents)
```

### 3. High-Level Components to Refactor

#### EnhancedIndexBuilder
- **Purpose:** Complex index schema creation
- **Migration Strategy:** 
  1. Extract schema definitions to JSON/dict format
  2. Use `IndexAutomation.ensure_index_exists()` with the schema
  3. Move helper functions to `rest/models.py`

#### LocalRepositoryIndexer
- **Purpose:** Repository indexing with AST parsing
- **Migration Strategy:**
  1. Keep AST parsing logic
  2. Replace Azure SDK calls with REST API operations
  3. Use `DataAutomation.bulk_upload()` for document upload

#### ReindexOperations
- **Purpose:** Reindexing workflows
- **Migration Strategy:**
  1. Use `IndexAutomation` for index management
  2. Use `DataAutomation.reindex_documents()` for data migration
  3. Implement specific workflows in automation layer

## Migration Steps

### Phase 1: Update Direct Imports (Week 1)
1. Update `mcprag/server.py` to use REST clients instead of old operations
2. Update standalone scripts (`deploy_codebase_search.py`, `add_vector_field.py`)
3. Update test files to use new imports

### Phase 2: Refactor High-Level Components (Week 2)
1. Refactor `EnhancedIndexBuilder` to use REST API
2. Update `LocalRepositoryIndexer` to use new document operations
3. Migrate reindexing scripts to use automation managers

### Phase 3: Clean Up (Week 3)
1. Mark old modules as deprecated
2. Update all documentation
3. Remove unused imports
4. Run comprehensive tests

## File-by-File Migration

### mcprag/server.py
```python
# Remove
from enhanced_rag.azure_integration.index_operations import IndexOperations
from enhanced_rag.azure_integration.indexer_integration import IndexerIntegration
from enhanced_rag.azure_integration.document_operations import DocumentOperations

# Already added in integration
# Uses REST API components initialized in _init_components()
```

### deploy_codebase_search.py
```python
# Old
from enhanced_rag.azure_integration.index_operations import IndexOperations
index_ops = IndexOperations()

# New
from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
from enhanced_rag.azure_integration.config import AzureSearchConfig

config = AzureSearchConfig.from_env()
async with AzureSearchClient(config.endpoint, config.api_key) as client:
    ops = SearchOperations(client)
    # Use ops for operations
```

### index/create_enhanced_index.py
```python
# Old
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder
builder = EnhancedIndexBuilder()
index = builder.create_enhanced_rag_index()

# New
from enhanced_rag.azure_integration.automation import IndexAutomation
from enhanced_rag.azure_integration.rest.models import create_field, FieldType

# Define schema using models
fields = [
    create_field("id", FieldType.STRING, key=True),
    # ... more fields
]

index_def = {
    "name": "codebase-mcp-sota",
    "fields": fields,
    "vectorSearch": {...},
    "semanticSearch": {...}
}

async with IndexAutomation(endpoint, api_key) as automation:
    await automation.ensure_index_exists(index_def)
```

## Deprecation Notices

Add to deprecated modules:
```python
import warnings

warnings.warn(
    "This module is deprecated. Use enhanced_rag.azure_integration.rest instead.",
    DeprecationWarning,
    stacklevel=2
)
```

## Testing Strategy

1. **Unit Tests:** Update all test imports
2. **Integration Tests:** Test new REST API against live service
3. **Migration Tests:** Ensure old → new produces same results
4. **Performance Tests:** Verify no performance regression

## Rollback Plan

1. Keep old modules during migration
2. Use feature flags to switch between old/new
3. Gradual rollout with monitoring
4. Full rollback procedure documented

## Success Criteria

- [ ] All imports updated
- [ ] All tests passing
- [ ] No functionality regression
- [ ] Performance maintained or improved
- [ ] Documentation updated
- [ ] Old modules marked deprecated