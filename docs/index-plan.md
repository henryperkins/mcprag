Complete plan to standardize indexing, eliminate drift, and enable all features

Objectives
- Use a single canonical index schema with vectors and semantic search enabled.
- Ensure vector dimensions and semantic configuration match runtime assumptions.
- Align ingestion to write required fields (including content_vector).
- Remove redundant creators that cause schema drift and confusion.
- Provide a repeatable validation and remediation workflow.

1) Environment and configuration
1.1 Set environment variables
- ACS_ENDPOINT, ACS_ADMIN_KEY
- ACS_INDEX_NAME=codebase-mcp-sota
- Optional (for integrated text-to-vector):
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_DEPLOYMENT_NAME

1.2 Runtime config defaults
- Keep dimensions 3072 for text-embedding-3-large:
  - [`enhanced_rag.core.EmbeddingConfig()`](enhanced_rag/core/config.py:35-43)
- Keep retrieval features enabled by default:
  - [`enhanced_rag.core.RetrievalConfig()`](enhanced_rag/core/config.py:76-83)
- Server index target:
  - [`mcprag.Config.INDEX_NAME`](mcprag/config.py:21)

2) Canonical index creation and usage
2.1 Only use EnhancedIndexBuilder for schema creation
- Canonical builder:
  - [`enhanced_rag/azure_integration/enhanced_index_builder.py`](enhanced_rag/azure_integration/enhanced_index_builder.py:1)
  - Use: create_enhanced_rag_index(index_name="codebase-mcp-sota", description="...", enable_vectors=True, enable_semantic=True) ([`enhanced_rag.azure_integration.EnhancedIndexBuilder.create_enhanced_rag_index()`](enhanced_rag/azure_integration/enhanced_index_builder.py:74-92,152-164,179-199))

2.2 Canonical create entrypoint (script to run)
- Run this script to create the index:
  - [`index/create_enhanced_index.py`](index/create_enhanced_index.py:1)
  - It creates “codebase-mcp-sota”, validates schema presence, and echoes config ([`index/create_enhanced_index.py`](index/create_enhanced_index.py:19-25,29-40))

2.3 Semantic configuration naming alignment
- “semantic-config” is emitted by the builder and used by retrieval:
  - [`enhanced_rag.azure_integration.EnhancedIndexBuilder._build_semantic_config`](enhanced_rag/azure_integration/enhanced_index_builder.py:636-656)
  - [`enhanced_rag.retrieval.hybrid_searcher.HybridSearcher`](enhanced_rag/retrieval/hybrid_searcher.py:332-343)

2.4 Integrated text-to-vector (optional)
- When AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME are set, builder attaches AzureOpenAIVectorizer:
  - [`enhanced_rag.azure_integration.EnhancedIndexBuilder._build_vector_search_config`](enhanced_rag/azure_integration/enhanced_index_builder.py:573-588,605-633)
- Otherwise, provide vectors client-side and avoid VectorizableTextQuery.

3) Ingestion strategy (choose one and standardize)
3.1 Automated ingestion via indexer/skills
- Use:
  - [`enhanced_rag/azure_integration/indexer_integration.py`](enhanced_rag/azure_integration/indexer_integration.py:1)
  - [`enhanced_rag/azure_integration/standard_skills.py`](enhanced_rag/azure_integration/standard_skills.py:1)
- Confirm mapping writes to content_vector and fields like content, function_name, repository, language.

3.2 Direct programmatic uploads
- Use:
  - [`enhanced_rag/azure_integration/document_operations.py`](enhanced_rag/azure_integration/document_operations.py:1)
- Ensure each document includes content_vector (array[float]) when not using integrated vectorizer.

4) Validation gates (automate in CI/startup)
4.1 Schema validation
- builder.validate_index_schema("codebase-mcp-sota", ["content","function_name","repository","language","content_vector"]) ([`enhanced_rag.azure_integration.EnhancedIndexBuilder.validate_index_schema`](enhanced_rag/azure_integration/enhanced_index_builder.py:899-930))

4.2 Vector dimension validation
- builder.validate_vector_dimensions("codebase-mcp-sota", expected=3072) ([`enhanced_rag.azure_integration.EnhancedIndexBuilder.validate_vector_dimensions`](enhanced_rag/azure_integration/enhanced_index_builder.py:932-1005))

4.3 Utility checks (keep and use)
- [`scripts/check_index_schema.py`](scripts/check_index_schema.py:1)
- [`scripts/check_index_schema_v2.py`](scripts/check_index_schema_v2.py:1)

5) Operational workflow
5.1 One-time remediation
- Stop ingestion jobs/indexers.
- Delete conflicting or redundant creators (see Section 6).
- Set env vars (Section 1.1).
- Create/recreate the index:
  - python index/create_enhanced_index.py
- Validate:
  - python scripts/check_index_schema.py
  - python scripts/check_index_schema_v2.py
  - Programmatic: validate_index_schema and validate_vector_dimensions
- Ingest a small sample via chosen ingestion path; verify content_vector and key fields are present in uploaded docs.
- Resume normal operations.

5.2 Ongoing guardrails
- On service startup or CI, run validation gates (Section 4).
- If mismatches are detected:
  - Drop and recreate index via EnhancedIndexBuilder.create_enhanced_rag_index
  - Re-ingest minimal sample, then resume full ingestion.

6) Files to remove to prevent confusion and schema drift
Remove these from the repository working directory:
- Alternate ad-hoc or redundant index creators:
  - [`azure_search_enhanced.py`](azure_search_enhanced.py:1)
  - [`index/create_index_3072.py`](index/create_index_3072.py:1)
  - [`scripts/create_index_with_skillset.py`](scripts/create_index_with_skillset.py:1)
  - [`scripts/create_index_mcp_aligned.py`](scripts/create_index_mcp_aligned.py:1)
  - [`scripts/create_index_from_json.py`](scripts/create_index_from_json.py:1)
  - [`scripts/create_index_rest.py`](scripts/create_index_rest.py:1)
  - [`scripts/recreate_index_for_mcp.py`](scripts/recreate_index_for_mcp.py:1)

- Optional to remove (if you standardize fully on the canonical builder and no longer need historical fixes):
  - [`index/recreate_index_fixed.py`](index/recreate_index_fixed.py:1)

7) Files to keep (canonical set)
- Builder and configuration:
  - [`enhanced_rag/azure_integration/enhanced_index_builder.py`](enhanced_rag/azure_integration/enhanced_index_builder.py:1)
  - [`enhanced_rag/core/config.py`](enhanced_rag/core/config.py:1)
- Canonical create entrypoint:
  - [`index/create_enhanced_index.py`](index/create_enhanced_index.py:1)
- Ingestion (keep only the path you’ll use):
  - [`enhanced_rag/azure_integration/indexer_integration.py`](enhanced_rag/azure_integration/indexer_integration.py:1)
  - [`enhanced_rag/azure_integration/standard_skills.py`](enhanced_rag/azure_integration/standard_skills.py:1)
  - [`enhanced_rag/azure_integration/document_operations.py`](enhanced_rag/azure_integration/document_operations.py:1)
- Retrieval and semantic config user:
  - [`enhanced_rag/retrieval/hybrid_searcher.py`](enhanced_rag/retrieval/hybrid_searcher.py:1)
- Validation helpers:
  - [`scripts/check_index_schema.py`](scripts/check_index_schema.py:1)
  - [`scripts/check_index_schema_v2.py`](scripts/check_index_schema_v2.py:1)
- Server config target:
  - [`mcprag/config.py`](mcprag/config.py:1)

8) Acceptance criteria
- Running python index/create_enhanced_index.py completes without error and logs vector profiles and semantic enabled.
- Validation scripts report:
  - content_vector exists and vector_search_dimensions == 3072
  - semantic_config named “semantic-config” attached
  - core fields (content, function_name, repository, language) present
- A sample ingestion shows content_vector arrays on documents.
- search_code returns results using enhanced backend (not bm25_only) and shows semantic behavior when requested.

9) Risk register and mitigations
- Risk: Embedding dimensions changed later.
  - Mitigation: Gate startup with validate_vector_dimensions; recreate index if drift is detected.
- Risk: New developers reintroduce alternate creators.
  - Mitigation: Remove redundant files (Section 6) and document the canonical path in README and CI checks.
- Risk: Semantic config renamed by mistake.
  - Mitigation: Unit test HybridSearcher’s use of “semantic-config” and validate index’s semantic config name via check scripts.

Execution order summary
1) Remove drift-causing files (Section 6).
2) Ensure env variables (Section 1.1).
3) Run canonical creator: python index/create_enhanced_index.py.
4) Validate schema and vectors (Section 4).
5) Ingest a test sample via chosen ingestion path.
6) Commit and enforce this plan with a CI job that re-runs validations on change.

This complete plan eliminates conflicting index definitions, enforces dimension and semantic alignment, and provides a repeatable workflow with clear file ownership and a cleanup list to avoid future confusion.
