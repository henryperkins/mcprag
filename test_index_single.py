#!/usr/bin/env python3
"""
Test indexing a single document
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime

load_dotenv()

# Create a simple test document
doc = {
    "id": "test-001",
    "content": "def hello_world():\n    print('Hello, World!')",
    "repository": "test-repo",
    "file_path": "test.py",
    "file_name": "test.py",
    "language": "python",
    "last_modified": datetime.utcnow().isoformat() + "+00:00",
    "function_name": "hello_world",
    "class_name": None,
    "imports": [],  # Array field
    "dependencies": [],  # Array field
    "tags": [],  # Array field
    "detected_patterns": [],  # Array field
    "intent_keywords": [],  # Array field
    "git_authors": [],  # Array field
    "docstring": "",
    "comments": "",
    "signature": "def hello_world()",
    "start_line": 1,
    "end_line": 2,
    "chunk_type": "function",
    "semantic_context": "Simple hello world function"
}

# Create client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

try:
    # Upload single document
    result = client.upload_documents([doc])
    print(f"✅ Successfully indexed test document")
    
    # Search for it
    results = client.search("hello world", top=5)
    for r in results:
        print(f"Found: {r['function_name']} in {r['file_path']}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()