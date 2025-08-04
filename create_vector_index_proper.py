#!/usr/bin/env python3
"""
Create Azure Search index with proper vector support using the automation framework
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid circular imports
from enhanced_rag.azure_integration.automation.index_manager import IndexAutomation

load_dotenv()

async def main():
    # Define the proper index schema with vector support
    index_schema = {
        "name": "codebase-mcp-sota",
        "fields": [
            # Key field
            {
                "name": "id",
                "type": "Edm.String",
                "key": True,
                "filterable": True,
                "retrievable": True,
                "searchable": False,
                "sortable": False,
                "facetable": False
            },
            # Content fields
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "analyzer": "en.microsoft"
            },
            # Vector field for content embeddings
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": 1536,  # Default to text-embedding-ada-002
                "vectorSearchProfile": "vector-profile-hnsw"
            },
            # Required MCP fields
            {
                "name": "repository",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "filterable": True,
                "sortable": True,
                "facetable": True
            },
            {
                "name": "file_path",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "filterable": True,
                "sortable": True
            },
            {
                "name": "language",
                "type": "Edm.String",
                "searchable": False,
                "retrievable": True,
                "filterable": True,
                "sortable": False,
                "facetable": True
            },
            # Optional but recommended fields
            {
                "name": "function_name",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "filterable": True
            },
            {
                "name": "class_name",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "filterable": True
            },
            {
                "name": "signature",
                "type": "Edm.String",
                "searchable": False,
                "retrievable": True
            },
            {
                "name": "docstring",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True
            },
            {
                "name": "semantic_context",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True
            },
            {
                "name": "chunk_type",
                "type": "Edm.String",
                "filterable": True,
                "retrievable": True
            },
            {
                "name": "chunk_id",
                "type": "Edm.String",
                "filterable": True,
                "retrievable": True
            },
            {
                "name": "start_line",
                "type": "Edm.Int32",
                "filterable": True,
                "retrievable": True,
                "searchable": False,
                "sortable": False
            },
            {
                "name": "end_line",
                "type": "Edm.Int32",
                "filterable": True,
                "retrievable": True,
                "searchable": False,
                "sortable": False
            },
            {
                "name": "last_modified",
                "type": "Edm.DateTimeOffset",
                "filterable": True,
                "sortable": True,
                "retrievable": True
            },
            {
                "name": "file_extension",
                "type": "Edm.String",
                "filterable": True,
                "facetable": True,
                "retrievable": True
            },
            {
                "name": "imports",
                "type": "Collection(Edm.String)",
                "searchable": True,
                "filterable": True,
                "retrievable": True
            },
            {
                "name": "dependencies",
                "type": "Collection(Edm.String)",
                "searchable": False,
                "filterable": False,
                "retrievable": True
            }
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "hnsw-config",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 12,
                        "efConstruction": 300,
                        "efSearch": 120,
                        "metric": "cosine"
                    }
                }
            ],
            "profiles": [
                {
                    "name": "vector-profile-hnsw",
                    "algorithm": "hnsw-config"
                }
            ]
        }
    }
    
    # Check if we have OpenAI configured for embeddings
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OpenAI API key detected - will use text-embedding-3-large (3072 dimensions)")
        # Update vector dimensions for text-embedding-3-large
        for field in index_schema["fields"]:
            if field["name"] == "content_vector":
                field["dimensions"] = 3072
    else:
        print("ℹ️  No OpenAI API key found - using default 1536 dimensions (text-embedding-ada-002)")
    
    # Initialize automation
    automation = IndexAutomation(
        endpoint=os.getenv("ACS_ENDPOINT"),
        api_key=os.getenv("ACS_ADMIN_KEY")
    )
    
    print(f"🔧 Creating/updating index: {index_schema['name']}")
    
    # Drop existing index and create new one
    result = await automation.recreate_index(index_schema)
    
    if result["created"]:
        print("✅ Created new index with vector support")
    
    # Validate the index
    validation = await automation.validate_index_schema(
        index_schema["name"],
        ["content", "function_name", "repository", "language", "content_vector"]
    )
    
    if validation["valid"]:
        print("✅ Schema validation passed")
        print(f"   Total fields: {validation['fieldCount']}")
    else:
        print("❌ Schema validation failed:")
        for issue in validation["issues"]:
            print(f"   - {issue['type']}: {issue['message']}")
    
    # Get index stats
    existing = await automation.ops.get_index(index_schema["name"])
    
    # Check vector search configuration
    vector_search = existing.get("vectorSearch")
    if vector_search:
        print("\n📊 Vector Search Configuration:")
        algorithms = vector_search.get("algorithms", [])
        for algo in algorithms:
            print(f"  - Algorithm: {algo['name']} ({algo['kind']})")
            if algo['kind'] == 'hnsw':
                params = algo.get('hnswParameters', {})
                print(f"    - m: {params.get('m')}")
                print(f"    - efConstruction: {params.get('efConstruction')}")
                print(f"    - efSearch: {params.get('efSearch')}")
                print(f"    - metric: {params.get('metric')}")
    
    print("\n✅ Index is ready for vector search!")
    print("\n🚀 Next steps:")
    print("1. Run: python reindex_with_embeddings.py")
    print("2. This will create embeddings for your documents and upload them")

if __name__ == "__main__":
    asyncio.run(main())