#!/usr/bin/env python3
"""
MCP-compliant server for Azure Cognitive Search code search.
This implements the Model Context Protocol specification for Claude integration.
"""

import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv()

class MCPServer:
    def __init__(self):
        self.search_client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT"),
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
        )
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests."""
        method = request.get("method")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "azure-code-search",
                        "version": "1.0.0"
                    }
                }
            }
            
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", 
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "search_code",
                            "description": "Search for code snippets using Azure Cognitive Search with semantic understanding",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Natural language query to search for code"
                                    },
                                    "intent": {
                                        "type": "string",
                                        "enum": ["implement", "debug", "understand", "refactor"],
                                        "description": "Search intent to optimize results"
                                    },
                                    "language": {
                                        "type": "string",
                                        "description": "Programming language filter"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    ]
                }
            }
            
        elif method == "tools/call":
            return await self.handle_tool_call(request)
            
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def handle_tool_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call requests."""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "search_code":
            try:
                results = await self.search_code_enhanced(
                    query=arguments.get("query", ""),
                    intent=arguments.get("intent"),
                    language=arguments.get("language")
                )
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": self.format_search_results(results)
                            }
                        ]
                    }
                }
                
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"Search error: {str(e)}"
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

    async def search_code_enhanced(self, query: str, intent: Optional[str] = None, language: Optional[str] = None) -> List[Dict]:
        """Enhanced code search with intent awareness."""
        # Enhance query based on intent
        enhanced_query = self._enhance_query_by_intent(query, intent)
        
        # Build search parameters
        search_params = {
            "search_text": enhanced_query,
            "query_type": "semantic",
            "semantic_configuration_name": "mcp-semantic",
            "vector_queries": [
                {
                    "kind": "text",
                    "text": enhanced_query,
                    "fields": "semantic_context",
                    "k": 10,
                    "threshold": {"kind": "vectorSimilarity", "value": 0.7}
                }
            ],
            "top": 5,
            "select": [
                "file_path", "function_signature", "code_chunk", 
                "semantic_context", "imports_used", "calls_functions",
                "chunk_type", "line_range"
            ]
        }
        
        # Add language filter if specified
        if language:
            search_params["filter"] = f"language eq '{language}'"
        
        results = self.search_client.search(**search_params)
        
        # Process results
        processed_results = []
        for result in results:
            processed_results.append({
                "file": result["file_path"],
                "function": result["function_signature"],
                "code": result["code_chunk"],
                "relevance": result.get("@search.score", 0),
                "context": result["semantic_context"],
                "related_functions": result.get("calls_functions", []),
                "imports": result.get("imports_used", []),
                "line_range": result["line_range"],
                "type": result["chunk_type"]
            })
        
        return processed_results

    def _enhance_query_by_intent(self, query: str, intent: Optional[str]) -> str:
        """Enhance query based on search intent."""
        if not intent:
            return query
        
        intent_prefixes = {
            "implement": f"implementation example code for {query}",
            "debug": f"error handling exception catching for {query}",
            "understand": f"explanation documentation of {query}",
            "refactor": f"refactoring patterns best practices for {query}"
        }
        
        return intent_prefixes.get(intent, query)

    def format_search_results(self, results: List[Dict]) -> str:
        """Format search results for Claude."""
        if not results:
            return "No relevant code found."
        
        formatted = "# Code Search Results\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"## Result {i}: {result['function']}\n"
            formatted += f"**File:** `{result['file']}`\n"
            formatted += f"**Relevance:** {result['relevance']:.2f}\n"
            formatted += f"**Context:** {result['context']}\n\n"
            formatted += "```python\n" if result['file'].endswith('.py') else "```javascript\n"
            formatted += result['code']
            formatted += "\n```\n\n"
            
            if result['imports']:
                formatted += f"**Imports:** {', '.join(result['imports'])}\n"
            if result['related_functions']:
                formatted += f"**Calls:** {', '.join(result['related_functions'])}\n"
            formatted += "\n---\n\n"
        
        return formatted

async def main():
    """Main MCP server loop."""
    server = MCPServer()
    
    # Read from stdin and write to stdout (MCP protocol)
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
