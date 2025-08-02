# Vector Compression Guide for Azure AI Search

## Overview

Based on the Azure AI Search documentation, vector compression can significantly reduce storage requirements and improve performance for large-scale vector indexes. This guide explains how to implement compression when SDK support is available.

## Compression Types

### 1. **Scalar Quantization**
- Reduces float32/float16 to int8
- **Compression ratio**: 4x reduction
- **Best for**: General-purpose vector compression
- **Quality impact**: Minimal with rescoring enabled

### 2. **Binary Quantization**
- Converts floats to 1-bit values
- **Compression ratio**: Up to 28x reduction
- **Best for**: High-dimensional vectors (≥1024 dimensions)
- **Recommended for**: Models like text-embedding-3-large (3072 dimensions)

## Implementation Strategy

### Current Implementation (Without Compression)

Our current implementation optimizes storage by:

1. **Setting `retrievable=False`** on vector fields
   - Prevents raw vectors from being returned in search results
   - Reduces network overhead

2. **Setting `stored=False`** on vector fields
   - Optimizes storage for future compression support
   - Prepares index for compression migration

```python
vector_field = SearchField(
    name="content_vector",
    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
    searchable=True,
    retrievable=False,  # Optimizes storage
    stored=False,       # Prepares for compression
    vector_search_dimensions=3072,
    vector_search_profile_name="vector-profile-hnsw"
)
```

### Future Implementation (With SDK Support)

When Azure SDK adds compression support, implement as follows:

```python
# Define compressions
compressions = [
    {
        "name": "scalar-quantization",
        "kind": "scalarQuantization",
        "rerankWithOriginalVectors": True,
        "defaultOversampling": 10.0,
        "scalarQuantizationParameters": {
            "quantizedDataType": "int8"
        }
    },
    {
        "name": "binary-quantization",
        "kind": "binaryQuantization",
        "rerankWithOriginalVectors": True,
        "defaultOversampling": 10.0
    }
]

# Create compressed vector profiles
profiles = [
    {
        "name": "vector-profile-hnsw-scalar",
        "compression": "scalar-quantization",
        "algorithm": "hnsw-algorithm",
        "vectorizer": "text-embedding-3-large-vectorizer"
    },
    {
        "name": "vector-profile-hnsw-binary",
        "compression": "binary-quantization",
        "algorithm": "hnsw-algorithm",
        "vectorizer": "text-embedding-3-large-vectorizer"
    }
]
```

## Benefits for 3072-Dimensional Vectors

With text-embedding-3-large's 3072 dimensions:

1. **Without compression**: ~12KB per vector
2. **With scalar quantization**: ~3KB per vector (4x reduction)
3. **With binary quantization**: ~384 bytes per vector (32x reduction)

For a 1M document index:
- Uncompressed: ~12GB vector storage
- Scalar compressed: ~3GB vector storage
- Binary compressed: ~384MB vector storage

## Rescoring and Quality Preservation

### Oversampling
- Retrieves more candidates than requested
- Formula: `k * oversampling_factor`
- Default: 10x oversampling (retrieve 100 to return 10)

### Rescoring with Original Vectors
- Uses uncompressed vectors for final ranking
- Maintains quality despite compression
- Automatically enabled in our configuration

## Query-Time Optimization

When querying compressed indexes:

```python
# Override oversampling at query time
vector_query = {
    "kind": "vector",
    "vector": embedding,
    "fields": "content_vector",
    "k": 10,
    "oversampling": 20.0  # Retrieve 200, return 10
}
```

## Migration Path

1. **Current state**: Optimized storage settings
2. **SDK update**: Add compression configurations
3. **Reindex**: Create new index with compression
4. **Validate**: Compare quality metrics
5. **Switch**: Update application to use compressed index

## Monitoring Compression Impact

Track these metrics:
- **Storage reduction**: Compare index sizes
- **Query latency**: Should improve with smaller vectors
- **Recall@k**: Should remain >95% with rescoring
- **Memory usage**: Significant reduction expected

## Best Practices

1. **Start with scalar quantization** for predictable quality
2. **Test binary quantization** for maximum savings
3. **Always enable rescoring** for quality preservation
4. **Monitor quality metrics** after compression
5. **Use appropriate oversampling** (10-20x typical)

## SDK Compatibility Note

The current Azure Search Python SDK (version 11.x) doesn't expose compression classes in the type system. When these become available, update the `enhanced_index_builder.py` to include compression configurations as shown above.

REST API users can implement compression immediately using the 2024-07-01 API version or later.