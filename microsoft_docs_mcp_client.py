"""Microsoft Docs MCP Client - Integrates with Microsoft Learn documentation search"""

import aiohttp
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MicrosoftDocsMCPClient:
    """Client for Microsoft Docs MCP Server"""
    
    def __init__(self, base_url: str = "https://learn.microsoft.com/api/mcp"):
        self.base_url = base_url
        self.session = None
        self.tools = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def initialize(self):
        """Initialize connection and get available tools"""
        try:
            # Initialize the MCP connection
            response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "mcp-rag-client",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            })
            
            # List available tools - required by MCP protocol
            tools_response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2
            })
            
            self.tools = tools_response.get("result", {}).get("tools", [])
            logger.info(f"Available Microsoft Docs tools: {[t['name'] for t in self.tools]}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Microsoft Docs MCP: {e}")
            raise
            
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        logger.debug(f"Sending request to {self.base_url}: {json.dumps(request, indent=2)}")
        
        try:
            async with self.session.post(self.base_url, json=request, headers=headers) as response:
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                text = await response.text()
                logger.debug(f"Response text: {text[:500]}...")
                
                if response.status != 200:
                    raise Exception(f"MCP request failed: {response.status} - {text}")
                    
                # Handle different content types
                content_type = response.headers.get('Content-Type', '')
                
                if 'text/event-stream' in content_type:
                    # Handle Server-Sent Events format
                    # Parse SSE format to extract JSON
                    for line in text.split('\n'):
                        if line.startswith('data: '):
                            data = line[6:].strip()
                            if data:
                                try:
                                    parsed = json.loads(data)
                                    logger.debug(f"Parsed SSE response: {json.dumps(parsed, indent=2)}")
                                    return parsed
                                except json.JSONDecodeError as e:
                                    logger.debug(f"Failed to parse JSON from SSE line: {e}")
                                    continue
                    raise Exception(f"No valid JSON found in SSE response")
                else:
                    parsed = json.loads(text)
                    logger.debug(f"Parsed JSON response: {json.dumps(parsed, indent=2)}")
                    return parsed
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
            
    async def search_docs(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Microsoft documentation
        
        Args:
            query: Search query
            max_results: Maximum number of results (default 10)
            
        Returns:
            List of search results with content chunks
        """
        try:
            # Call the microsoft_docs_search tool
            # Note: The Microsoft Docs MCP server expects "question" not "query"
            response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "microsoft_docs_search",
                    "arguments": {
                        "question": query
                    }
                },
                "id": 3
            })
            
            result = response.get("result", {})
            
            # Extract content from the response
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Parse the text content for results
                    text_content = content[0].get("text", "")
                    return self._parse_search_results(text_content)
            
            return []
            
        except Exception as e:
            logger.error(f"Microsoft Docs search failed: {e}")
            return []
            
    def _parse_search_results(self, text_content: str) -> List[Dict[str, Any]]:
        """Parse the text response into structured results"""
        results = []
        
        # Check if the response is a JSON array string
        if text_content.strip().startswith('['):
            try:
                # Parse as JSON array
                parsed_results = json.loads(text_content)
                if isinstance(parsed_results, list):
                    for item in parsed_results[:10]:  # Limit to 10 results
                        if isinstance(item, dict):
                            results.append({
                                "title": item.get("title", "No title"),
                                "content": item.get("content", ""),
                                "source": "Microsoft Docs",
                                "url": item.get("contentUrl", "")
                            })
                    return results
            except json.JSONDecodeError:
                logger.debug("Failed to parse as JSON, falling back to text parsing")
        
        # Fallback: parse as plain text
        sections = text_content.split("\n\n")
        
        for section in sections:
            if section.strip():
                # Extract title and content
                lines = section.strip().split("\n")
                if lines:
                    # Assume first line is title/URL
                    title = lines[0].strip()
                    content = "\n".join(lines[1:]) if len(lines) > 1 else ""
                    
                    results.append({
                        "title": title,
                        "content": content,
                        "source": "Microsoft Docs"
                    })
                    
        return results[:10]  # Limit to 10 results
        
    async def search_with_context(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhanced search with additional context
        
        Args:
            query: Search query
            context: Additional context (language, framework, etc.)
            
        Returns:
            Structured response with results and metadata
        """
        # Enhance query based on context
        enhanced_query = query
        if context:
            if context.get("language"):
                enhanced_query = f"{query} {context['language']}"
            if context.get("framework"):
                enhanced_query = f"{enhanced_query} {context['framework']}"
                
        results = await self.search_docs(enhanced_query)
        
        return {
            "query": query,
            "enhanced_query": enhanced_query,
            "results": results,
            "result_count": len(results),
            "source": "Microsoft Learn Documentation"
        }


# Example usage
async def example_usage():
    async with MicrosoftDocsMCPClient() as client:
        # Search for Azure Cognitive Search documentation
        results = await client.search_docs("Azure Cognitive Search vector search")
        
        print(f"Found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"\n{i+1}. {result['title']}")
            print(f"   {result['content'][:200]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())