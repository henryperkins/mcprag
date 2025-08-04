#!/usr/bin/env python3
"""
Test MCP protocol implementation
"""

import json
import sys
import subprocess
import time

def test_mcp_server():
    """Test if the MCP server implements the protocol correctly"""
    
    # Start the server in stdio mode
    proc = subprocess.Popen(
        [sys.executable, "mcp_server_sota.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    # Give server time to start
    time.sleep(2)
    
    # Send initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    print("Sending initialize request...")
    proc.stdin.write(json.dumps(initialize_request) + "\n")
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        print("Response:", response_line)
        response = json.loads(response_line)
        print("Parsed response:", json.dumps(response, indent=2))
    else:
        print("No response received")
        stderr = proc.stderr.read()
        print("Stderr:", stderr)
    
    # Send initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    print("\nSending initialized notification...")
    proc.stdin.write(json.dumps(initialized_notification) + "\n")
    proc.stdin.flush()
    
    # Give server time to process
    time.sleep(0.5)
    
    # Send tools/list request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    print("\nSending tools/list request...")
    proc.stdin.write(json.dumps(list_tools_request) + "\n")
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        print("Response:", response_line)
        response = json.loads(response_line)
        if "result" in response and "tools" in response["result"]:
            print(f"Found {len(response['result']['tools'])} tools")
            for tool in response['result']['tools'][:3]:  # Show first 3 tools
                print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    else:
        print("No response received")
    
    # Test a tool call
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "test",
                "max_results": 1
            }
        }
    }
    
    print("\nSending search_code tool call...")
    proc.stdin.write(json.dumps(search_request) + "\n")
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        print("Response received (truncated):", response_line[:200] + "...")
    else:
        print("No response received")
    
    # Clean up
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    test_mcp_server()