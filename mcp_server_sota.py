# mcp_server_sota.py
import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv()

# MCP Protocol Implementation
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

search_client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-mcp-sota",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

class MCPSearchRequest(BaseModel):
    input: str = Field(..., description="Natural language query or code context")
    context: Optional[Dict] = Field(None, description="Current code context from Claude")
    intent: Optional[str] = Field(None, description="Search intent: implement/debug/understand/refactor")

class ContextualResult(BaseModel):
    file: str
    function: str
    code: str
    relevance: float
    context: str
    related_functions: List[str]
    imports: List[str]

@app.get("/health")
def health():
    return {"status": "healthy", "version": "SOTA"}

@app.post("/mcp-query")
async def mcp_contextual_search(request: MCPSearchRequest):
    """SOTA contextual code search for Claude Code."""

    try:
        # Enhanced query based on intent
        enhanced_query = _enhance_query_by_intent(request.input, request.intent)

        # Multi-stage retrieval for better context
        search_params = {
            "search_text": enhanced_query,
            "query_type": "semantic",
            "semantic_configuration_name": "mcp-semantic",
            "vector_queries": [
                {
                    "kind": "text",
                    "text": enhanced_query,
                    "fields": "semantic_context",
                    "k": 20,  # Get more candidates
                    "threshold": {"kind": "vectorSimilarity", "value": 0.7}
                },
                {
                    "kind": "text",
                    "text": f"code implementation: {request.input}",
                    "fields": "code_chunk",
                    "k": 10
                }
            ],
            "query_rewrites": "generative|count-3",  # Generate query variations
            "hybrid_search": {
                "max_text_recall_size": 2000,
                "count_and_facet_mode": "countAllResults"
            },
            "top": 15,
            "select": [
                "file_path", "function_signature", "code_chunk",
                "semantic_context", "imports_used", "calls_functions",
                "chunk_type", "line_range"
            ]
        }

        # Add context-aware filters
        if request.context:
            filters = _build_contextual_filters(request.context)
            if filters:
                search_params["filter"] = filters

        results = search_client.search(**search_params)

        # Process results with cross-reference enhancement
        mcp_context = []
        seen_functions = set()

        for result in results:
            if result["function_signature"] not in seen_functions:
                seen_functions.add(result["function_signature"])

                # Build rich context for Claude
                context_entry = {
                    "file": result["file_path"],
                    "function": result["function_signature"],
                    "code": result["code_chunk"],
                    "relevance": result.get("@search.score", 0),
                    "context": result["semantic_context"],
                    "related_functions": result.get("calls_functions", []),
                    "imports": result.get("imports_used", []),
                    "line_range": result["line_range"],
                    "type": result["chunk_type"]
                }

                mcp_context.append(context_entry)

                # Stop at 5 highly relevant results for Claude's context window
                if len(mcp_context) >= 5 and context_entry["relevance"] > 2.0:
                    break

        # Add cross-file context if needed
        if request.intent in ["implement", "debug"]:
            mcp_context = _add_dependency_context(mcp_context, search_client)

        return {
            "context": mcp_context,
            "query_info": {
                "original": request.input,
                "enhanced": enhanced_query,
                "intent": request.intent,
                "total_results": len(mcp_context)
            }
        }

    except Exception as e:
        return {"context": [], "error": str(e)}

def _enhance_query_by_intent(query: str, intent: Optional[str]) -> str:
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

def _build_contextual_filters(context: Dict) -> Optional[str]:
    """Build filters from Claude's current context."""
    filters = []

    if context.get("current_file"):
        # Prioritize same repository
        repo = context["current_file"].split("/")[0]
        filters.append(f"repo_name eq '{repo}'")

    if context.get("current_language"):
        filters.append(f"language eq '{context['current_language']}'")

    if context.get("imported_modules"):
        # Find code using similar imports
        import_filters = [f"imports_used/any(i: i eq '{imp}')"
                         for imp in context["imported_modules"][:3]]
        if import_filters:
            filters.append(f"({' or '.join(import_filters)})")

    return " and ".join(filters) if filters else None

def _add_dependency_context(results: List[Dict], client) -> List[Dict]:
    """Add related code that the main results depend on."""
    # Collect all called functions
    all_calls = set()
    for r in results[:3]:  # Top 3 results
        all_calls.update(r.get("related_functions", []))

    if all_calls:
        # Find implementations of called functions
        dep_query = " OR ".join([f'function_signature:"{fn}"' for fn in list(all_calls)[:5]])

        dep_results = client.search(
            search_text=dep_query,
            top=3,
            select=["file_path", "function_signature", "code_chunk"]
        )

        for dep in dep_results:
            results.append({
                "file": dep["file_path"],
                "function": dep["function_signature"],
                "code": dep["code_chunk"],
                "relevance": 0.5,  # Lower relevance for dependencies
                "context": "Dependency function",
                "related_functions": [],
                "imports": [],
                "type": "dependency"
            })

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
