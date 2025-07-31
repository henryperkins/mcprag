#!/usr/bin/env python3
"""
Test with arrays
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# Test different array configurations
tests = [
    {
        "name": "No arrays",
        "doc": {
            "id": "test-003",
            "content": "test",
            "repository": "test",
            "file_path": "test.py",
            "file_name": "test.py",
            "language": "python",
            "last_modified": "2024-01-01T00:00:00+00:00"
        }
    },
    {
        "name": "With empty imports",
        "doc": {
            "id": "test-004",
            "content": "test",
            "repository": "test",
            "file_path": "test.py",
            "file_name": "test.py",
            "language": "python",
            "last_modified": "2024-01-01T00:00:00+00:00",
            "imports": []
        }
    },
    {
        "name": "With filled imports",
        "doc": {
            "id": "test-005",
            "content": "test",
            "repository": "test",
            "file_path": "test.py",
            "file_name": "test.py",
            "language": "python",
            "last_modified": "2024-01-01T00:00:00+00:00",
            "imports": ["os", "sys"]
        }
    }
]

# Create client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

for test in tests:
    print(f"\nTesting: {test['name']}")
    try:
        result = client.upload_documents([test['doc']])
        print(f"  ✅ Success")
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")