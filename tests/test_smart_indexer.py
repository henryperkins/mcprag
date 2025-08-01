#!/usr/bin/env python3
"""
Test smart indexer with a few files
"""

import subprocess
import sys

# Index the enhanced_rag module files
files = [
    "enhanced_rag/azure_integration/enhanced_index_builder.py",
    "enhanced_rag/azure_integration/indexer_integration.py", 
    "enhanced_rag/core/config.py",
    "smart_indexer.py",
    "mcp_server_sota.py"
]

print("Indexing files with smart_indexer...")
cmd = ["python", "smart_indexer.py", "--files"] + files
result = subprocess.run(cmd, capture_output=True, text=True)

print("\nSTDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

print(f"\nReturn code: {result.returncode}")