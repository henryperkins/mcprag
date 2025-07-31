#!/usr/bin/env python3
"""
Apply workspace awareness to mcp_server_sota.py
This patch makes the server default to the current workspace when no repository is specified
"""

import os

# Read the original file
with open('mcp_server_sota.py', 'r') as f:
    content = f.read()

# Add workspace detection to the _resolve_repository method
patch = '''
    def _resolve_repository(self, repo: Optional[str]) -> Optional[str]:
        """Resolve repository with caching"""
        if repo == "*" or repo == "all":
            return None

        if repo:
            return repo

        # Check for workspace environment variable first
        workspace_name = os.getenv("MCP_WORKSPACE_NAME")
        if workspace_name:
            return workspace_name

        # Detect current repository with caching
'''

# Replace the method
content = content.replace(
    '''    def _resolve_repository(self, repo: Optional[str]) -> Optional[str]:
        """Resolve repository with caching"""
        if repo == "*" or repo == "all":
            return None

        if repo:
            return repo

        # Detect current repository with caching''',
    patch
)

# Write the patched version
with open('mcp_server_sota_workspace.py', 'w') as f:
    f.write(content)

print("✅ Created workspace-aware version: mcp_server_sota_workspace.py")