#!/usr/bin/env python3
"""
Create Azure Search index with schema aligned to MCP server requirements
Includes all fields expected by mcp_server_sota.py
"""

import os
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, ComplexField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch, ScoringProfile, FreshnessScoringFunction,
    FreshnessScoringParameters, MagnitudeScoringFunction, MagnitudeScoringParameters,
    ScoringFunctionInterpolation, TextWeights
)
from azure.core.credentials import AzureKeyCredential
from datetime import timedelta

def create_mcp_aligned_index():
    """Create index with schema matching MCP server expectations"""
    
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        raise ValueError("Missing ACS_ENDPOINT or ACS_ADMIN_KEY environment variables")
    
    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
    
    # Define the index name
    index_name = "codebase-mcp-aligned"
    
    # Define fields matching MCP server expectations
    fields = [
        # Key field
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        
        # Repository and path fields (REQUIRED by MCP)
        SearchableField(name="repository", type=SearchFieldDataType.String, 
                       filterable=True, sortable=True, facetable=True),
        SearchableField(name="file_path", type=SearchFieldDataType.String,
                       filterable=True, sortable=True),
        
        # Language field (REQUIRED by MCP)
        SearchableField(name="language", type=SearchFieldDataType.String,
                       filterable=True, sortable=True, facetable=True),
        
        # Content fields (REQUIRED by MCP)
        SearchableField(name="content", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        SearchableField(name="code_content", type=SearchFieldDataType.String,
                       analyzer_name="standard.lucene"),
        
        # Semantic and context fields
        SearchableField(name="semantic_context", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        SearchableField(name="title", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        SearchableField(name="description", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        
        # Function/class metadata
        SearchableField(name="function_name", type=SearchFieldDataType.String,
                       filterable=True),
        SearchableField(name="class_name", type=SearchFieldDataType.String,
                       filterable=True),
        SearchableField(name="signature", type=SearchFieldDataType.String),
        SearchableField(name="docstring", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        
        # Line numbers for precise location
        SimpleField(name="start_line", type=SearchFieldDataType.Int32,
                   filterable=True, sortable=True),
        SimpleField(name="end_line", type=SearchFieldDataType.Int32,
                   filterable=True, sortable=True),
        
        # Dependencies and imports
        SearchableField(name="imports", type="Collection(Edm.String)",
                       filterable=True),
        SearchableField(name="dependencies", type="Collection(Edm.String)",
                       filterable=True),
        
        # Chunk metadata
        SimpleField(name="chunk_id", type=SearchFieldDataType.String,
                   filterable=True),
        SearchableField(name="chunk_type", type=SearchFieldDataType.String,
                       filterable=True, facetable=True),
        
        # File metadata
        SimpleField(name="file_extension", type=SearchFieldDataType.String,
                   filterable=True, facetable=True),
        SimpleField(name="size_bytes", type=SearchFieldDataType.Int64,
                   filterable=True, sortable=True),
        SimpleField(name="last_modified", type=SearchFieldDataType.DateTimeOffset,
                   filterable=True, sortable=True),
        
        # Git metadata
        SimpleField(name="git_branch", type=SearchFieldDataType.String,
                   filterable=True, facetable=True),
        SimpleField(name="git_commit", type=SearchFieldDataType.String,
                   filterable=True),
        SimpleField(name="git_last_modified", type=SearchFieldDataType.DateTimeOffset,
                   filterable=True, sortable=True),
        SearchableField(name="git_authors", type="Collection(Edm.String)",
                       filterable=True, facetable=True),
        
        # Quality and metrics
        SimpleField(name="quality_score", type=SearchFieldDataType.Double,
                   filterable=True, sortable=True),
        SimpleField(name="complexity_score", type=SearchFieldDataType.Double,
                   filterable=True, sortable=True),
        SimpleField(name="test_coverage", type=SearchFieldDataType.Double,
                   filterable=True, sortable=True),
        SimpleField(name="reference_count", type=SearchFieldDataType.Int32,
                   filterable=True, sortable=True),
        
        # Enhanced search features
        SearchableField(name="tags", type="Collection(Edm.String)",
                       filterable=True, facetable=True),
        SearchableField(name="intent_keywords", type="Collection(Edm.String)",
                       filterable=True),
        SearchableField(name="detected_patterns", type="Collection(Edm.String)",
                       filterable=True, facetable=True),
        SearchableField(name="framework", type=SearchFieldDataType.String,
                       filterable=True, facetable=True),
        
        # Comments for additional context
        SearchableField(name="comments", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        
        # Vector field for semantic search (3072 dimensions)
        SimpleField(
            name="content_vector",
            type="Collection(Edm.Single)",
            searchable=False,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile-3072"
        ),
        
        # Alternative vector field for code-specific embeddings
        SimpleField(
            name="code_vector", 
            type="Collection(Edm.Single)",
            searchable=False,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile-3072"
        ),
        
        # Scoring boost field
        SimpleField(name="score_boost", type=SearchFieldDataType.Double,
                   filterable=True, sortable=True),
    ]
    
    # Vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-3072",
                parameters={
                    "m": 8,
                    "efConstruction": 400,
                    "efSearch": 80,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile-3072",
                algorithm_configuration_name="hnsw-3072"
            )
        ]
    )
    
    # Semantic search configuration
    semantic_config = SemanticConfiguration(
        name="semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[
                SemanticField(field_name="content"),
                SemanticField(field_name="semantic_context"),
                SemanticField(field_name="docstring")
            ],
            keywords_fields=[
                SemanticField(field_name="tags"),
                SemanticField(field_name="intent_keywords")
            ]
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Scoring profiles for result ranking
    scoring_profiles = [
        ScoringProfile(
            name="code-freshness",
            functions=[
                FreshnessScoringFunction(
                    field_name="last_modified",
                    boost=2.0,
                    parameters=FreshnessScoringParameters(
                        boosting_duration=timedelta(days=30)
                    ),
                    interpolation=ScoringFunctionInterpolation.QUADRATIC
                ),
                MagnitudeScoringFunction(
                    field_name="quality_score",
                    boost=1.5,
                    parameters=MagnitudeScoringParameters(
                        boosting_range_start=0,
                        boosting_range_end=100,
                        should_boost_beyond_range_by_constant=False
                    ),
                    interpolation=ScoringFunctionInterpolation.LINEAR
                )
            ],
            function_aggregation="sum"
        ),
        ScoringProfile(
            name="code-relevance",
            text=TextWeights(
                weights={
                    "function_name": 3.0,
                    "class_name": 2.5,
                    "semantic_context": 2.0,
                    "content": 1.5,
                    "docstring": 1.2,
                    "comments": 1.0
                }
            ),
            function_aggregation="sum"
        )
    ]
    
    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
        scoring_profiles=scoring_profiles,
        default_scoring_profile="code-relevance"
    )
    
    # Delete existing index if it exists
    try:
        client.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")
    except Exception:
        pass
    
    # Create the new index
    result = client.create_index(index)
    print(f"Created index: {result.name}")
    print(f"Fields: {len(result.fields)}")
    print(f"Vector search enabled: Yes (3072 dimensions)")
    print(f"Semantic search enabled: Yes")
    print(f"Scoring profiles: {len(result.scoring_profiles)}")
    
    # Print field summary
    print("\nKey fields for MCP compatibility:")
    required_fields = ["repository", "file_path", "language", "content"]
    for field in required_fields:
        field_obj = next((f for f in result.fields if f.name == field), None)
        if field_obj:
            print(f"  ✓ {field}: {field_obj.type}")
        else:
            print(f"  ✗ {field}: MISSING")
    
    print("\nOptional fields for enhanced search:")
    optional_fields = ["function_name", "class_name", "signature", "imports", 
                      "dependencies", "semantic_context", "start_line", "end_line", 
                      "docstring", "chunk_type"]
    for field in optional_fields:
        field_obj = next((f for f in result.fields if f.name == field), None)
        if field_obj:
            print(f"  ✓ {field}: {field_obj.type}")
    
    return result

if __name__ == "__main__":
    create_mcp_aligned_index()