#!/usr/bin/env python3
"""
MCP Server with automatic workspace indexing
Detects the current directory and indexes it on startup
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
import hashlib
import json
from typing import Optional, Dict, Any

# Add the mcprag directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server_sota import EnhancedMCPServer, SearchCodeParams, SearchResult
from smart_indexer import SmartIndexer

class AutoIndexingMCPServer(EnhancedMCPServer):
    """MCP Server that automatically indexes the current workspace"""
    
    def __init__(self, auto_index: bool = True):
        super().__init__()
        self.workspace_path = self._detect_workspace()
        self.workspace_name = self._get_workspace_name()
        self.index_metadata_file = Path.home() / ".mcp" / "indexed_workspaces.json"
        
        if auto_index and self.workspace_path:
            self._ensure_workspace_indexed()
    
    def _detect_workspace(self) -> Optional[Path]:
        """Detect the current workspace from environment or cwd"""
        # Check common environment variables that editors/IDEs set
        workspace_env_vars = [
            "CLAUDE_CODE_WORKSPACE",  # If Claude Code sets this
            "PWD",                    # Current working directory
            "PROJECT_ROOT",           # Common project root var
            "WORKSPACE_FOLDER",       # VS Code style
        ]
        
        for var in workspace_env_vars:
            if var in os.environ:
                path = Path(os.environ[var])
                if path.exists() and path.is_dir():
                    return path
        
        # Fall back to current working directory
        return Path.cwd()
    
    def _get_workspace_name(self) -> str:
        """Get a meaningful name for the workspace"""
        if not self.workspace_path:
            return "unknown"
        
        # Check if it's a git repository
        git_dir = self.workspace_path / ".git"
        if git_dir.exists():
            # Try to get remote origin URL
            try:
                result = subprocess.run(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout:
                    url = result.stdout.strip()
                    # Extract repo name from URL
                    name = url.split('/')[-1].replace('.git', '')
                    return name
            except:
                pass
        
        # Fall back to directory name
        return self.workspace_path.name
    
    def _get_workspace_hash(self) -> str:
        """Get a unique hash for the workspace path"""
        return hashlib.md5(str(self.workspace_path).encode()).hexdigest()
    
    def _load_index_metadata(self) -> Dict[str, Any]:
        """Load metadata about indexed workspaces"""
        self.index_metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        if self.index_metadata_file.exists():
            try:
                with open(self.index_metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {}
    
    def _save_index_metadata(self, metadata: Dict[str, Any]):
        """Save metadata about indexed workspaces"""
        self.index_metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.index_metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _should_reindex(self) -> bool:
        """Check if the workspace needs reindexing"""
        metadata = self._load_index_metadata()
        workspace_hash = self._get_workspace_hash()
        
        if workspace_hash not in metadata:
            return True
        
        workspace_info = metadata[workspace_hash]
        last_indexed = datetime.fromisoformat(workspace_info.get('last_indexed', '2000-01-01'))
        
        # Check if any files have been modified since last index
        try:
            # Get the most recently modified file
            most_recent = max(
                (p.stat().st_mtime for p in self.workspace_path.rglob('*') 
                 if p.is_file() and not any(part.startswith('.') for part in p.parts)),
                default=0
            )
            
            if most_recent > last_indexed.timestamp():
                return True
                
        except Exception as e:
            print(f"Error checking file modifications: {e}")
            return True
        
        return False
    
    def _ensure_workspace_indexed(self):
        """Ensure the current workspace is indexed"""
        if not self.workspace_path:
            return
        
        print(f"🔍 Checking workspace: {self.workspace_path}")
        print(f"📁 Repository name: {self.workspace_name}")
        
        if not self._should_reindex():
            print("✅ Workspace is up to date")
            return
        
        print("📝 Indexing workspace...")
        
        try:
            # Run the smart indexer
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "smart_indexer.py"),
                "--repo-path", str(self.workspace_path),
                "--repo-name", self.workspace_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Workspace indexed successfully")
                
                # Update metadata
                metadata = self._load_index_metadata()
                metadata[self._get_workspace_hash()] = {
                    'path': str(self.workspace_path),
                    'name': self.workspace_name,
                    'last_indexed': datetime.now().isoformat()
                }
                self._save_index_metadata(metadata)
            else:
                print(f"❌ Indexing failed: {result.stderr}")
        
        except Exception as e:
            print(f"❌ Error during indexing: {e}")
    
    async def search_code(self, params: SearchCodeParams) -> list[SearchResult]:
        """Override to add workspace context"""
        # If no repository specified, default to current workspace
        if not params.repository:
            params.repository = self.workspace_name
        
        # Call parent implementation
        return await super().search_code(params)
    
    async def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the current workspace"""
        return {
            "path": str(self.workspace_path),
            "name": self.workspace_name,
            "indexed": not self._should_reindex(),
            "repository_filter": self.workspace_name
        }


# MCP Server entry point
async def serve():
    """Run the MCP server with auto-indexing"""
    server = AutoIndexingMCPServer(auto_index=True)
    
    # Print workspace info
    info = await server.get_workspace_info()
    print(f"\n🚀 MCP Server started")
    print(f"📂 Workspace: {info['name']} ({info['path']})")
    print(f"🔍 Search filter: repository={info['repository_filter']}")
    print(f"✨ Ready for queries!\n")
    
    # Keep the server running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Check if we should run in standalone mode or integrate with existing MCP
    if "--standalone" in sys.argv:
        asyncio.run(serve())
    else:
        # Export the server class for MCP integration
        print("AutoIndexingMCPServer ready for MCP integration")