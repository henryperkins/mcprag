#!/usr/bin/env python3
"""
Index changed files via the Azure integration automation layer.

Usage:
  python scripts/index_changed_files.py --files "path1 path2 ..." --index-name codebase-mcp-sota
"""

import argparse
import os
import sys
from typing import List

from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
from enhanced_rag.azure_integration.automation import CLIAutomation
from enhanced_rag.azure_integration.embedding_provider import AzureOpenAIEmbeddingProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True, help="Space-separated list of files to index")
    parser.add_argument("--index-name", default=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"))
    parser.add_argument("--repo-name", default=None)
    args = parser.parse_args()

    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    if not endpoint or not api_key:
        print("Missing ACS_ENDPOINT or ACS_ADMIN_KEY", file=sys.stderr)
        return 2

    # Resolve repository name
    repo_name = args.repo_name or os.getenv("GITHUB_REPOSITORY", "local-repo").split("/")[-1]

    # Normalize files into a list; GitHub action passes space-separated
    files: List[str] = [f for f in args.files.split() if f]
    if not files:
        print("No files to index; exiting.")
        return 0

    # Initialize automation components
    rest_client = AzureSearchClient(endpoint=endpoint, api_key=api_key)
    ops = SearchOperations(rest_client)
    embedder = AzureOpenAIEmbeddingProvider()
    cli = CLIAutomation(operations=ops, embedding_provider=embedder)

    # Run indexing
    import asyncio

    async def run():
        result = await cli.index_changed_files(
            file_paths=files,
            repo_name=repo_name,
            index_name=args.index_name,
            generate_embeddings=True,
        )
        print(result)

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

