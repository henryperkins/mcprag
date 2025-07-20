#!/usr/bin/env python3
"""Check what repositories are currently indexed."""

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv()

# Create search client
client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

# Search for all documents and get unique repo names
results = client.search(
    search_text="*",
    select=["repo_name"],
    top=1000
)

repo_names = set()
count = 0
for result in results:
    repo_name = result.get("repo_name")
    if repo_name:
        repo_names.add(repo_name)
    count += 1

print(f"Total documents: {count}")
print(f"Unique repositories: {sorted(repo_names)}")