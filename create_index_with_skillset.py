#!/usr/bin/env python3
"""
Create Azure Search index with integrated skillset for MCP tools
Includes repository extraction, embeddings, and code analysis
"""

import os
import json
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, ComplexField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch, ScoringProfile, FreshnessScoringFunction,
    FreshnessScoringParameters, MagnitudeScoringFunction, MagnitudeScoringParameters,
    ScoringFunctionInterpolation, SearchIndexerSkillset, WebApiSkill,
    AzureOpenAIEmbeddingSkill, SplitSkill, InputFieldMappingEntry,
    OutputFieldMappingEntry, AIServicesByKey, SearchIndexer, SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer, FieldMapping
)
from azure.core.credentials import AzureKeyCredential
from datetime import timedelta

def create_index_schema(index_name: str = "codebase-mcp-sota-3072"):
    """Create index schema aligned with MCP server requirements"""
    
    fields = [
        # Key field
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        
        # Repository fields - CRITICAL for MCP
        SearchableField(name="repository", type=SearchFieldDataType.String, 
                       filterable=True, sortable=True, facetable=True),
        SearchableField(name="repo", type=SearchFieldDataType.String,  # Alias for compatibility
                       filterable=True, sortable=True, facetable=True),
        
        # Path fields - CRITICAL for MCP
        SearchableField(name="file_path", type=SearchFieldDataType.String,
                       filterable=True, sortable=True),
        SearchableField(name="path", type=SearchFieldDataType.String,  # Alias for compatibility
                       filterable=True, sortable=True),
        
        # Language field - CRITICAL for MCP
        SearchableField(name="language", type=SearchFieldDataType.String,
                       filterable=True, sortable=True, facetable=True),
        
        # Content fields - CRITICAL for MCP
        SearchableField(name="content", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        SearchableField(name="code_content", type=SearchFieldDataType.String,
                       analyzer_name="standard.lucene"),
        
        # Semantic and context fields
        SearchableField(name="semantic_context", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        SearchableField(name="title", type=SearchFieldDataType.String,
                       analyzer_name="en.lucene"),
        
        # Function/class metadata
        SearchableField(name="function_name", type=SearchFieldDataType.String,
                       filterable=True),
        SearchableField(name="class_name", type=SearchFieldDataType.String,
                       filterable=True),
        SearchableField(name="signature", type=SearchFieldDataType.String),
        SearchableField(name="docstring", type=SearchFieldDataType.String),
        
        # Line numbers
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
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32,
                   filterable=True, sortable=True),
        SimpleField(name="chunk_count", type=SearchFieldDataType.Int32,
                   filterable=True, sortable=True),
        
        # File metadata
        SimpleField(name="file_extension", type=SearchFieldDataType.String,
                   filterable=True, facetable=True),
        SimpleField(name="size", type=SearchFieldDataType.Int64,
                   filterable=True, sortable=True),
        SimpleField(name="updatedAt", type=SearchFieldDataType.DateTimeOffset,
                   filterable=True, sortable=True),
        
        # Git metadata
        SimpleField(name="branch", type=SearchFieldDataType.String,
                   filterable=True, facetable=True),
        SimpleField(name="owner", type=SearchFieldDataType.String,
                   filterable=True, facetable=True),
        SimpleField(name="filename", type=SearchFieldDataType.String,
                   filterable=True, sortable=True),
        
        # Enhanced search features
        SearchableField(name="tags", type="Collection(Edm.String)",
                       filterable=True, facetable=True),
        SearchableField(name="topics", type="Collection(Edm.String)",
                       filterable=True, facetable=True),
        
        # Vector fields for semantic search (3072 dimensions)
        SimpleField(
            name="content_vector",
            type="Collection(Edm.Single)",
            searchable=False,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-hnsw-3072"
        ),
        SimpleField(
            name="embedding_content", 
            type="Collection(Edm.Single)",
            searchable=False,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-hnsw-3072"
        ),
        SimpleField(
            name="embedding_code",
            type="Collection(Edm.Single)", 
            searchable=False,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-hnsw-3072"
        ),
        
        # Scoring boost field
        SimpleField(name="score_boost", type=SearchFieldDataType.Double,
                   filterable=True, sortable=True),
    ]
    
    # Vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="vector-hnsw-3072",
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
                name="vector-hnsw-3072",
                algorithm_configuration_name="vector-hnsw-3072"
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
                SemanticField(field_name="code_content")
            ],
            keywords_fields=[
                SemanticField(field_name="tags")
            ]
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Scoring profiles
    scoring_profiles = [
        ScoringProfile(
            name="recencyBoost",
            functions=[
                FreshnessScoringFunction(
                    field_name="updatedAt",
                    boost=1.2,
                    parameters=FreshnessScoringParameters(
                        boosting_duration=timedelta(days=30)
                    ),
                    interpolation=ScoringFunctionInterpolation.QUADRATIC
                ),
                MagnitudeScoringFunction(
                    field_name="score_boost",
                    boost=1.5,
                    parameters=MagnitudeScoringParameters(
                        boosting_range_start=0,
                        boosting_range_end=5,
                        should_boost_beyond_range_by_constant=False
                    ),
                    interpolation=ScoringFunctionInterpolation.LINEAR
                )
            ],
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
        default_scoring_profile="recencyBoost",
        cors_options={"allowed_origins": ["*"]}
    )
    
    return index

def create_skillset(skillset_name: str = "codebase-mcp-skillset"):
    """Create skillset for extracting repository info and generating embeddings"""
    
    # Repository extraction skill (custom WebAPI)
    repo_extraction_skill = WebApiSkill(
        name="extract-repository-info",
        description="Extract repository name from file path",
        context="/document",
        uri=os.getenv("REPO_EXTRACTION_API", "https://your-function-app.azurewebsites.net/api/extract-repo"),
        http_method="POST",
        timeout="PT30S",
        batch_size=10,
        inputs=[
            InputFieldMappingEntry(name="file_path", source="/document/file_path"),
            InputFieldMappingEntry(name="metadata_storage_path", source="/document/metadata_storage_path")
        ],
        outputs=[
            OutputFieldMappingEntry(name="repository", target_name="repository"),
            OutputFieldMappingEntry(name="owner", target_name="owner"),
            OutputFieldMappingEntry(name="branch", target_name="branch")
        ]
    )
    
    # Content embedding skill
    content_embedding_skill = AzureOpenAIEmbeddingSkill(
        name="generate-content-embeddings",
        description="Generate embeddings for semantic content",
        context="/document",
        resource_uri=os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-openai.openai.azure.com"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        deployment_id=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        dimensions=3072,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/content")
        ],
        outputs=[
            OutputFieldMappingEntry(name="embedding", target_name="content_vector")
        ]
    )
    
    # Code embedding skill (separate for code-specific embeddings)
    code_embedding_skill = AzureOpenAIEmbeddingSkill(
        name="generate-code-embeddings",
        description="Generate embeddings for code content",
        context="/document",
        resource_uri=os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-openai.openai.azure.com"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        deployment_id=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        dimensions=3072,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/code_content")
        ],
        outputs=[
            OutputFieldMappingEntry(name="embedding", target_name="embedding_code")
        ]
    )
    
    # Text splitting skill for large documents
    split_skill = SplitSkill(
        name="split-text",
        description="Split large text into chunks",
        context="/document",
        text_split_mode="pages",
        maximum_page_length=2000,
        page_overlap_length=200,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/content")
        ],
        outputs=[
            OutputFieldMappingEntry(name="textItems", target_name="pages")
        ]
    )
    
    # Cognitive services configuration
    cognitive_services = AIServicesByKey(
        key=os.getenv("COGNITIVE_SERVICES_KEY"),
        subdomain_url=os.getenv("COGNITIVE_SERVICES_ENDPOINT", "https://your-cognitive-services.cognitiveservices.azure.com/")
    )
    
    # Create the skillset
    skillset = SearchIndexerSkillset(
        name=skillset_name,
        description="Skillset for MCP code search with repository extraction and embeddings",
        skills=[repo_extraction_skill, content_embedding_skill, code_embedding_skill, split_skill],
        cognitive_services_account=cognitive_services
    )
    
    return skillset

def create_indexer(indexer_name: str, index_name: str, skillset_name: str, datasource_name: str):
    """Create indexer with field mappings for MCP compatibility"""
    
    # Field mappings to ensure compatibility
    field_mappings = [
        FieldMapping(source_field_name="metadata_storage_path", target_field_name="file_path"),
        FieldMapping(source_field_name="metadata_storage_path", target_field_name="path"),  # Alias
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="filename"),
        FieldMapping(source_field_name="metadata_storage_size", target_field_name="size"),
        FieldMapping(source_field_name="metadata_storage_last_modified", target_field_name="updatedAt")
    ]
    
    # Output field mappings from skillset
    output_field_mappings = [
        FieldMapping(source_field_name="/document/repository", target_field_name="repository"),
        FieldMapping(source_field_name="/document/repository", target_field_name="repo"),  # Alias
        FieldMapping(source_field_name="/document/owner", target_field_name="owner"),
        FieldMapping(source_field_name="/document/branch", target_field_name="branch"),
        FieldMapping(source_field_name="/document/content_vector", target_field_name="content_vector"),
        FieldMapping(source_field_name="/document/content_vector", target_field_name="embedding_content"),
        FieldMapping(source_field_name="/document/embedding_code", target_field_name="embedding_code")
    ]
    
    indexer = SearchIndexer(
        name=indexer_name,
        description="Indexer for MCP code search",
        skillset_name=skillset_name,
        target_index_name=index_name,
        data_source_name=datasource_name,
        field_mappings=field_mappings,
        output_field_mappings=output_field_mappings
    )
    
    return indexer

def main():
    """Create complete indexing pipeline"""
    
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        raise ValueError("Missing ACS_ENDPOINT or ACS_ADMIN_KEY")
    
    # Initialize clients
    index_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
    
    # Create index
    index_name = "codebase-mcp-sota-3072"
    index = create_index_schema(index_name)
    
    try:
        index_client.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")
    except:
        pass
    
    result = index_client.create_index(index)
    print(f"Created index: {result.name}")
    
    # Verify critical fields
    print("\nVerifying MCP-required fields:")
    required_fields = ["repository", "file_path", "language", "content"]
    for field_name in required_fields:
        field = next((f for f in result.fields if f.name == field_name), None)
        if field:
            print(f"  ✓ {field_name}: {field.type}")
        else:
            print(f"  ✗ {field_name}: MISSING!")
    
    # Create skillset
    skillset_name = "codebase-mcp-skillset"
    skillset = create_skillset(skillset_name)
    
    try:
        indexer_client.delete_skillset(skillset_name)
        print(f"\nDeleted existing skillset: {skillset_name}")
    except:
        pass
    
    result_skillset = indexer_client.create_skillset(skillset)
    print(f"Created skillset: {result_skillset.name}")
    print(f"Skills: {len(result_skillset.skills)}")
    
    print("\nIndexing pipeline ready for MCP tools!")
    print("\nNext steps:")
    print("1. Create a data source pointing to your code repository")
    print("2. Create an indexer using the data source and this schema")
    print("3. Run the indexer to populate the index")
    print("4. The MCP server will now work with proper field mappings")

if __name__ == "__main__":
    main()