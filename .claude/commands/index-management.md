# Azure Search Index Management

Manage Azure Cognitive Search indices for the MCP server.

## Purpose

This command helps you create, validate, and manage search indices that power the MCP code search functionality.

## Usage

```
/index-management
```

## Quick Commands

### Check Index Status
```bash
# View current index status and document count
python -m enhanced_rag.azure_integration.cli reindex --method status

# Validate index schema
python -m enhanced_rag.azure_integration.cli reindex --method validate

# Check detailed schema
python scripts/check_index_schema_v2.py
```

### Index Your Repository
```bash
# Index the current repository
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag

# Index with specific file patterns
python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name mcprag --patterns "*.py" "*.js"

# Index only changed files (for CI/CD)
python -m enhanced_rag.azure_integration.cli changed-files --files file1.py file2.js --repo-name mcprag
```

### Reindex Operations
```bash
# Backup current schema before changes
python -m enhanced_rag.azure_integration.cli reindex --method backup --output schema_backup.json

# Drop and rebuild index (CAUTION: deletes all data)
python -m enhanced_rag.azure_integration.cli reindex --method drop-rebuild

# Clear documents from specific repository
python -m enhanced_rag.azure_integration.cli reindex --method clear --filter "repository eq 'old-repo'"
```

### Create/Update Index
```bash
# Create canonical index with all features
python index/create_enhanced_index.py

# Validate canonical index configuration
python scripts/validate_index_canonical.py
```

## Best Practices

1. **Always backup** before schema changes
2. **Validate after indexing** to ensure success
3. **Use incremental indexing** for updates
4. **Monitor document count** to track progress
5. **Keep embeddings updated** for semantic search

## Environment Variables

Ensure these are set in your `.env`:
```
ACS_ENDPOINT=https://your-search.search.windows.net
ACS_ADMIN_KEY=your-admin-key
AZURE_OPENAI_KEY=your-openai-key (optional for embeddings)
```