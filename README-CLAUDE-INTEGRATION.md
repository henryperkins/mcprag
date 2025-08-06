# Claude Code + Azure Code Search MCP Integration

This guide explains how to use the Azure Code Search MCP server with Claude Code.

## Prerequisites

1. Ensure the MCP server is properly set up:
   ```bash
   cd /home/azureuser/mcprag
   source .venv/bin/activate

   # Copy and configure .env file
   cp .env.example .env
   # Edit .env with your Azure credentials

   # Index your codebase
   python create_index.py
   python smart_indexer.py --repo-path /path/to/your/code --repo-name myproject
   ```

2. Install Claude Code CLI (if not already installed):
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

3. Set up Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```

## Usage Methods

### Method 1: Interactive Session with MCP

Start Claude Code with the MCP server available:

```bash
# Make the script executable
chmod +x /home/azureuser/mcprag/start-claude-with-mcp.sh

# Start interactive session
./start-claude-with-mcp.sh
```

Once in the session, you can ask Claude to search the codebase:
- "Search for authentication functions in the codebase"
- "Find all database models"
- "Show me similar code to the UserController class"

### Method 2: Non-Interactive CLI Usage

Use Claude Code CLI directly with MCP configuration:

```bash
# Single query
claude -p "Use the MCP tools to find all API endpoints" \
  --mcp-config /home/azureuser/mcprag/claude-mcp-config.json \
  --allowedTools "mcp__azure-code-search__search_code"

# With JSON output
claude -p "Search for error handling code" \
  --mcp-config /home/azureuser/mcprag/claude-mcp-config.json \
  --allowedTools "mcp__azure-code-search__search_code" \
  --output-format json
```

### Method 3: Python SDK Integration

```python
import asyncio
from claude_code_sdk import query, ClaudeCodeOptions

async def search_codebase(search_query):
    options = ClaudeCodeOptions(
        max_turns=3,
        mcp_config="/home/azureuser/mcprag/claude-mcp-config.json",
        allowed_tools=["mcp__azure-code-search__search_code"]
    )

    async for message in query(
        prompt=f"Search the codebase for: {search_query}",
        options=options
    ):
        if message.get("type") == "assistant":
            print(message.get("message", {}).get("content", ""))

asyncio.run(search_codebase("authentication logic"))
```

## Available MCP Tools

The Azure Code Search MCP server provides these tools:

1. **mcp__azure-code-search__search_code**
   - Searches for code based on query and intent
   - Supports intents: implement, debug, understand, refactor

2. **mcp__azure-code-search__get_file_context**
   - Retrieves full context for a specific file
   - Useful for understanding complete implementations

3. **mcp__azure-code-search__search_similar_code**
   - Finds code similar to a given snippet
   - Helpful for finding patterns or duplicates

## Troubleshooting

1. **MCP server not starting**: Check that the virtual environment is activated and dependencies are installed
2. **No search results**: Verify that you've indexed code using `smart_indexer.py`
3. **Authentication errors**: Ensure .env file has valid Azure credentials
4. **Tool permission errors**: Make sure to include tools in `--allowedTools` parameter

## Testing the Integration

Run the test script to verify everything is working:

```bash
cd /home/azureuser/mcprag
source .venv/bin/activate
python test-mcp-integration.py
```

This will run several test queries and show you the MCP integration in action.
