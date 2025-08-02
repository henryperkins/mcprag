# Vector Dimensions Update - 3072

## Overview

The Azure AI Search integration has been updated to use **3072-dimensional vectors** instead of the previous 1536 dimensions. This change provides richer semantic representations for improved search quality.

## Configuration Changes

### 1. Embedding Model Configuration

The system uses `text-embedding-3-large` which supports configurable dimensions:

```python
# In enhanced_rag/core/config.py
class EmbeddingConfig(BaseModel):
    """Embedding generation configuration"""
    provider: str = Field(default="azure_openai_http")
    model: str = Field(default="text-embedding-3-large")
    dimensions: int = Field(default=3072)  # Updated from 1536
```

### 2. Index Schema Updates

Vector fields in the search index must be configured with matching dimensions:

```python
# Vector field definition
SearchField(
    name="content_vector",
    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
    searchable=True,
    retrievable=True,
    vector_search_dimensions=3072,  # Must match embedding dimensions
    vector_search_profile_name="vector-profile-hnsw"
)
```

### 3. Vectorizer Configuration

The Azure OpenAI vectorizer is configured to use the same model:

```python
AzureOpenAIVectorizer(
    name="text-embedding-3-large-vectorizer",
    parameters={
        "resourceUri": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "deploymentId": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        "modelName": "text-embedding-3-large"
    }
)
```

## Migration Considerations

### Existing Indexes

If you have existing indexes with 1536-dimensional vectors, you'll need to:

1. **Create a new index** with 3072 dimensions
2. **Re-embed all documents** using the new dimension setting
3. **Migrate search queries** to use the new index

### Performance Impact

- **Storage**: 3072-dimensional vectors require approximately 2x more storage
- **Memory**: Increased memory usage for vector operations
- **Latency**: Slight increase in search latency due to larger vectors
- **Quality**: Improved semantic understanding and search relevance

### Compatibility

Ensure all components use the same dimensions:
- Embedding generation (3072)
- Index field definitions (3072)
- Vector search configurations (3072)
- Query vectorization (3072)

## Environment Variables

No changes needed to environment variables. The system automatically uses the configured dimensions from `config.py`.

## Testing

To verify the configuration:

```python
from enhanced_rag.core.config import get_config

cfg = get_config()
print(f"Embedding dimensions: {cfg.embedding.dimensions}")  # Should output: 3072
```

## Benefits

1. **Richer Representations**: More dimensions capture nuanced semantic meaning
2. **Better Disambiguation**: Improved distinction between similar concepts
3. **Enhanced Context**: Better understanding of code context and relationships
4. **Future-Proof**: Aligns with latest embedding model capabilities

## Notes

- The `text-embedding-3-large` model supports dimensions: 256, 1024, 1536, 3072
- We chose 3072 for maximum semantic richness
- The model automatically handles the dimension configuration