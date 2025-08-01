#!/usr/bin/env python3
"""
Index multiple repositories in batch
"""

import subprocess
import sys
from pathlib import Path

# Define your repositories here
REPOSITORIES = [
    {
        "path": "~/projects/frontend",
        "name": "frontend-app"
    },
    {
        "path": "~/projects/backend", 
        "name": "backend-api"
    },
    {
        "path": "~/projects/shared-libs",
        "name": "shared-libraries"
    }
]

def index_repository(repo_path: str, repo_name: str):
    """Index a single repository"""
    # Expand home directory
    full_path = Path(repo_path).expanduser()
    
    if not full_path.exists():
        print(f"❌ Repository path not found: {full_path}")
        return False
        
    print(f"\n{'='*60}")
    print(f"Indexing: {repo_name}")
    print(f"Path: {full_path}")
    print('-'*60)
    
    cmd = [
        sys.executable,
        "smart_indexer.py",
        "--repo-path", str(full_path),
        "--repo-name", repo_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Successfully indexed {repo_name}")
        print(result.stdout)
        return True
    else:
        print(f"❌ Failed to index {repo_name}")
        print(result.stderr)
        return False

def main():
    """Index all repositories"""
    successful = 0
    failed = 0
    
    for repo in REPOSITORIES:
        if index_repository(repo["path"], repo["name"]):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: {successful} successful, {failed} failed")
    
if __name__ == "__main__":
    main()