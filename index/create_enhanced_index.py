#!/usr/bin/env python3
"""
Create enhanced Azure Search index with all advanced features
"""

import asyncio
import sys
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    try:
        print("Creating Enhanced RAG Index...")
        builder = EnhancedIndexBuilder()
        
        # Create the main index
        index = await builder.create_enhanced_rag_index(
            index_name="codebase-mcp-sota",
            description="Enhanced code search index with AST analysis and vector search",
            enable_vectors=True,
            enable_semantic=True
        )
        
        print(f"✅ Created index: {index.name}")
        
        # Validate schema
        validation = await builder.validate_index_schema(
            "codebase-mcp-sota",
            ["content", "function_name", "repository", "language", "content_vector"]
        )
        
        if validation['valid']:
            print("✅ Schema validation passed")
            print(f"   Total fields: {validation['total_fields']}")
            print(f"   Has vector search: {validation['has_vector_search']}")
            print(f"   Has semantic search: {validation['has_semantic_search']}")
            print(f"   Scoring profiles: {', '.join(validation['scoring_profiles'])}")
        else:
            print(f"⚠️  Missing fields: {validation['missing_fields']}")
            
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())