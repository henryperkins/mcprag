# Module Update Status

## Summary of Updates to Modules Reliant on Old Modules

### Files Updated ✅

1. **index/mcp_auto_index.py**
   - Updated import: `from smart_indexer import SmartIndexer` → `from enhanced_rag.azure_integration import LocalRepositoryIndexer`
   - Updated CLI command to use new module: `python -m enhanced_rag.azure_integration.cli local-repo`

2. **tests/test_code_chunker.py**
   - Updated import: `from smart_indexer import CodeChunker` → `from enhanced_rag.code_understanding import CodeChunker`
   - Removed unnecessary patch for SearchClient

3. **tests/test_index_with_chunk.py**
   - Updated import: `from smart_indexer import CodeChunker` → `from enhanced_rag.code_understanding import CodeChunker`

4. **tests/test_complete_indexing.py**
   - Already updated to use `from enhanced_rag.code_understanding import CodeChunker`

5. **tests/test_improved_chunking.py**
   - Already updated to use `from enhanced_rag.code_understanding import CodeChunker`

6. **tests/test_vector_search.py**
   - Updated import: `from vector_embeddings import VectorEmbedder` → `from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider`
   - Fixed method name: `get_embedding()` → `generate_embedding()`

7. **tests/test_vector_embedder.py**
   - Updated all imports to use `from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider as VectorEmbedder`

8. **tests/test_vector_embeddings.py**
   - Updated import to use `from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider as VectorEmbedder`

9. **tests/debug_chunks.py**
   - Updated import to use `from enhanced_rag.code_understanding import CodeChunker`

10. **setup/test_indexer.py**
    - Already updated to use `from enhanced_rag.code_understanding import CodeChunker`

11. **mcp_server_sota.py**
    - Previously updated to use `from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider`

12. **enhanced_rag/retrieval/hybrid_searcher.py**
    - Previously updated to use `from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider`

13. **.github/workflows/ci.yml**
    - Updated Docker test command to import new modules
    - Fixed Python version array syntax
    - Updated mypy command to include enhanced_rag directory

### GitHub Integration Migration

The `github_webhook_handler.py` still imports from `github_azure_integration.py`:
- Created migration wrappers:
  - `migrate_github_webhook.py` - Wrapper to run webhook server using new module
  - `migrate_github_integration.py` - Migration guide and examples

### Status

All modules that were importing from `vector_embeddings.py` and `smart_indexer.py` have been updated to use the new enhanced_rag modules. The only remaining items are:

1. **Test Fixes Needed**: Some tests are failing because they expect the old chunk structure (e.g., `function_signature` vs `signature`)
2. **GitHub Scripts**: The old GitHub scripts (`github_webhook_handler.py`, `github_azure_integration.py`, `connect_github_to_azure.py`) are still present but migration wrappers have been created

### Next Steps

1. Fix test expectations to match the new chunk structure
2. Test the GitHub integration end-to-end
3. Remove deprecated scripts once migration is verified