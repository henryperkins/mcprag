#!/usr/bin/env python3
import json
import subprocess
import sys

def test_mcp_tools():
    """Test MCP server tool registration"""
    
    # Start MCP server process
    cmd = [sys.executable, "mcp_server_sota.py", "--mode", "rpc"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Send tools/list request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    
    # Send request and get response
    stdout, stderr = proc.communicate(input=json.dumps(request) + "\n", timeout=5)
    
    # Parse response
    if stdout:
        print("MCP Server Response:")
        print(stdout)
        try:
            response = json.loads(stdout.strip())
            if "result" in response and "tools" in response["result"]:
                print("\nRegistered tools:")
                for tool in response["result"]["tools"]:
                    print(f"- {tool['name']}: {tool['description']}")
            else:
                print("\nNo tools found in response")
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
    
    if stderr:
        print("\nServer output:", stderr)

if __name__ == "__main__":
    test_mcp_tools()