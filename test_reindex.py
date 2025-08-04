#!/usr/bin/env python3
"""
Direct test of re-indexing functionality
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import json

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
index_name = "codebase-mcp-sota"

print(f"🔧 Testing index operations...")
print(f"📍 Endpoint: {endpoint}")
print(f"📚 Index: {index_name}")

if not endpoint or not admin_key:
    print("❌ Missing Azure Search credentials")
    sys.exit(1)

try:
    # Create search client
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Test basic operations
    print("\n📊 Getting document count...")
    count = search_client.get_document_count()
    print(f"✅ Current documents: {count}")
    
    # Test search
    print("\n🔍 Testing search...")
    results = search_client.search(
        search_text="test",
        top=2,
        include_total_count=True
    )
    
    print(f"✅ Search works! Found {results.get_count()} results")
    
    # Show sample result structure
    for i, result in enumerate(results):
        if i == 0:
            print("\n📄 Sample document structure:")
            print(json.dumps(dict(result), indent=2))
        break
    
    # Create a test document
    print("\n📝 Testing document upload...")
    test_doc = {
        "id": "test_mcprag_reindex",
        "content": "# Test Document\nThis is a test to verify indexing works",
        "file_path": "test_reindex.md",
        "repository": "mcprag",
        "language": "markdown",
        "chunk_id": 0,
        "title": "Test Reindex Document"
    }
    
    # Upload document
    result = search_client.merge_or_upload_documents([test_doc])
    print("✅ Document uploaded successfully!")
    
    # Verify it was indexed
    doc = search_client.get_document(key="test_mcprag_reindex")
    print(f"✅ Document verified: {doc['file_path']}")
    
    print("\n✅ All tests passed! Indexing is working.")
    print("\n📋 Next steps:")
    print("1. The index is working and accepts documents")
    print("2. To fully re-index mcprag, we need to:")
    print("   - Parse all code files in the repository")
    print("   - Extract functions/classes with proper metadata")
    print("   - Upload documents with correct schema")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()