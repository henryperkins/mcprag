#!/usr/bin/env python3
"""
Check actual index schema
"""

import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

client = SearchIndexClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

index = client.get_index("codebase-mcp-sota")

print("Index fields:")
for field in index.fields:
    if hasattr(field, 'name') and 'imports' in field.name:
        print(f"\nField: {field.name}")
        print(f"  Type: {field.type}")
        print(f"  Searchable: {getattr(field, 'searchable', None)}")
        print(f"  Analyzer: {getattr(field, 'analyzer_name', None)}")
        print(f"  All attributes: {dir(field)}")
        
# Check all collection fields
print("\n\nAll Collection fields:")
for field in index.fields:
    if hasattr(field, 'type') and 'Collection' in str(field.type):
        print(f"  {field.name}: {field.type}")