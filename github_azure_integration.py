#!/usr/bin/env python3
"""
Enhanced GitHub API + Azure Cognitive Search Integration
Supports remote repository indexing, webhook handling, and multi-repo management.
"""

import os
import json
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import base64

load_dotenv()

class GitHubAzureIntegrator:
    """Integrates GitHub API with Azure Cognitive Search for remote repository indexing."""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.azure_client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT"),
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
        )
        self.github_api_base = "https://api.github.com"
        
    def get_github_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MCPRag-Indexer/1.0"
        }
    
    def get_repository_info(self, owner: str, repo: str) -> Dict:
        """Get repository information from GitHub API."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.get_github_headers())
        response.raise_for_status()
        return response.json()
    
    def get_repository_contents(self, owner: str, repo: str, path: str = "") -> List[Dict]:
        """Get repository contents from GitHub API."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=self.get_github_headers())
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, owner: str, repo: str, file_path: str) -> str:
        """Get file content from GitHub API."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}/contents/{file_path}"
        response = requests.get(url, headers=self.get_github_headers())
        response.raise_for_status()
        
        file_data = response.json()
        if file_data.get("encoding") == "base64":
            content = base64.b64decode(file_data["content"]).decode('utf-8', errors='ignore')
            return content
        return ""
    
    def get_changed_files_from_push(self, owner: str, repo: str, before_sha: str, after_sha: str) -> List[str]:
        """Get list of changed files between two commits."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}/compare/{before_sha}...{after_sha}"
        response = requests.get(url, headers=self.get_github_headers())
        response.raise_for_status()
        
        comparison = response.json()
        changed_files = []
        
        for file in comparison.get("files", []):
            filename = file["filename"]
            if any(filename.endswith(ext) for ext in ['.py', '.js', '.ts']):
                changed_files.append(filename)
        
        return changed_files
    
    def get_pull_request_files(self, owner: str, repo: str, pr_number: int) -> List[str]:
        """Get list of files changed in a pull request."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.get_github_headers())
        response.raise_for_status()
        
        files = response.json()
        changed_files = []
        
        for file in files:
            filename = file["filename"]
            if any(filename.endswith(ext) for ext in ['.py', '.js', '.ts']):
                changed_files.append(filename)
        
        return changed_files
    
    def index_remote_repository(self, owner: str, repo: str, branch: str = "main") -> None:
        """Index an entire remote repository."""
        print(f"🔄 Indexing remote repository {owner}/{repo}...")
        
        # Get repository info
        repo_info = self.get_repository_info(owner, repo)
        repo_name = f"{owner}/{repo}"
        
        # Recursively get all code files
        code_files = self._get_all_code_files(owner, repo, "", branch)
        
        documents = []
        for file_path in code_files:
            try:
                content = self.get_file_content(owner, repo, file_path)
                chunks = self._parse_file_content(content, file_path)
                
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{repo_name}:{file_path}:{i}".encode()).hexdigest()
                    
                    documents.append({
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": file_path,
                        "language": self._detect_language(file_path),
                        "github_url": f"https://github.com/{owner}/{repo}/blob/{branch}/{file_path}",
                        "last_modified": repo_info.get("updated_at"),
                        **chunk
                    })
                    
                    if len(documents) >= 50:
                        self.azure_client.merge_or_upload_documents(documents)
                        documents = []
                        
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
        
        if documents:
            self.azure_client.merge_or_upload_documents(documents)
        
        print(f"✅ Indexed {len(code_files)} files from {repo_name}")
    
    def index_changed_files_remote(self, owner: str, repo: str, file_paths: List[str], branch: str = "main") -> None:
        """Index only specific changed files from a remote repository."""
        print(f"🔄 Indexing {len(file_paths)} changed files from {owner}/{repo}...")
        
        repo_name = f"{owner}/{repo}"
        documents = []
        
        for file_path in file_paths:
            try:
                content = self.get_file_content(owner, repo, file_path)
                chunks = self._parse_file_content(content, file_path)
                
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{repo_name}:{file_path}:{i}".encode()).hexdigest()
                    
                    documents.append({
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": file_path,
                        "language": self._detect_language(file_path),
                        "github_url": f"https://github.com/{owner}/{repo}/blob/{branch}/{file_path}",
                        **chunk
                    })
                    
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
        
        if documents:
            self.azure_client.merge_or_upload_documents(documents)
            print(f"✅ Re-indexed {len(documents)} documents from changed files")
    
    def _get_all_code_files(self, owner: str, repo: str, path: str, branch: str) -> List[str]:
        """Recursively get all code files from a repository."""
        code_files = []
        
        try:
            contents = self.get_repository_contents(owner, repo, path)
            
            for item in contents:
                if item["type"] == "file":
                    if any(item["name"].endswith(ext) for ext in ['.py', '.js', '.ts']):
                        code_files.append(item["path"])
                elif item["type"] == "dir":
                    # Recursively get files from subdirectories
                    code_files.extend(self._get_all_code_files(owner, repo, item["path"], branch))
                    
        except Exception as e:
            print(f"❌ Error accessing {path}: {e}")
        
        return code_files
    
    def _parse_file_content(self, content: str, file_path: str) -> List[Dict]:
        """Parse file content using appropriate parser."""
        # Import here to avoid circular imports
        from smart_indexer import CodeChunker
        
        chunker = CodeChunker()
        
        if file_path.endswith('.py'):
            return chunker.chunk_python_file(content, file_path)
        elif file_path.endswith(('.js', '.ts')):
            return chunker.chunk_js_ts_file(content, file_path)
        else:
            # Fallback for unsupported files
            return [{
                "code_chunk": content[:8000],
                "semantic_context": f"Code from {file_path}",
                "function_signature": "",
                "imports_used": [],
                "calls_functions": [],
                "chunk_type": "file",
                "line_range": "1-"
            }]
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        if file_path.endswith('.py'):
            return "python"
        elif file_path.endswith('.js'):
            return "javascript"
        elif file_path.endswith('.ts'):
            return "typescript"
        else:
            return "unknown"

def main():
    """CLI interface for GitHub + Azure integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub API + Azure Cognitive Search Integration")
    parser.add_argument("--owner", required=True, help="GitHub repository owner")
    parser.add_argument("--repo", required=True, help="GitHub repository name")
    parser.add_argument("--branch", default="main", help="Branch to index")
    parser.add_argument("--files", nargs="*", help="Specific files to index")
    parser.add_argument("--pr", type=int, help="Pull request number to index")
    
    args = parser.parse_args()
    
    integrator = GitHubAzureIntegrator()
    
    if args.pr:
        # Index files from a pull request
        files = integrator.get_pull_request_files(args.owner, args.repo, args.pr)
        integrator.index_changed_files_remote(args.owner, args.repo, files, args.branch)
    elif args.files:
        # Index specific files
        integrator.index_changed_files_remote(args.owner, args.repo, args.files, args.branch)
    else:
        # Index entire repository
        integrator.index_remote_repository(args.owner, args.repo, args.branch)

if __name__ == "__main__":
    main()
