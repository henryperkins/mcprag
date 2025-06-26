#!/usr/bin/env python3
"""
GitHub API + Azure Cognitive Search Integration
Enables remote repository indexing without local clones
"""
import os
import base64
import argparse
import hashlib
from typing import List, Dict, Optional
import requests
from pathlib import Path
from smart_indexer import CodeChunker
from dotenv import load_dotenv

load_dotenv()

class GitHubAzureIntegrator:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        
        # Only add Authorization header if token is present
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        self.chunker = CodeChunker()

    def get_repository_files(self, owner: str, repo: str, path: str = "", ref: str = "main") -> List[Dict]:
        """Get all code files from a GitHub repository."""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        files = []
        items = response.json()

        for item in items:
            if item["type"] == "file":
                # Check if it's a code file we want to index
                if any(item["name"].endswith(ext) for ext in [".py", ".js", ".ts"]):
                    files.append(item)
            elif item["type"] == "dir":
                # Recursively get files from subdirectories
                subfiles = self.get_repository_files(owner, repo, item["path"], ref)
                files.extend(subfiles)

        return files

    def get_file_content(self, owner: str, repo: str, file_path: str) -> str:
        """Get the content of a specific file from GitHub."""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        file_data = response.json()
        # GitHub API returns content as base64
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        return content

    def get_changed_files_from_push(self, owner: str, repo: str, before_sha: str, after_sha: str) -> List[str]:
        """Get list of changed files from a push event."""
        url = f"https://api.github.com/repos/{owner}/{repo}/compare/{before_sha}...{after_sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        compare_data = response.json()
        changed_files = []

        for file in compare_data.get("files", []):
            if file["status"] != "removed" and any(file["filename"].endswith(ext) for ext in [".py", ".js", ".ts"]):
                changed_files.append(file["filename"])

        return changed_files

    def get_pull_request_files(self, owner: str, repo: str, pr_number: int) -> List[str]:
        """Get list of files changed in a pull request."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        files = []
        for file in response.json():
            if file["status"] != "removed" and any(file["filename"].endswith(ext) for ext in [".py", ".js", ".ts"]):
                files.append(file["filename"])

        return files

    def index_remote_repository(self, owner: str, repo: str, ref: str = "main"):
        """Index an entire remote repository."""
        print(f"🔄 Indexing remote repository: {owner}/{repo} (ref: {ref})")

        # Get all code files
        files = self.get_repository_files(owner, repo, ref=ref)
        print(f"📁 Found {len(files)} code files to index")

        documents = []

        for file_info in files:
            try:
                # Get file content
                content = self.get_file_content(owner, repo, file_info["path"])

                # Determine language
                if file_info["name"].endswith(".py"):
                    chunks = self.chunker.chunk_python_file(content, file_info["path"])
                    language = "python"
                elif file_info["name"].endswith((".js", ".ts")):
                    chunks = self.chunker.chunk_js_ts_file(content, file_info["path"])
                    language = "javascript" if file_info["name"].endswith(".js") else "typescript"
                else:
                    continue

                # Create documents for each chunk
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{owner}/{repo}:{file_info['path']}:{i}".encode()).hexdigest()

                    doc = {
                        "id": doc_id,
                        "repo_name": f"{owner}/{repo}",
                        "file_path": file_info["path"],
                        "language": language,
                        "github_url": file_info["html_url"],
                        **chunk
                    }

                    # Add vector embedding if available
                    if self.chunker.embedder:
                        embedding = self.chunker.embedder.generate_code_embedding(
                            chunk["code_chunk"],
                            chunk["semantic_context"]
                        )
                        if embedding:
                            doc["code_vector"] = embedding

                    documents.append(doc)

                    # Upload in batches
                    if len(documents) >= 50:
                        self.chunker.client.merge_or_upload_documents(documents)
                        print(f"✅ Indexed {len(documents)} chunks")
                        documents = []

            except Exception as e:
                print(f"❌ Error indexing {file_info['path']}: {e}")

        # Upload remaining documents
        if documents:
            self.chunker.client.merge_or_upload_documents(documents)
            print(f"✅ Indexed final {len(documents)} chunks")

        print(f"🎉 Successfully indexed {owner}/{repo}")

    def index_changed_files_remote(self, owner: str, repo: str, file_paths: List[str]):
        """Index specific changed files from a remote repository."""
        print(f"🔄 Indexing {len(file_paths)} changed files from {owner}/{repo}")

        documents = []

        for file_path in file_paths:
            try:
                content = self.get_file_content(owner, repo, file_path)

                # Determine language and chunk
                if file_path.endswith(".py"):
                    chunks = self.chunker.chunk_python_file(content, file_path)
                    language = "python"
                elif file_path.endswith((".js", ".ts")):
                    chunks = self.chunker.chunk_js_ts_file(content, file_path)
                    language = "javascript" if file_path.endswith(".js") else "typescript"
                else:
                    continue

                # Create documents
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{owner}/{repo}:{file_path}:{i}".encode()).hexdigest()

                    doc = {
                        "id": doc_id,
                        "repo_name": f"{owner}/{repo}",
                        "file_path": file_path,
                        "language": language,
                        "github_url": f"https://github.com/{owner}/{repo}/blob/main/{file_path}",
                        **chunk
                    }

                    # Add vector embedding if available
                    if self.chunker.embedder:
                        embedding = self.chunker.embedder.generate_code_embedding(
                            chunk["code_chunk"],
                            chunk["semantic_context"]
                        )
                        if embedding:
                            doc["code_vector"] = embedding

                    documents.append(doc)

            except Exception as e:
                print(f"❌ Error indexing {file_path}: {e}")

        if documents:
            self.chunker.client.merge_or_upload_documents(documents)
            print(f"✅ Indexed {len(documents)} chunks from changed files")

def main():
    parser = argparse.ArgumentParser(description="Index GitHub repositories into Azure Cognitive Search")
    parser.add_argument("--owner", required=True, help="Repository owner")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--ref", default="main", help="Git ref (branch/tag/commit)")
    parser.add_argument("--files", nargs="*", help="Specific files to index")
    parser.add_argument("--pr", type=int, help="Pull request number to index")

    args = parser.parse_args()

    integrator = GitHubAzureIntegrator()

    if args.pr:
        # Index pull request files
        files = integrator.get_pull_request_files(args.owner, args.repo, args.pr)
        integrator.index_changed_files_remote(args.owner, args.repo, files)
    elif args.files:
        # Index specific files
        integrator.index_changed_files_remote(args.owner, args.repo, args.files)
    else:
        # Index entire repository
        integrator.index_remote_repository(args.owner, args.repo, args.ref)

if __name__ == "__main__":
    main()
