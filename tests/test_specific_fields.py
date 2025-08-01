#!/usr/bin/env python3
"""
Test specific array fields
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# Base document
base_doc = {
    "id": "test-array-field",
    "content": "test content",
    "repository": "test",
    "file_path": "test.py",
    "file_name": "test.py",
    "language": "python",
    "last_modified": "2024-01-01T00:00:00+00:00"
}

# Test each array field individually
array_fields = [
    ("imports", ["os", "sys"]),
    ("dependencies", ["print", "len"]),
    ("tags", ["test", "example"]),
    ("git_authors", ["user1", "user2"]),
    ("detected_patterns", ["singleton", "factory"]),
    ("intent_keywords", ["implement", "create"])
]

# Create client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

print("Testing individual array fields...")
for field_name, field_value in array_fields:
    doc = base_doc.copy()
    doc["id"] = f"test-{field_name}"
    doc[field_name] = field_value
    
    print(f"\nTesting {field_name}: {field_value}")
    try:
        result = client.upload_documents([doc])
        print(f"  ✅ Success")
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")