#!/usr/bin/env python3
"""Test which MCP servers are actually functional."""

import json
import subprocess
import os
import sys
from pathlib import Path

def test_python_module(module_name):
    """Test if a Python module can be imported."""
    try:
        # Try to import the module
        result = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def test_command(command, args=None):
    """Test if a command exists and is executable."""
    try:
        cmd = [command]
        if args:
            cmd.extend(args)
        result = subprocess.run(
            cmd + ["--help"],  # Most commands support --help
            capture_output=True,
            text=True,
            timeout=5
        )
        # Check if command exists (not just return code)
        if "not found" in result.stderr or result.returncode == 127:
            return False, "Command not found"
        return True, "Command exists"
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)

def main():
    # Read all MCP configurations
    config_files = ['.mcp.json', 'mcp-servers.json', '.roo/mcp.json']
    
    results = []
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            continue
            
        with open(config_file) as f:
            data = json.load(f)
            servers = data.get('mcpServers', {})
            
            for name, config in servers.items():
                command = config.get('command', 'N/A')
                args = config.get('args', [])
                
                if command == 'python3' and '-m' in args:
                    # Python module
                    module_idx = args.index('-m') + 1
                    if module_idx < len(args):
                        module_name = args[module_idx]
                        success, error = test_python_module(module_name)
                        results.append({
                            'server': name,
                            'type': 'python-module',
                            'module': module_name,
                            'functional': success,
                            'error': error if not success else None,
                            'config_file': config_file
                        })
                elif command in ['npx', 'uvx']:
                    # Node/Python package runner
                    package = args[0] if args else 'unknown'
                    success, error = test_command(command, args[:1])
                    results.append({
                        'server': name,
                        'type': f'{command}-package',
                        'package': package,
                        'functional': success,
                        'error': error if not success else None,
                        'config_file': config_file
                    })
                else:
                    # Direct command
                    success, error = test_command(command)
                    results.append({
                        'server': name,
                        'type': 'direct-command',
                        'command': command,
                        'functional': success,
                        'error': error if not success else None,
                        'config_file': config_file
                    })
    
    # Print results
    print("\nMCP Server Status Report")
    print("=" * 80)
    
    functional_count = sum(1 for r in results if r['functional'])
    total_count = len(results)
    
    print(f"\nTotal servers configured: {total_count}")
    print(f"Functional servers: {functional_count}")
    print(f"Non-functional servers: {total_count - functional_count}")
    
    print("\n✅ Functional Servers:")
    print("-" * 40)
    for result in results:
        if result['functional']:
            print(f"  • {result['server']:30} ({result['config_file']})")
    
    print("\n❌ Non-functional Servers:")
    print("-" * 40)
    for result in results:
        if not result['functional']:
            print(f"  • {result['server']:30} ({result['config_file']})")
            if result['type'] == 'python-module':
                print(f"    Module: {result['module']}")
            elif result['type'] in ['npx-package', 'uvx-package']:
                print(f"    Package: {result['package']}")
            else:
                print(f"    Command: {result['command']}")
            print(f"    Error: {result['error']}")
    
    # Save detailed report
    with open('mcp_server_status.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed report saved to: mcp_server_status.json")

if __name__ == "__main__":
    main()