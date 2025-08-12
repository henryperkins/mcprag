# Azure Integration Refactor – Duplication & Impact Report

This document consolidates two analyses:

1. **Current Redundancies & Duplicated Logic** – where code overlaps inside
   `enhanced_rag/azure_integration/`.
2. **Down-stream Dependencies** – the files in the wider repository that will
   need import/path changes when the duplication is removed.

---

## 1. Duplication Overview

| Area | Overlapping Files | Issue | Consolidation Target |
|------|-------------------|-------|----------------------|
| **Index creation / schema management** | `automation/index_manager.py`, `rest_index_builder.py`, `schema_automation.py` | Three different *ensure-index* flows | Keep `IndexAutomation`; other modules become thin wrappers. |
| **Re-indexing & clear / rebuild** | `reindex_operations.py`, `automation/reindex_manager.py`, `automation/unified_manager.py` | Conflicting drop/clear logic, double execution | Keep `ReindexAutomation` (REST); deprecate `reindex_operations.py`. |
| **Indexer / datasource pipelines** | `automation/indexer_manager.py`, `schema_automation.py`, `cli_schema_automation.py` | Duplicate blob/SQL helpers | Use `IndexerAutomation` everywhere. |
| **Embedding providers / batch helpers** | `embedding_provider.py`, `automation/embedding_manager.py` | Two caching + env-resolution layers | Keep `embedding_provider.py`; slim or remove `embedding_manager.py`. |
| **Configuration objects** | `azure_integration/config.py`, `enhanced_rag/core/config.py`, `mcprag/config.py` | Multiple env parsers | Canonicalise on core Pydantic config; expose adapter for legacy callers. |
| **REST vs SDK paths** | REST layer (`rest/*`) vs direct SDK calls in `reindex_operations.py`, etc. | Mixed access patterns, inconsistent retries | Standardise on REST layer. |
| **Field / vector helper factories** | `rest/models.py` vs inline dicts in `schema_automation.py`, `cli_schema_automation.py` | Spec divergence risk | Import factories from `rest.models` globally. |
| **File-to-document processing** | `processing.py` vs loops in `cli_manager.py`, `reindex_operations.py` | Inconsistent MIME detection & truncation | Use `processing.FileProcessor` exclusively. |
| **Connection pooling** | `rest/client_pool.py` (unused) | Dead abstraction | Delete or wire through DI. |
| **Blob helpers** | `automation/storage_manager.py` vs logic in `indexer_manager.py` | Double maintenance | Fold into `indexer_manager.py`. |
| **Schema constants** | Duplicated in `schema_automation.py` | Typos / divergence | Centralise in `rest.models`. |
| **Dual index creation call** | `unified_manager.create_or_update_index()` calls both builder + manager | Work executed twice | Call `IndexAutomation` once. |

> **Quick metrics:** ~1 000 duplicated lines across these areas.

**Priority fix order**

1. Deprecate `reindex_operations.py` & migrate callers.
2. Remove `client_pool.py` & `storage_manager.py`.
3. Replace inline field/vector definitions with `rest.models` factories.
4. Update CLI modules to reuse `FileProcessor` and `IndexerAutomation`.
5. Drop `rest_index_builder.py` once callers shift to `IndexAutomation`.

---

## 2. Files Requiring Updates After Refactor

These files *outside* `enhanced_rag/azure_integration/` currently import one of
the duplicated modules.  When paths or APIs change they must be updated (or a
compat shim left in place).

```
index/create_enhanced_index.py
index/recreate_index_fixed.py
scripts/check_index_schema.py
scripts/check_index_schema_v2.py
scripts/index_changed_files.py
scripts/validate_index_canonical.py
tests/test_processing_pruning_and_validation.py
mcprag/server.py
mcprag/azure/unified_search.py
mcprag/mcp/tools/azure_management.py
enhanced_rag/github_integration/remote_indexer.py
enhanced_rag/retrieval/hybrid_searcher.py
enhanced_rag/azure_integration/automation/deploy_via_mcp.py  # sibling imports
```

### Expected Changes

1. **Index creation imports** – switch
   `enhanced_rag.azure_integration.rest_index_builder.EnhancedIndexBuilder`
   ➜ `enhanced_rag.azure_integration.automation.index_manager.IndexAutomation`.

2. **Embedding provider references** – confirm
   `embedding_provider.AzureOpenAIEmbeddingProvider` remains (else add alias).

3. **CLI & automation helpers** – ensure
   `automation.CLIAutomation`, `IndexerAutomation`, `FileProcessor` APIs stay
   stable or provide wrapper.

4. **Server bootstrap (`mcprag/server.py`)** – remove guards that still test
   for deprecated SDK helpers; rely on REST layer flag only.

5. **Tests & scripts** – adjust import paths; no functional change expected.

---

Maintainers can use this document as a checklist while executing the refactor
and during code-review to ensure all dependent paths are updated and CI stays
green.

