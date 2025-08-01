#!/usr/bin/env python3
"""
Test with minimal document
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# Create minimal document - only required fields
doc = {
    "id": "test-002",
    "content": "print('Hello')",
    "repository": "test",
    "file_path": "test.py",
    "file_name": "test.py", 
    "language": "python",
    "last_modified": "2024-01-01T00:00:00+00:00"
}

# Create client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

try:
    result = client.upload_documents([doc])
    print(f"✅ Successfully indexed minimal document")
except Exception as e:
    print(f"❌ Error: {e}")