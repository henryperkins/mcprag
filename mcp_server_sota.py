# mcp_server_sota.py
import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI

# Add import for vector embeddings
try:
    from vector_embeddings import VectorEmbedder
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False

load_dotenv()

app = FastAPI()

# MCP Protocol Implementation
class MCPServer:
    def __init__(self):
        self.search_client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT"),
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
        )

        # Initialize embedder if available
        self.embedder = None
        if VECTOR_SUPPORT and (os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")):
            try:
                self.embedder = VectorEmbedder()
                print("✅ Vector search enabled in MCP server")
            except Exception as e:
                print(f"Warning: Could not initialize vector embedder: {e}")

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
                            "description": "Search for code snippets using Azure Cognitive Search with semantic understanding and vector search",
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
        """Enhanced search with vector support."""
        # Enhance query based on intent
        enhanced_query = self._enhance_query_by_intent(query, intent)

        # Build search parameters
        search_params = {
            "search_text": enhanced_query,
            "query_type": "semantic",
            "semantic_configuration_name": "mcp-semantic",
            "top": 10,
            "select": [
                "id", "repo_name", "file_path", "language", "code_chunk",
                "semantic_context", "function_signature", "imports_used",
                "calls_functions", "chunk_type", "line_range"
            ]
        }

        # Add vector search if embedder is available
        if self.embedder:
            query_embedding = self.embedder.generate_embedding(enhanced_query)
            if query_embedding:
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=50,
                    fields="code_vector"
                )
                search_params["vector_queries"] = [vector_query]

        # Add language filter if specified
        if language:
            search_params["filter"] = f"language eq '{language}'"

        # Execute search
        results = list(self.search_client.search(**search_params))

        return results

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
        """Format search results for MCP response."""
        if not results:
            return "No results found."

        formatted = f"Found {len(results)} code matches:\n\n"

        for i, result in enumerate(results[:5], 1):  # Top 5 results
            formatted += f"**Result {i}**\n"
            formatted += f"- File: `{result.get('file_path', 'Unknown')}`\n"
            formatted += f"- Function: `{result.get('function_signature', 'N/A')}`\n"
            formatted += f"- Repository: `{result.get('repo_name', 'Unknown')}`\n"
            formatted += f"- Language: {result.get('language', 'Unknown')}\n"
            formatted += f"- Context: {result.get('semantic_context', '')[:200]}...\n"
            formatted += f"- Score: {result.get('@search.score', 0):.2f}\n\n"

            # Include code snippet
            code = result.get('code_chunk', '')
            if code:
                formatted += "```" + result.get('language', '') + "\n"
                formatted += code[:500] + ("..." if len(code) > 500 else "") + "\n"
                formatted += "```\n\n"

        return formatted


# FastAPI endpoints for testing
class MCPSearchRequest(BaseModel):
    input: str = Field(..., description="Natural language query or code context")
    context: Optional[Dict] = Field(None, description="Current code context from Claude")
    intent: Optional[str] = Field(None, description="Search intent: implement/debug/understand/refactor")


@app.get("/health")
def health():
    return {"status": "healthy", "version": "SOTA with Vector Support"}


@app.post("/mcp-query")
async def mcp_contextual_search(request: MCPSearchRequest):
    """SOTA contextual code search for Claude Code."""
    server = MCPServer()

    try:
        results = await server.search_code_enhanced(
            query=request.input,
            intent=request.intent
        )

        # Process results for MCP context
        mcp_context = []
        seen_functions = set()

        for result in results:
            if result.get("function_signature") not in seen_functions:
                seen_functions.add(result.get("function_signature"))

                # Build rich context
                context_entry = {
                    "file": result.get("file_path"),
                    "function": result.get("function_signature"),
                    "code": result.get("code_chunk"),
                    "relevance": result.get("@search.score", 0),
                    "context": result.get("semantic_context"),
                    "related_functions": result.get("calls_functions", []),
                    "imports": result.get("imports_used", []),
                    "line_range": result.get("line_range"),
                    "type": result.get("chunk_type")
                }

                mcp_context.append(context_entry)

                # Limit results for context window
                if len(mcp_context) >= 5:
                    break

        return {
            "context": mcp_context,
            "query_info": {
                "original": request.input,
                "intent": request.intent,
                "total_results": len(mcp_context),
                "vector_search_enabled": server.embedder is not None
            }
        }

    except Exception as e:
        return {"context": [], "error": str(e)}


# MCP Protocol server main loop
async def run_mcp_server():
    """Run the MCP server reading from stdin and writing to stdout."""
    server = MCPServer()

    while True:
        try:
            # Read line from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            # Parse JSON request
            request = json.loads(line.strip())

            # Handle request
            response = await server.handle_request(request)

            # Write response to stdout
            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    # If run directly, start FastAPI server for testing
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
