#!/usr/bin/env python3
"""
Test indexing with actual chunk data
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from smart_indexer import CodeChunker
import hashlib

load_dotenv()

# Create test chunk
test_code = '''
def hello_world():
    """Say hello"""
    print("Hello, World!")
'''

chunker = CodeChunker()
chunks = chunker.chunk_python_file(test_code, "test.py")
chunk = chunks[0]

# Create document from chunk
doc_id = hashlib.md5(f"test-repo:test.py:0".encode()).hexdigest()
doc = {
    "id": doc_id,
    "repository": "test-repo",
    "file_path": "test.py",
    "file_name": "test.py",
    "language": "python",
    "last_modified": "2024-01-01T00:00:00+00:00",
    **chunk  # Add all chunk fields
}

# Remove None values - Azure Search doesn't like them
doc = {k: v for k, v in doc.items() if v is not None}

print("Document to index:")
for k, v in doc.items():
    print(f"  {k}: {type(v).__name__} = {repr(v)[:100]}")

# Create client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

try:
    result = client.upload_documents([doc])
    print(f"\n✅ Successfully indexed document with chunk data")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()