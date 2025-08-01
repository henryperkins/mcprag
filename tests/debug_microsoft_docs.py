"""Debug script to test Microsoft Docs MCP server directly"""

import asyncio
import logging
import traceback
from microsoft_docs_mcp_client import MicrosoftDocsMCPClient

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def test_microsoft_docs():
    """Test Microsoft Docs MCP with debug logging"""
    print("Testing Microsoft Docs MCP Server...")
    print("=" * 60)

    try:
        async with MicrosoftDocsMCPClient() as client:
            print("\nClient initialized successfully")

            # Test search
            print("\n[TEST] Searching for 'Azure Cognitive Search'")
            results = await client.search_docs("Azure Cognitive Search")

            print(f"\nResults: {len(results)}")
            for i, result in enumerate(results[:3]):
                print(f"\n{i+1}. {result.get('title', 'No title')}")
                print(f"   {result.get('content', 'No content')[:200]}...")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"\nError: {exc}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_microsoft_docs())
