#!/usr/bin/env python3
"""
Test script to verify the MCP RAG setup is working correctly.
"""
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()


def test_azure_connection():
    """Test connection to Azure Cognitive Search."""
    print("🔍 Testing Azure Cognitive Search connection...")

    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")

    if not endpoint or not admin_key:
        print("❌ Missing ACS_ENDPOINT or ACS_ADMIN_KEY in .env file")
        return False

    # Test service info endpoint
    url = f"{endpoint}/servicestats?api-version=2023-11-01"
    headers = {"api-key": admin_key}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ Azure Cognitive Search connection successful")
            return True
        else:
            print(f"❌ Azure connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Azure connection error: {e}")
        return False


def test_index_exists():
    """Test if the search index exists."""
    print("🔍 Checking if search index exists...")

    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")

    url = f"{endpoint}/indexes/codebase-mcp-sota?api-version=2023-11-01"
    headers = {"api-key": admin_key}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ Search index 'codebase-mcp-sota' exists")
            return True
        else:
            print(f"❌ Search index not found: {response.status_code}")
            print("   Run: python create_index.py")
            return False
    except Exception as e:
        print(f"❌ Index check error: {e}")
        return False


def test_mcp_server():
    """Test if MCP server is running."""
    print("🔍 Testing MCP server...")

    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ MCP server is running")
            return True
        else:
            print(f"❌ MCP server error: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ MCP server not running")
        print("   Run: python mcp_server.py")
        return False
    except Exception as e:
        print(f"❌ MCP server test error: {e}")
        return False


def test_search_functionality():
    """Test search functionality."""
    print("🔍 Testing search functionality...")

    search_data = {"query": "function", "max_results": 5}

    try:
        response = requests.post(
            "http://localhost:8001/search", json=search_data, timeout=10
        )

        if response.status_code == 200:
            results = response.json()
            result_count = len(results.get("results", []))
            print(f"✅ Search working - found {result_count} results")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Search test error: {e}")
        return False


def test_mcp_endpoint():
    """Test MCP-compatible endpoint."""
    print("🔍 Testing MCP endpoint...")

    mcp_data = {"input": "authentication"}

    try:
        response = requests.post(
            "http://localhost:8001/mcp-query", json=mcp_data, timeout=10
        )

        if response.status_code == 200:
            results = response.json()
            context_count = len(results.get("context", []))
            print(f"✅ MCP endpoint working - found {context_count} context items")
            return True
        else:
            print(f"❌ MCP endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ MCP endpoint test error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running MCP RAG System Tests")
    print("=" * 40)

    tests = [
        ("Azure Connection", test_azure_connection),
        ("Search Index", test_index_exists),
        ("MCP Server", test_mcp_server),
        ("Search Functionality", test_search_functionality),
        ("MCP Endpoint", test_mcp_endpoint),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        time.sleep(1)  # Brief pause between tests

    print(f"\n📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Your MCP RAG system is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

        if passed < 2:
            print("\n💡 Quick fixes:")
            print("   1. Ensure .env file exists with correct Azure credentials")
            print("   2. Run: python create_index.py")
            print("   3. Run: python indexer.py")
            print("   4. Run: python mcp_server.py")


if __name__ == "__main__":
    main()
