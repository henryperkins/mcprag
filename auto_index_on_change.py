#!/usr/bin/env python3
"""
Automatically index files when they change
Can be used with file watchers or git hooks
"""

import subprocess
import sys
import os
from pathlib import Path

def get_changed_files():
    """Get list of changed files from git"""
    # Get files changed in the last commit
    cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    return []

def get_repo_info():
    """Get current repository information"""
    # Get repo name from git remote or directory name
    cmd = ["git", "config", "--get", "remote.origin.url"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout:
        # Extract repo name from URL
        url = result.stdout.strip()
        repo_name = url.split('/')[-1].replace('.git', '')
    else:
        # Use directory name as fallback
        repo_name = Path.cwd().name
    
    return repo_name

def index_changed_files():
    """Index only changed files"""
    files = get_changed_files()
    
    if not files:
        print("No changed files to index")
        return
    
    # Filter for supported file types
    supported_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cs', '.cpp', '.c', '.h'}
    files_to_index = [f for f in files if Path(f).suffix in supported_extensions]
    
    if not files_to_index:
        print("No supported files to index")
        return
    
    repo_name = get_repo_info()
    print(f"Indexing {len(files_to_index)} changed files in {repo_name}")
    
    # Run indexer
    cmd = [sys.executable, "/home/azureuser/mcprag/smart_indexer.py", "--files"] + files_to_index
    subprocess.run(cmd)

if __name__ == "__main__":
    index_changed_files()