# mcp_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Code Search MCP")

search_client = SearchClient(
    endpoint=os.getenv("ACS_ENDPOINT"),
    index_name="codebase-search",
    credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
)

class SearchRequest(BaseModel):
    query: str
    language: Optional[str] = None
    max_results: int = 10

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/search")
async def search_code(request: SearchRequest):
    """Main search endpoint using 2025 preview features."""
    try:
        # Build filter
        filter_expr = f"language eq '{request.language}'" if request.language else None
        
        # Use 2025 text-to-vector feature - no embedding service needed!
        results = search_client.search(
            search_text=request.query,
            query_type="semantic",
            semantic_configuration_name="code-config",
            vector_queries=[{
                "kind": "text",  # Auto-converts text to vector
                "text": f"code that {request.query}",
                "fields": "code_content",
                "k": request.max_results
            }],
            filter=filter_expr,
            top=request.max_results
        )
        
        # Format results
        output = []
        for result in results:
            output.append({
                "file": result["file_path"],
                "function": result.get("function_name", ""),
                "language": result["language"],
                "score": result["@search.score"],
                "content": result["code_content"][:500]  # Preview
            })
        
        return {"results": output}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp-query")
async def mcp_query(request: Dict):
    """Claude Code compatible endpoint."""
    search_req = SearchRequest(query=request.get("input", ""))
    response = await search_code(search_req)
    
    # Format for Claude Code
    context = []
    for r in response["results"]:
        context.append({
            "file": r["file"],
            "function": r["function"],
            "code": r["content"]
        })
    
    return {"context": context}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
