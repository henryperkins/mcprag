#!/usr/bin/env python3
"""
Standalone Index Health Verification Script
Works without enhanced_rag dependencies
"""
import os
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()

async def verify_index_health(index_name: str = "codebase-mcp-sota") -> Dict[str, Any]:
    """Verify the health of the search index."""
    
    # Get credentials from environment
    endpoint = os.getenv("ACS_ENDPOINT", os.getenv("AZURE_SEARCH_ENDPOINT"))
    api_key = os.getenv("ACS_ADMIN_KEY", os.getenv("AZURE_SEARCH_API_KEY"))
    
    if not endpoint or not api_key:
        return {
            "status": "error",
            "message": "Missing Azure Search credentials in environment"
        }
    
    credential = AzureKeyCredential(api_key)
    
    # Create clients
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    
    health_report = {
        "index_name": index_name,
        "status": "unknown",
        "vector_fields": {},
        "document_count": 0,
        "sample_documents": [],
        "issues": []
    }
    
    try:
        # Check if index exists
        try:
            index = index_client.get_index(index_name)
            health_report["status"] = "exists"
        except Exception as e:
            health_report["status"] = "not_found"
            health_report["issues"].append(f"Index not found: {str(e)}")
            return health_report
        
        # Check vector fields
        for field in index.fields:
            if hasattr(field, 'vector_search_dimensions') and field.vector_search_dimensions:
                health_report["vector_fields"][field.name] = {
                    "dimensions": field.vector_search_dimensions,
                    "algorithm": "hnsw"  # Assuming HNSW
                }
                
                # Check if dimensions match expected (3072 for text-embedding-3-large)
                if field.vector_search_dimensions != 3072:
                    health_report["issues"].append(
                        f"Vector field '{field.name}' has {field.vector_search_dimensions} dimensions, "
                        f"expected 3072 for text-embedding-3-large"
                    )
        
        # Get document count
        result = search_client.search(search_text="*", include_total_count=True, top=0)
        health_report["document_count"] = result.get_count()
        
        # Sample documents to check for issues
        sample_results = search_client.search(
            search_text="*", 
            top=5,
            select=["id", "content", "file_path", "content_vector"]
        )
        
        for doc in sample_results:
            doc_info = {
                "id": doc.get("id", "unknown"),
                "has_content": bool(doc.get("content")),
                "content_length": len(doc.get("content", "")) if doc.get("content") else 0,
                "file_path": doc.get("file_path", "unknown")
            }
            
            # Check vector
            if "content_vector" in doc:
                vector = doc["content_vector"]
                if vector:
                    doc_info["vector_dimensions"] = len(vector)
                    # Check for zero vector
                    if all(v == 0.0 for v in vector[:10]):  # Check first 10 values
                        doc_info["vector_status"] = "zero_vector"
                        health_report["issues"].append(f"Document {doc_info['id']} has zero vector")
                    else:
                        doc_info["vector_status"] = "ok"
                else:
                    doc_info["vector_status"] = "missing"
            else:
                doc_info["vector_status"] = "field_missing"
            
            health_report["sample_documents"].append(doc_info)
        
        # Overall status
        if health_report["issues"]:
            health_report["status"] = "unhealthy"
        else:
            health_report["status"] = "healthy"
            
    except Exception as e:
        health_report["status"] = "error"
        health_report["issues"].append(f"Error checking index: {str(e)}")
    
    return health_report

def print_health_report(report: Dict[str, Any]):
    """Pretty print the health report."""
    print(f"\n{'='*60}")
    print(f"Index Health Report: {report['index_name']}")
    print(f"{'='*60}")
    
    # Status
    status_emoji = {
        "healthy": "✅",
        "unhealthy": "⚠️",
        "not_found": "❌",
        "error": "❌",
        "unknown": "❓"
    }.get(report["status"], "❓")
    
    print(f"\nStatus: {status_emoji} {report['status'].upper()}")
    print(f"Document Count: {report['document_count']:,}")
    
    # Vector fields
    if report["vector_fields"]:
        print("\nVector Fields:")
        for field_name, field_info in report["vector_fields"].items():
            print(f"  - {field_name}: {field_info['dimensions']} dimensions")
    
    # Sample documents
    if report["sample_documents"]:
        print("\nSample Documents:")
        for doc in report["sample_documents"]:
            print(f"  - ID: {doc['id']}")
            print(f"    Content: {'✓' if doc['has_content'] else '✗'} ({doc['content_length']} chars)")
            print(f"    Vector: {doc.get('vector_status', 'unknown')}")
            if doc.get('vector_dimensions'):
                print(f"    Dimensions: {doc['vector_dimensions']}")
    
    # Issues
    if report["issues"]:
        print(f"\n⚠️  Issues Found ({len(report['issues'])}):")
        for issue in report["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✅ No issues found!")
    
    print(f"\n{'='*60}\n")

async def main():
    """Run the health check."""
    print("Verifying Azure Cognitive Search index health...")
    
    # Check default index
    results = await verify_index_health()
    print_health_report(results)
    
    # Recommendations
    if results["status"] == "unhealthy":
        print("\n📋 Recommendations:")
        
        # Check for dimension issues
        if any("dimensions" in issue for issue in results["issues"]):
            print("  1. Re-create index with correct vector dimensions (3072)")
            print("     Run: python scripts/reindex_with_validation.py")
        
        # Check for zero vectors
        if any("zero vector" in issue for issue in results["issues"]):
            print("  2. Re-index documents with proper embeddings")
            print("     Ensure embedding provider is configured correctly")
        
        # Check for missing content
        if any(not doc["has_content"] for doc in results["sample_documents"]):
            print("  3. Some documents are missing content")
            print("     Check indexing pipeline and field mappings")

if __name__ == "__main__":
    asyncio.run(main())