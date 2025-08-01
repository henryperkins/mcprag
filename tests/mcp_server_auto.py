#!/usr/bin/env python3
"""
Auto-indexing wrapper for mcp_server_sota.py
Automatically detects and indexes the current workspace before starting the MCP server
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Add the mcprag directory to path so we can import the existing server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_workspace_info():
    """Get current workspace path and name"""
    workspace = Path.cwd()
    
    # Try to get repo name from git
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=workspace,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout:
            url = result.stdout.strip()
            name = url.split('/')[-1].replace('.git', '')
            return workspace, name
    except:
        pass
    
    # Fall back to directory name
    return workspace, workspace.name

def should_index(workspace_path, workspace_name):
    """Check if workspace needs indexing"""
    # Simple check: look for a marker file that stores last index time
    marker_file = Path.home() / ".mcp" / f"indexed_{workspace_name}.json"
    
    if not marker_file.exists():
        return True
    
    try:
        with open(marker_file, 'r') as f:
            data = json.load(f)
            last_indexed = datetime.fromisoformat(data['timestamp'])
            
        # Check if any code files were modified since last index
        for ext in ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx']:
            for file in workspace_path.rglob(ext):
                if file.stat().st_mtime > last_indexed.timestamp():
                    return True
                    
    except:
        return True
    
    return False

def index_workspace(workspace_path, workspace_name):
    """Run smart_indexer on the workspace"""
    print(f"🔍 Indexing workspace: {workspace_name} at {workspace_path}")
    
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "smart_indexer.py"),
        "--repo-path", str(workspace_path),
        "--repo-name", workspace_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Workspace indexed successfully")
        
        # Save marker file
        marker_file = Path.home() / ".mcp" / f"indexed_{workspace_name}.json"
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(marker_file, 'w') as f:
            json.dump({
                'workspace': str(workspace_path),
                'name': workspace_name,
                'timestamp': datetime.now().isoformat()
            }, f)
        
        return True
    else:
        print(f"❌ Indexing failed: {result.stderr}")
        return False

def main():
    """Main entry point"""
    # Get workspace info
    workspace_path, workspace_name = get_workspace_info()
    
    print(f"🚀 Starting MCP Server with Auto-Indexing")
    print(f"📂 Workspace: {workspace_name} ({workspace_path})")
    
    # Check if indexing is needed
    if should_index(workspace_path, workspace_name):
        index_workspace(workspace_path, workspace_name)
    else:
        print("✅ Workspace already indexed and up to date")
    
    # Now run the original MCP server with command line args
    print("\n🔧 Starting MCP server...")
    print(f"💡 Searches will default to repository: {workspace_name}")
    print("   (use repository='*' to search all repositories)\n")
    
    # Run the original server as a subprocess so we don't need to modify it
    mcp_server_path = os.path.join(os.path.dirname(__file__), "mcp_server_sota.py")
    
    # Pass through any command line arguments
    cmd = [sys.executable, mcp_server_path] + sys.argv[1:]
    
    # Run the MCP server
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 MCP server stopped")

if __name__ == "__main__":
    main()