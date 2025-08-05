#!/usr/bin/env python3
"""Test the azure-code-search MCP server connection."""

import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_azure_search_connection():
    """Test Azure Cognitive Search connection."""
    endpoint = os.getenv('ACS_ENDPOINT')
    api_key = os.getenv('ACS_ADMIN_KEY')
    index_name = os.getenv('ACS_INDEX_NAME', 'codebase-mcp-sota')
    
    print(f"Testing Azure Search connection...")
    print(f"Endpoint: {endpoint}")
    print(f"API Key: {'*' * 10 if api_key else 'NOT SET'}")
    print(f"Index Name: {index_name}")
    
    if not endpoint or not api_key:
        print("❌ Missing Azure Search credentials")
        return False
    
    # Test connection using the enhanced_rag module
    try:
        from enhanced_rag.azure_integration.config import AzureSearchConfig
        config = AzureSearchConfig.from_env()
        print(f"✅ Azure config loaded successfully")
        print(f"   - Endpoint: {config.endpoint}")
        print(f"   - API Version: {config.api_version}")
        
        # Test actual connection
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        client = AzureSearchClient(config.endpoint, config.api_key, config.api_version)
        
        # Try to get index info
        response = client.get(f"/indexes/{index_name}")
        if response and response.get('name') == index_name:
            print(f"✅ Successfully connected to index: {index_name}")
            print(f"   - Document Count: {response.get('@odata.count', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to connect to index")
            return False
    except Exception as e:
        print(f"❌ Failed to load Azure config: {e}")
        return False

def test_mcp_server():
    """Test the MCP server startup."""
    print("\nTesting MCP server startup...")
    
    # Try to start the server with a test request
    test_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {}
        },
        "id": 1
    }
    
    try:
        # Start the MCP server
        process = subprocess.Popen(
            [sys.executable, "-m", "mcprag"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send test request
        process.stdin.write(json.dumps(test_request) + '\n')
        process.stdin.flush()
        
        # Read response (with timeout)
        import select
        ready, _, _ = select.select([process.stdout], [], [], 5.0)
        
        if ready:
            response = process.stdout.readline()
            if response:
                print("✅ MCP server responded:")
                print(f"   {response.strip()}")
                process.terminate()
                return True
        
        process.terminate()
        print("❌ MCP server did not respond within 5 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        return False

def main():
    print("Azure Code Search MCP Server Test")
    print("=" * 50)
    
    # Test Azure connection
    azure_ok = test_azure_search_connection()
    
    # Test MCP server
    mcp_ok = test_mcp_server()
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Azure Search Connection: {'✅ OK' if azure_ok else '❌ FAILED'}")
    print(f"MCP Server Startup: {'✅ OK' if mcp_ok else '❌ FAILED'}")
    
    return 0 if (azure_ok and mcp_ok) else 1

if __name__ == "__main__":
    sys.exit(main())