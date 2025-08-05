# Azure Search Operations

Interact with Azure Cognitive Search for testing and debugging.

## Purpose

This command provides direct access to Azure Search operations for debugging search issues and testing queries.

## Usage

```
/azure-search
```

## Search Operations

### Test Search Queries
```bash
# Basic search test
python scripts/debug_search.py

# Test single query
python test_single_search.py

# Test with specific query
python -c "
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os

client = SearchClient(
    endpoint=os.getenv('ACS_ENDPOINT'),
    index_name='codebase-mcp-sota',
    credential=AzureKeyCredential(os.getenv('ACS_ADMIN_KEY'))
)

results = client.search('authentication', top=5)
for r in results:
    print(f'{r['file_path']}: {r['function_name']}')
"
```

### Vector Search
```bash
# Test vector search
python tests/test_vector_search.py

# Generate embeddings for query
python -c "
from enhanced_rag.azure_integration.embedding_provider import EmbeddingProvider
provider = EmbeddingProvider()
vector = provider.generate_embedding('find authentication functions')
print(f'Vector dimensions: {len(vector)}')
"
```

### Semantic Search
```bash
# Test semantic configuration
python -c "
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os

client = SearchClient(
    endpoint=os.getenv('ACS_ENDPOINT'),
    index_name='codebase-mcp-sota',
    credential=AzureKeyCredential(os.getenv('ACS_ADMIN_KEY'))
)

# Semantic search
results = client.search(
    search_text='how to authenticate users',
    query_type='semantic',
    semantic_configuration_name='semantic-config',
    top=5
)
"
```

## Index Operations

### Inspect Index
```bash
# Get index statistics
python scripts/status.py

# Check index schema
python scripts/check_index_schema_v2.py

# Validate index
python scripts/validate_index_canonical.py

# Get document count by repository
python -c "
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os

client = SearchClient(
    endpoint=os.getenv('ACS_ENDPOINT'),
    index_name='codebase-mcp-sota',
    credential=AzureKeyCredential(os.getenv('ACS_ADMIN_KEY'))
)

# Get facets
results = client.search('*', facets=['repository'], top=0)
for facet in results.get_facets()['repository']:
    print(f\"{facet['value']}: {facet['count']} documents\")
"
```

### Manage Documents
```bash
# Upload documents
python -m enhanced_rag.azure_integration.cli manage-documents \
  --action upload \
  --index-name codebase-mcp-sota \
  --documents '[{"id": "test1", "content": "test document"}]'

# Delete documents
python -m enhanced_rag.azure_integration.cli manage-documents \
  --action delete \
  --index-name codebase-mcp-sota \
  --document-keys '["test1"]'

# Count documents
python -m enhanced_rag.azure_integration.cli manage-documents \
  --action count \
  --index-name codebase-mcp-sota
```

## Query Analysis

### Analyze Query Processing
```bash
# Preview query enhancements
python -c "
from mcprag.mcp.tools.search import preview_query_processing
import asyncio

result = asyncio.run(preview_query_processing({
    'query': 'find authentication middleware'
}))
print(result)
"

# Explain ranking
python -c "
from mcprag.mcp.tools.analysis import explain_ranking
import asyncio

result = asyncio.run(explain_ranking({
    'query': 'authentication',
    'mode': 'base'
}))
print(result)
"
```

### Debug Search Results
```bash
# Get detailed search diagnostics
python tests/test_timing_enhancement.py

# Check exact term extraction
python tests/test_exact_terms_enhancement.py

# Test BM25 vs Semantic
python -c "
from mcprag.mcp.tools.search import search_code
import asyncio

# BM25 only
bm25_results = asyncio.run(search_code({
    'query': 'def authenticate_user',
    'bm25_only': True
}))

# Semantic search
semantic_results = asyncio.run(search_code({
    'query': 'user authentication functions'
}))

print(f'BM25 results: {len(bm25_results)}')
print(f'Semantic results: {len(semantic_results)}')
"
```

## Performance Monitoring

### Cache Statistics
```bash
# Get cache stats
python -c "
from mcprag.mcp.tools.cache import cache_stats
import asyncio

stats = asyncio.run(cache_stats())
print(stats)
"

# Clear cache
python -c "
from mcprag.mcp.tools.cache import cache_clear
import asyncio

result = asyncio.run(cache_clear({'scope': 'all'}))
print(result)
"
```

### Search Performance
```bash
# Measure search latency
python -c "
import time
from mcprag.mcp.tools.search import search_code
import asyncio

start = time.time()
results = asyncio.run(search_code({
    'query': 'authentication',
    'include_timings': True
}))
end = time.time()

print(f'Total time: {end-start:.2f}s')
if 'timings_ms' in results[0]:
    print(f'Server timings: {results[0]['timings_ms']}')
"
```

## Best Practices

1. **Test queries locally** before using in MCP
2. **Monitor performance** with timing diagnostics
3. **Use facets** to understand data distribution
4. **Check schema** after any index changes
5. **Clear cache** when debugging search issues