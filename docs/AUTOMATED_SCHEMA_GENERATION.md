# Automated Schema Generation for Azure AI Search

## Overview

The automated schema generation system provides a dynamic way to create and negotiate index schemas with Azure AI Search, eliminating manual schema file maintenance and ensuring compatibility with your Azure service tier.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Feature Request   │────►│  Schema Automation   │────►│  Azure AI Search │
│  (vector, semantic) │     │    Engine            │     │   Service        │
└─────────────────────┘     └──────────────────────┘     └─────────────────┘
                                      │                             │
                            ┌─────────▼────────┐          ┌────────▼────────┐
                            │ Capability       │          │ Schema          │
                            │ Detection        │          │ Validation      │
                            └──────────────────┘          └─────────────────┘
                                      │                             │
                            ┌─────────▼────────┐          ┌────────▼────────┐
                            │ Schema           │          │ Compatibility   │
                            │ Generation       │          │ Adjustment      │
                            └──────────────────┘          └─────────────────┘
```

## Components

### 1. **SchemaAutomation** (`schema_automation.py`)

Core engine that handles:
- Azure capability detection
- Feature-based schema generation
- Schema negotiation with Azure
- Safe update identification

### 2. **CLI Integration** (`cli_schema_automation.py`)

Command-line interface providing:
- `detect-capabilities`: Discover what Azure supports
- `generate-schema`: Create schemas from feature lists
- `negotiate-schema`: Test and adjust schemas
- `update-schema`: Add features to existing indexes
- `compare-schemas`: Diff two schema files

## How It Works

### Step 1: Capability Detection

The system attempts to create test indexes with various features to detect what's supported:

```python
# Detects:
# - Maximum vector dimensions (3072 vs 1536)
# - Semantic search availability
# - Custom analyzer support
# - API version compatibility
capabilities = await detect_azure_capabilities()
```

**Current Findings** (2025-05-01-preview API):
- ✅ Vector search: Supported with up to 3072 dimensions
- ❌ Semantic search: Property 'semanticSearch' not recognized
- ❌ Custom analyzers: 'standard' tokenizer not supported

### Step 2: Feature-Based Generation

Generate schemas based on requested features:

```python
schema = await generate_schema_from_features(
    features=["vector_search", "faceted_search"],
    custom_fields=[...]
)
```

Maps features to required fields:
- `vector_search` → Adds content_vector field with detected dimensions
- `semantic_search` → Adds content field with analyzer
- `faceted_search` → Adds facetable repository/language fields

### Step 3: Schema Negotiation

Tests schema with Azure and makes adjustments:

```python
result = await negotiate_schema_with_azure(schema, "my-index")
```

Automatic adjustments:
1. Removes `searchable` from non-string fields
2. Fixes vector field attributes (no filterable/sortable)
3. Adjusts analyzer references
4. Documents all changes made

### Step 4: Safe Updates

Identifies what can be changed without reindexing:

```python
result = await update_existing_index_schema("my-index", ["scoring_profiles"])
```

Safe updates:
- ✅ Adding new fields
- ✅ Adding scoring profiles
- ❌ Changing field types (requires reindex)
- ❌ Modifying key fields (requires reindex)

## Usage Examples

### Basic Schema Generation

```bash
# Generate minimal schema with core features
python -m enhanced_rag.azure_integration.cli generate-schema \
  --name codebase-mcp-sota \
  --features vector_search faceted_search \
  --output schema.json
```

### Complete Workflow

```bash
# 1. Detect capabilities
python -m enhanced_rag.azure_integration.cli detect-capabilities \
  --output capabilities.json

# 2. Generate schema with all features
python -m enhanced_rag.azure_integration.cli generate-schema \
  --name codebase-mcp-sota \
  --features vector_search semantic_search faceted_search \
  --custom-fields custom_fields.json \
  --output full_schema.json

# 3. Negotiate and create
python -m enhanced_rag.azure_integration.cli negotiate-schema \
  --index-name codebase-mcp-sota \
  --schema-file full_schema.json \
  --create-index

# 4. Compare with existing
python -m enhanced_rag.azure_integration.cli compare-schemas \
  azure_search_index_schema.json \
  full_schema.json
```

### Custom Fields Definition

Create `custom_fields.json`:

```json
[
  {
    "name": "custom_metadata",
    "type": "string",
    "searchable": true,
    "filterable": true
  },
  {
    "name": "priority_score",
    "type": "double",
    "filterable": true,
    "sortable": true
  }
]
```

## Schema Comparison

The system can compare schemas to identify differences:

```bash
python -m enhanced_rag.azure_integration.cli compare-schemas \
  old_schema.json new_schema.json
```

Shows:
- Fields only in each schema
- Field attribute differences
- Feature differences

## Integration with Existing System

### Using Generated Schema

1. **Replace static schema file**:
   ```bash
   mv generated_schema.json azure_search_index_schema.json
   ```

2. **Use in index creation**:
   ```python
   python index/create_enhanced_index.py
   ```

3. **Validate before indexing**:
   ```python
   python scripts/validate_index_canonical.py
   ```

### Programmatic Usage

```python
from enhanced_rag.azure_integration import SchemaAutomation

async def create_optimal_index():
    automation = SchemaAutomation()
    
    # Generate based on capabilities
    schema = await automation.generate_schema_from_features(
        features=["vector_search", "faceted_search"],
        custom_fields=existing_fields
    )
    
    # Negotiate with Azure
    result = await automation.negotiate_schema_with_azure(
        schema, "my-index"
    )
    
    if result["success"]:
        print("Schema created:", result["negotiated"])
```

## Benefits

1. **Dynamic Compatibility**: Adapts to your Azure service capabilities
2. **No Manual Maintenance**: Schema generated from feature requirements
3. **Automatic Fixes**: Adjusts for API version differences
4. **Safe Updates**: Knows what can be changed without data loss
5. **Version Agnostic**: Works across different Azure API versions

## Current Limitations

1. **API Version Issues**: Some features (semantic search, custom analyzers) not supported in 2025-05-01-preview
2. **Limited Testing**: Capability detection could be more comprehensive
3. **No Rollback**: Schema changes are permanent once applied

## Future Enhancements

1. **Schema Versioning**: Track schema evolution over time
2. **Automatic Migration**: Generate migration scripts for breaking changes
3. **A/B Testing**: Support multiple schema versions simultaneously
4. **Webhook Integration**: Notify on schema changes
5. **Schema Templates**: Pre-built schemas for common use cases

## Troubleshooting

### Common Issues

1. **"Property not recognized" errors**: API version doesn't support the feature
2. **"Invalid tokenizer" errors**: Use built-in analyzers instead of custom
3. **Vector dimension mismatch**: Ensure embedding model matches schema

### Debug Mode

Set logging to DEBUG for detailed information:

```python
import logging
logging.getLogger('enhanced_rag.azure_integration').setLevel(logging.DEBUG)
```

## Conclusion

The automated schema generation system transforms index creation from a static, manual process to a dynamic, capability-aware system that adapts to your Azure environment. This ensures optimal schema configuration while maintaining compatibility across different Azure service tiers and API versions.