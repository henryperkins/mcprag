#!/bin/bash
# Auto-indexing script for Claude Code startup
# This script checks if the current directory needs indexing and indexes it if necessary

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in a git repository or a regular directory
CURRENT_DIR=$(pwd)
REPO_NAME=$(basename "$CURRENT_DIR")

# Check if it's a git repo and get the remote name if available
if [ -d ".git" ]; then
    REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null)
    if [ ! -z "$REMOTE_URL" ]; then
        REPO_NAME=$(basename "$REMOTE_URL" .git)
    fi
fi

echo "🔍 Auto-indexing check for: $CURRENT_DIR"
echo "📁 Repository name: $REPO_NAME"

# Check if Python and required environment variables are set
if [ -z "$ACS_ENDPOINT" ] || [ -z "$ACS_ADMIN_KEY" ]; then
    echo "⚠️  Azure Search credentials not found in environment"
    echo "   Please set ACS_ENDPOINT and ACS_ADMIN_KEY"
    exit 0
fi

# Create a marker file to track when we last indexed
MARKER_DIR="$HOME/.mcp/indexed_dirs"
mkdir -p "$MARKER_DIR"
MARKER_FILE="$MARKER_DIR/$(echo "$CURRENT_DIR" | md5sum | cut -d' ' -f1)"

# Check if we need to index
SHOULD_INDEX=0

if [ ! -f "$MARKER_FILE" ]; then
    echo "📝 First time indexing this directory"
    SHOULD_INDEX=1
else
    # Check if any files have been modified since last index
    LAST_INDEX=$(cat "$MARKER_FILE")
    NEWEST_FILE=$(find "$CURRENT_DIR" -type f -name "*.py" -o -name "*.js" -o -name "*.ts" 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
    
    if [ ! -z "$NEWEST_FILE" ] && [ "$NEWEST_FILE" -nt "$MARKER_FILE" ]; then
        echo "📝 Files have been modified since last index"
        SHOULD_INDEX=1
    fi
fi

if [ $SHOULD_INDEX -eq 1 ]; then
    echo "🚀 Starting indexing..."
    
    # Run the smart indexer
    python "$SCRIPT_DIR/smart_indexer.py" --repo-path "$CURRENT_DIR" --repo-name "$REPO_NAME"
    
    if [ $? -eq 0 ]; then
        echo "✅ Indexing completed successfully"
        # Update the marker file
        date > "$MARKER_FILE"
    else
        echo "❌ Indexing failed"
    fi
else
    echo "✅ Directory is already indexed and up to date"
fi

echo ""