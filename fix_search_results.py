#!/usr/bin/env python3
"""
Test and fix the search results handling
"""
import os
import sys
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
index_name = "codebase-mcp-sota"

# Create search client
search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(admin_key)
)

print("🔍 Testing search result structure...")

# Do a simple search
results = search_client.search(
    search_text="test",
    filter="repository eq 'mcprag'",
    top=1
)

for result in results:
    print(f"\n📄 Result type: {type(result)}")
    print(f"📋 Result class: {result.__class__.__name__}")
    
    # Test different access methods
    print("\n🧪 Testing access methods:")
    
    # Method 1: Dictionary access
    try:
        lang1 = result['language']
        print(f"✅ result['language'] = {lang1}")
    except Exception as e:
        print(f"❌ result['language'] failed: {e}")
    
    # Method 2: get method
    try:
        lang2 = result.get('language', 'unknown')
        print(f"✅ result.get('language') = {lang2}")
    except Exception as e:
        print(f"❌ result.get('language') failed: {e}")
    
    # Method 3: Direct attribute
    try:
        lang3 = result.language
        print(f"✅ result.language = {lang3}")
    except Exception as e:
        print(f"❌ result.language failed: {e}")
    
    # Show all available fields
    print("\n📦 Available fields:")
    if hasattr(result, '__dict__'):
        for key, value in result.__dict__.items():
            print(f"  - {key}: {type(value).__name__}")
    else:
        # Try to iterate as dict
        try:
            for key in result:
                print(f"  - {key}: {type(result[key]).__name__}")
        except:
            print("  Unable to iterate fields")
    
    break  # Just test one result