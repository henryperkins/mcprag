#!/usr/bin/env python3
"""Test MCP integration with Claude Code SDK."""

import asyncio
import json
import os
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

async def test_mcp_search():
    """Test the MCP Azure Code Search integration."""

    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()

    # Create MCP config with environment variables resolved
    mcp_config = {
        "mcpServers": {
            "azure-code-search": {
                "command": "python",
                "args": ["-m", "mcprag"],
                "cwd": str(Path(__file__).parent),
                "env": {
                    "ACS_ENDPOINT": os.getenv("ACS_ENDPOINT"),
                    "ACS_ADMIN_KEY": os.getenv("ACS_ADMIN_KEY"),
                    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "AZURE_OPENAI_KEY": os.getenv("AZURE_OPENAI_KEY"),
                    "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT", "text-embedding-ada-002")
                }
            }
        }
    }

    # Write resolved config to temp file
    config_path = Path("/tmp/test-mcp-config.json")
    config_path.write_text(json.dumps(mcp_config, indent=2))

    # Test queries
    test_prompts = [
        "Use the azure-code-search MCP server to find authentication functions in the codebase",
        "Search for database connection code using the MCP tools",
        "Find all API endpoint handlers"
    ]

    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"Testing: {prompt}")
        print('='*60)

        try:
            messages = []
            options = ClaudeCodeOptions(
                max_turns=3,
                mcp_config=str(config_path),
                allowed_tools=[
                    "mcp__azure-code-search__search_code",
                    "mcp__azure-code-search__get_file_context",
                    "mcp__azure-code-search__search_similar_code"
                ],
                output_format="stream-json"
            )

            async for message in query(prompt=prompt, options=options):
                messages.append(message)
                if message.get("type") == "assistant":
                    print(f"Assistant: {message.get('message', {}).get('content', '')[:200]}...")
                elif message.get("type") == "result":
                    print(f"Result: Success={not message.get('is_error')}, Turns={message.get('num_turns')}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_search())
