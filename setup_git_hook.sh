#!/bin/bash
# Setup git post-commit hook to automatically index changed files

REPO_PATH=${1:-.}
HOOK_PATH="$REPO_PATH/.git/hooks/post-commit"

cat > "$HOOK_PATH" << 'EOF'
#!/bin/bash
# Auto-index changed files after commit

echo "Indexing changed files for search..."
python /home/azureuser/mcprag/auto_index_on_change.py
EOF

chmod +x "$HOOK_PATH"
echo "✅ Git hook installed at: $HOOK_PATH"
echo "Changed files will be automatically indexed after each commit"