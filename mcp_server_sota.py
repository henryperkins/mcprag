# mcp_server_sota.py
import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI

# Add import for vector embeddings
try:
    from vector_embeddings import VectorEmbedder
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False

# Add import for Microsoft Docs MCP Client
try:
    from microsoft_docs_mcp_client import MicrosoftDocsMCPClient
    MICROSOFT_DOCS_SUPPORT = True
except ImportError:
    MICROSOFT_DOCS_SUPPORT = False

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
        self.current_directory = os.getcwd()

        # Initialize embedder if available
        self.embedder = None
        if VECTOR_SUPPORT and (os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")):
            try:
                self.embedder = VectorEmbedder()
                print("✅ Vector search enabled in MCP server")
            except Exception as e:
                print(f"Warning: Could not initialize vector embedder: {e}")
                
        # Initialize Microsoft Docs client if available
        self.microsoft_docs_client = None
        if MICROSOFT_DOCS_SUPPORT:
            print("✅ Microsoft Docs search enabled in MCP server")
    
    def detect_current_repository(self) -> str:
        """Detect repository name from current working directory."""
        current_path = Path(self.current_directory)
        
        # Walk up directory tree looking for .git folder
        for parent in [current_path] + list(current_path.parents):
            git_dir = parent / ".git"
            if git_dir.exists() and git_dir.is_dir():
                # Found git repository root
                return parent.name
        
        # Fallback to current directory name
        return current_path.name

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
            tools = [
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
                            },
                            "repository": {
                                "type": "string",
                                "description": "Repository to search (defaults to current directory's repo name, use '*' for all repos)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
            
            # Add Microsoft Docs search tool if available
            if MICROSOFT_DOCS_SUPPORT:
                tools.append({
                    "name": "search_microsoft_docs",
                    "description": "Search Microsoft Learn documentation for APIs, guides, and technical reference",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query to search Microsoft documentation"
                            },
                            "max_results": {
                                "type": "number",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                })
                
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": tools
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
                    language=arguments.get("language"),
                    repository=arguments.get("repository")
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
                
        elif tool_name == "search_microsoft_docs" and MICROSOFT_DOCS_SUPPORT:
            try:
                # Create client instance for this request
                async with MicrosoftDocsMCPClient() as client:
                    results = await client.search_docs(
                        query=arguments.get("query", ""),
                        max_results=arguments.get("max_results", 10)
                    )
                    
                    formatted_results = self.format_microsoft_docs_results(results)
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": formatted_results
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
                        "message": f"Microsoft Docs search error: {str(e)}"
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

    async def search_code_enhanced(self, query: str, intent: Optional[str] = None, 
                                   language: Optional[str] = None, repository: Optional[str] = None) -> List[Dict]:
        """Enhanced search with vector support and repository filtering."""
        # Enhance query based on intent
        enhanced_query = self._enhance_query_by_intent(query, intent)
        
        # Determine repository to search
        if repository is None:
            # Default to current repository
            repository = self.detect_current_repository()
            print(f"🔍 Searching in repository: {repository} (auto-detected)")
        elif repository == "*" or repository.lower() == "all":
            # Search all repositories
            repository = None
            print("🔍 Searching across all repositories")
        else:
            print(f"🔍 Searching in repository: {repository}")

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

        # Build filter conditions
        filters = []
        
        # Add repository filter if specified (not None means we have a specific repo)
        if repository is not None:
            filters.append(f"repo_name eq '{repository}'")
        
        # Add language filter if specified
        if language:
            filters.append(f"language eq '{language}'")
        
        # Combine filters with AND
        if filters:
            search_params["filter"] = " and ".join(filters)

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
        
    def format_microsoft_docs_results(self, results: List[Dict]) -> str:
        """Format Microsoft Docs search results for MCP response."""
        if not results:
            return "No Microsoft documentation found for your query."
            
        formatted = f"Found {len(results)} Microsoft Docs matches:\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"**Result {i}**\n"
            formatted += f"- Title: {result.get('title', 'Unknown')}\n"
            formatted += f"- Source: {result.get('source', 'Microsoft Learn')}\n"
            
            content = result.get('content', '')
            if content:
                # Truncate content if too long
                if len(content) > 500:
                    content = content[:500] + "..."
                formatted += f"- Content: {content}\n"
            
            formatted += "\n"
            
        return formatted


# FastAPI endpoints for testing
class MCPSearchRequest(BaseModel):
    input: str = Field(..., description="Natural language query or code context")
    context: Optional[Dict] = Field(None, description="Current code context from Claude")
    intent: Optional[str] = Field(None, description="Search intent: implement/debug/understand/refactor")
    repository: Optional[str] = Field(None, description="Repository to search (defaults to current, use '*' for all)")


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
            intent=request.intent,
            repository=request.repository
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
    """
    Stand-alone entry point.

    --mode api (default)  → Launch FastAPI HTTP service on the given port
    --mode rpc            → Start JSON-RPC stdin/stdout loop for Claude MCP
    """
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Azure Code Search MCP Server")
    parser.add_argument(
        "--mode",
        choices=["api", "rpc"],
        default="api",
        help="api = FastAPI service (default); rpc = JSON-RPC over stdio",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_API_PORT", "8001")),
        help="Port for FastAPI when --mode api is used",
    )
    args = parser.parse_args()

    if args.mode == "api":
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # Launch the JSON-RPC loop that reads from stdin and writes to stdout
        asyncio.run(run_mcp_server())
